from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "photo_social_platform",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.email_tasks"]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
    task_soft_time_limit=240,  # 4 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Optional: Configure periodic tasks if needed
celery_app.conf.beat_schedule = {
    # Example: Clean old chat messages every day
    'clean-old-messages': {
        'task': 'app.tasks.email_tasks.clean_old_chat_messages',
        'schedule': 86400.0,  # 24 hours in seconds
    },
}