from celery import Celery
import jinja2
import logging
from models.phishing_email import PhishingEmail

celery = Celery("c2_server", broker="redis://redis:6379/0", backend="redis://redis:6379/0")

logger = logging.getLogger(__name__)


@celery.task
def send_phishing_email(phishing_email_id: int):
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
