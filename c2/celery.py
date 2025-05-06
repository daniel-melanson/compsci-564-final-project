from celery import Celery

app = Celery("c2", broker="redis://redis:6379/0", backend="redis://redis:6379/0")

app.autodiscover_tasks(["c2.tasks"])

if __name__ == "__main__":
    app.start()
