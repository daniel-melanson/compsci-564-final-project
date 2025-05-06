import logging
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import jinja2
from celery import Celery

from c2.models import PhishingEmail, db

app = Celery("c2")


logger = logging.getLogger(__name__)


@app.task
def send_phishing_email(phishing_email_id: int):
    with db.transaction():
        phishing_email: PhishingEmail = PhishingEmail.get(id=phishing_email_id)
        phishing_email.status = "running"
        phishing_email.save()

    subject_template = jinja2.Template(phishing_email.template.subject)
    subject = subject_template.render(target=phishing_email.target)

    with open(phishing_email.template.path, "r") as f:
        body_template = jinja2.Template(f.read())

    body = body_template.render(target=phishing_email.target)

    email_account = phishing_email.email_account
    with smtplib.SMTP(email_account.smtp_server, email_account.smtp_port) as server:
        server.login(email_account.username, email_account.password)
        msg = MIMEMultipart()

        msg["From"] = email_account.username
        msg["To"] = phishing_email.target.email
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "html"))
        with open(phishing_email.attachment.path, "rb") as f:
            attachment = MIMEApplication(f.read())
            attachment.add_header(
                "Content-Disposition",
                f"attachment; filename={phishing_email.attachment.name}",
            )
            msg.attach(attachment)

        server.send_message(msg)

    with db.transaction():
        phishing_email.status = "completed"
        phishing_email.save()
