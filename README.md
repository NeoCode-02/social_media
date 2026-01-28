# Social Media Platform

A modern photo-sharing social media platform built with FastAPI. Share photos, connect with users, chat in real-time, and engage through likes and comments.

## Features

- **User Management**: Authentication with JWT, email verification, and Google OAuth
- **Photos**: Upload, view, and organize with automatic compression
- **Social Features**: Follow users, like/dislike photos, nested comments
- **Real-time Chat**: One-to-one messaging with WebSocket support
- **User Control**: Block users, search and filter content
- **Notifications**: Email alerts powered by Celery background tasks

## Tech Stack

- **Backend**: FastAPI
- **Database**: PostgreSQL with SQLAlchemy v2
- **Cache**: Redis
- **Task Queue**: Celery
- **Image Processing**: Pillow
- **Migrations**: Alembic

## Quick Start

### Prerequisites
- Python 3.12+
- PostgreSQL
- Redis

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd social_media

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt or "uv sync"
```

### Setup & Run

```bash
# Run database migrations
alembic upgrade head

# Terminal 1: Start FastAPI server
uvicorn app.main:app --reload

# Terminal 2: Start Celery worker
celery -A app.core.celery_app worker --loglevel=info
```

Access the API at `http://localhost:8000/docs`

## API Endpoints

**Authentication**: `/api/v1/auth/` (register, login, verify email, password reset, OAuth)

**Users**: `/api/v1/users/` (profile, follow/unfollow, block/unblock)

**Photos**: `/api/v1/photos/` (upload, list, like, categories)

**Comments**: `/api/v1/photos/{photo_id}/comments` (add, reply, update, delete)

**Chat**: `WS /api/v1/chat/ws` (real-time messaging)

## Project Structure

```
app/
├── api/v1/endpoints/     # API route handlers
├── core/                 # Config, security, Celery setup
├── db/                   # Database session & base models
├── models/               # SQLAlchemy ORM models
├── schemas/              # Pydantic request/response schemas
├── services/             # Business logic (email, cache)
├── tasks/                # Celery async tasks
└── utils/                # Helper functions
```

## License

MIT