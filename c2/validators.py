"""
This fule contains miscellanious validators for user input.
"""

import json
import re
from datetime import datetime

from c2.models import Attachment, EmailAccount, Group, PhishingEmailTemplate, Target


def validate_target_id(target_id):
    try:
        target_id = int(target_id)
    except ValueError:
        return "Target ID must be an integer"
    try:
        Target.get(id=target_id)
    except Target.DoesNotExist:
        return "Target does not exist"

    return True


def validate_target_email(email):
    email = email.strip().lower()
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

    if not re.match(pattern, email):
        return "Invalid email address"
    elif Target.select().where(Target.email == email).exists():
        return "Target with this email already exists"
    else:
        return True


def validate_target_data(data):
    try:
        json.loads(data)
    except json.JSONDecodeError:
        return "Invalid JSON"
    else:
        return True


def validate_template_name(name):
    name = name.strip()
    if len(name) < 3:
        return "Template name must be at least 3 characters long"
    elif len(name) > 100:
        return "Template name cannot be longer than 100 characters"
    elif not re.match(r"^[\w ]+$", name):
        return "Template name can only contain letters, numbers, and spaces"
    elif (
        PhishingEmailTemplate.select()
        .where(PhishingEmailTemplate.name == name)
        .exists()
    ):
        return "Template name already exists"
    else:
        return True


def validate_template_subject(subject):
    subject = subject.strip()
    if len(subject) < 3:
        return "Template subject must be at least 3 characters long"
    elif len(subject) > 100:
        return "Template subject cannot be longer than 100 characters"
    else:
        return True


def validate_group_name(name):
    name = name.strip()
    if len(name) < 3:
        return "Target group name must be at least 3 characters long"
    elif len(name) > 100:
        return "Target group name cannot be longer than 100 characters"
    elif not re.match(r"^[\w ]+$", name):
        return "Target group name can only contain letters, numbers, and spaces"
    elif Group.select().where(Group.name == name).exists():
        return "Target group name already exists"
    else:
        return True


def validate_attachment_name(name):
    name = name.strip()
    if len(name) < 3:
        return "Attachment name must be at least 3 characters long"
    elif len(name) > 100:
        return "Attachment name cannot be longer than 100 characters"
    elif Attachment.select().where(Attachment.name == name).exists():
        return "Attachment name already exists"
    else:
        return True


def validate_email_account_name(name: str):
    name = name.strip()
    if name == "":
        return "Name cannot be empty"
    elif len(name) < 3:
        return "Name must be at least 3 characters long"
    elif len(name) > 32:
        return "Name must be at most 32 characters long"
    elif EmailAccount.select().where(EmailAccount.name == name).exists():
        return "Name already exists"
    return True


def validate_date(date):
    try:
        date = datetime.fromisoformat(date)
    except ValueError:
        return "Invalid date format"

    if date < datetime.now():
        return "Date must be in the future"

    return True


def validate_duration(duration):
    duration_pattern = r"^(\d+d)?(\d+h)?(\d+m)?(\d+s)?$"
    match = re.match(duration_pattern, duration)

    if not match:
        return "Invalid duration format. Expected e.g. 1d2h3m5s"
    else:
        return True


def duration_to_seconds(duration):
    duration_pattern = r"^(\d+d)?(\d+h)?(\d+m)?(\d+s)?$"
    match = re.match(duration_pattern, duration)

    if not match:
        raise ValueError("Invalid duration format")

    seconds = 0
    if match.group(1):
        seconds += int(match.group(1)[:-1]) * 24 * 60 * 60
    if match.group(2):
        seconds += int(match.group(2)[:-1]) * 60 * 60
    if match.group(3):
        seconds += int(match.group(3)[:-1]) * 60
    if match.group(4):
        seconds += int(match.group(4)[:-1])

    return seconds
