from celery import Celery

app = Celery("c2_server", broker="redis://redis:6379/0", backend="redis://redis:6379/0")

@app.task
def send_phishing_email(target, phishing_email):
    pass
