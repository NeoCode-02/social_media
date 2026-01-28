from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from typing import Dict, List
from datetime import datetime

from app.db.session import get_db, AsyncSessionLocal
from app.models.user import User
from app.models.chat import ChatMessage
from app.schemas.chat import MessageCreate, MessageResponse, ConversationResponse
from app.api.deps import get_current_verified_user
from app.core.security import decode_token
from app.services.cache_service import set_user_online, is_user_online

router = APIRouter()

# Store active WebSocket connections
active_connections: Dict[int, WebSocket] = {}


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str):
    """WebSocket endpoint for real-time chat"""
    
    # Verify token
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    user_id = payload.get("sub")
    if not user_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    # Accept connection
    await websocket.accept()
    active_connections[user_id] = websocket
    await set_user_online(user_id)
    
    try:
        async with AsyncSessionLocal() as db:
            while True:
                # Receive message
                data = await websocket.receive_json()
                
                message_type = data.get("type")
                
                if message_type == "message":
                    # Send message
                    receiver_id = data.get("receiver_id")
                    content = data.get("content")
                    
                    if not receiver_id or not content:
                        continue
                    
                    # Check if users are not blocked
                    # (Add block check logic here)
                    
                    # Save message to database
                    message = ChatMessage(
                        content=content,
                        sender_id=user_id,
                        receiver_id=receiver_id
                    )
                    db.add(message)
                    await db.commit()
                    await db.refresh(message)
                    
                    # Send to receiver if online
                    if receiver_id in active_connections:
                        receiver_ws = active_connections[receiver_id]
                        await receiver_ws.send_json({
                            "type": "message",
                            "id": message.id,
                            "content": content,
                            "sender_id": user_id,
                            "created_at": message.created_at.isoformat()
                        })
                    
                    # Confirm to sender
                    await websocket.send_json({
                        "type": "sent",
                        "id": message.id,
                        "receiver_id": receiver_id
                    })
                
                elif message_type == "typing":
                    # Notify typing status
                    receiver_id = data.get("receiver_id")
                    if receiver_id and receiver_id in active_connections:
                        receiver_ws = active_connections[receiver_id]
                        await receiver_ws.send_json({
                            "type": "typing",
                            "sender_id": user_id
                        })
                
                elif message_type == "read":
                    # Mark message as read
                    message_id = data.get("message_id")
                    if message_id:
                        result = await db.execute(
                            select(ChatMessage).where(
                                and_(
                                    ChatMessage.id == message_id,
                                    ChatMessage.receiver_id == user_id
                                )
                            )
                        )
                        message = result.scalar_one_or_none()
                        if message:
                            message.is_read = True
                            message.read_at = datetime.utcnow()
                            await db.commit()
                            
                            # Notify sender
                            if message.sender_id in active_connections:
                                sender_ws = active_connections[message.sender_id]
                                await sender_ws.send_json({
                                    "type": "read",
                                    "message_id": message_id
                                })
    
    except WebSocketDisconnect:
        pass
    finally:
        # Remove connection
        if user_id in active_connections:
            del active_connections[user_id]


@router.get("/conversations", response_model=List[ConversationResponse])
async def get_conversations(
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Get list of conversations with latest message"""
    
    # Get all users the current user has chatted with
    result = await db.execute(
        select(ChatMessage)
        .where(
            or_(
                ChatMessage.sender_id == current_user.id,
                ChatMessage.receiver_id == current_user.id
            )
        )
        .order_by(ChatMessage.created_at.desc())
    )
    messages = result.scalars().all()
    
    # Build conversations map
    conversations = {}
    for message in messages:
        other_user_id = message.receiver_id if message.sender_id == current_user.id else message.sender_id
        
        if other_user_id not in conversations:
            # Get unread count
            unread_count = await db.scalar(
                select(func.count()).select_from(ChatMessage).where(
                    and_(
                        ChatMessage.sender_id == other_user_id,
                        ChatMessage.receiver_id == current_user.id,
                        ChatMessage.is_read == False
                    )
                )
            )
            
            # Get other user info
            user_result = await db.execute(select(User).where(User.id == other_user_id))
            other_user = user_result.scalar_one_or_none()
            
            if other_user:
                conversations[other_user_id] = ConversationResponse(
                    user_id=other_user.id,
                    username=other_user.username,
                    profile_picture=other_user.profile_picture,
                    last_message=message.content[:50],
                    last_message_time=message.created_at,
                    unread_count=unread_count or 0
                )
    
    return list(conversations.values())


@router.get("/messages/{other_user_id}", response_model=List[MessageResponse])
async def get_chat_history(
    other_user_id: int,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Get chat message history with another user"""
    
    # Check if other user exists
    result = await db.execute(select(User).where(User.id == other_user_id))
    other_user = result.scalar_one_or_none()
    
    if not other_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get messages between current user and other user
    result = await db.execute(
        select(ChatMessage)
        .where(
            or_(
                and_(
                    ChatMessage.sender_id == current_user.id,
                    ChatMessage.receiver_id == other_user_id
                ),
                and_(
                    ChatMessage.sender_id == other_user_id,
                    ChatMessage.receiver_id == current_user.id
                )
            )
        )
        .order_by(ChatMessage.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    messages = result.scalars().all()
    
    # Mark messages from other user as read
    for message in messages:
        if message.receiver_id == current_user.id and not message.is_read:
            message.is_read = True
            message.read_at = datetime.utcnow()
    
    await db.commit()
    
    # Return messages in chronological order
    return [MessageResponse.model_validate(msg) for msg in reversed(messages)]


@router.post("/messages/{receiver_id}", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message_rest(
    receiver_id: int,
    message_data: MessageCreate,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Send a message (REST API fallback)"""
    
    # Check if receiver exists
    result = await db.execute(select(User).where(User.id == receiver_id))
    receiver = result.scalar_one_or_none()
    
    if not receiver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receiver not found"
        )
    
    # Can't send message to yourself
    if receiver_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot send message to yourself"
        )
    
    # Create message
    message = ChatMessage(
        content=message_data.content,
        sender_id=current_user.id,
        receiver_id=receiver_id
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    
    # Notify receiver if online via WebSocket
    if receiver_id in active_connections:
        receiver_ws = active_connections[receiver_id]
        try:
            await receiver_ws.send_json({
                "type": "message",
                "id": message.id,
                "content": message.content,
                "sender_id": current_user.id,
                "created_at": message.created_at.isoformat()
            })
        except:
            pass
    
    return MessageResponse.model_validate(message)