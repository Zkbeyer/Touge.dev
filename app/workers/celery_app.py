from celery import Celery
from celery.schedules import crontab

from app.config import settings

app = Celery(
    "mountain_pass_streak",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

app.conf.beat_schedule = {
    "sync-active-users": {
        "task": "app.workers.tasks.sync_all_active_users",
        "schedule": crontab(minute=0),  # every hour
    },
}
