import logging

import jinja2

from c2.models import db, PhishingEmail
from celery import Celery

app = Celery("c2")


logger = logging.getLogger(__name__)


@app.task
def send_phishing_email(phishing_email_id: int):
    with db.transaction():
        phishing_email = PhishingEmail.get(id=phishing_email_id)
        phishing_email.status = "running"
        phishing_email.save()

    subject_template = jinja2.Template(phishing_email.subject)
    subject = subject_template.render(target=phishing_email.target)

    with open(phishing_email.template.path, "r") as f:
        body_template = jinja2.Template(f.read())

    body = body_template.render(target=phishing_email.target)

    logger.info(subject)
    logger.info(body)

    logger.info("send_phishing_email")
