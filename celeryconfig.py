from celery.schedules import crontab

broker_url = 'redis://localhost:6379/0'
result_backend = 'redis://localhost:6379/0'

beat_schedule = {
    # 'run-every-morning': {
    #     'task': 'tasks.my_scheduled_task',
    #     'schedule': crontab(hour=7, minute=30),
    # },
}

timezone = 'UTC'