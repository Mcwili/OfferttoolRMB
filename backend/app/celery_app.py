"""
Celery-Konfiguration für asynchrone Task-Verarbeitung
"""

from celery import Celery
from app.core.config import settings

# Celery-App erstellen
celery_app = Celery(
    "hlks_planungsanalyse",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.extraction_tasks"]
)

# Celery-Konfiguration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 Minuten Timeout
    task_soft_time_limit=25 * 60,  # 25 Minuten Soft-Timeout
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Separate Queue für Extraction-Tasks
    task_routes={
        "app.tasks.extraction_tasks.*": {"queue": "extraction"},
    },
    task_default_queue="default",
    task_default_exchange="tasks",
    task_default_exchange_type="direct",
    task_default_routing_key="default",
)

# Task-Module importieren
celery_app.autodiscover_tasks(["app.tasks"])
