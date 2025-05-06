import csv
import json
import os
import random
import shutil
import uuid
from datetime import datetime, timedelta

import questionary

from c2.models import db
from c2.models.attachment import Attachment
from c2.models.email_account import EmailAccount
from c2.models.execution import Execution
from c2.models.group import Group
from c2.models.phishing_email import PhishingEmail
from c2.models.phishing_email_template import PhishingEmailTemplate
from c2.models.target import Target, TargetGroup, get_fingerprint
from c2.tasks import send_phishing_email
from c2.validators import (
    duration_to_seconds,
    validate_attachment_name,
    validate_date,
    validate_duration,
    validate_email_account_name,
    validate_group_name,
    validate_target_data,
    validate_target_email,
    validate_template_name,
    validate_template_subject,
)


def prompt_group():
    name = questionary.text(
        "Enter target group name", validate=validate_group_name
    ).ask()
    assert name.strip()

    group = Group.create(name=name.strip())
    questionary.print(f"Created {group}")
    return group


def prompt_phishing_email_template():
    id = uuid.uuid4().hex[:8]
    name = questionary.text(
        "Enter template name",
        validate=validate_template_name,
    ).ask()
    assert name.strip()
    subject = questionary.text(
        "Enter template subject (as seen by the target; supports Jinja)",
        validate=validate_template_subject,
    ).ask()
    assert subject.strip()

    template = PhishingEmailTemplate.create(
        id=id,
        name=name.strip(),
        subject=subject.strip(),
        path=os.path.join(
            os.getcwd(), f"templates/{id}_{name.strip().lower().replace(' ', '_')}.html"
        ),
    )
    shutil.copyfile("templates/default.html", template.path)
    questionary.print(f"Created {template}")
    questionary.print(f"Write template contents to: {template.path}")
    return template


def prompt_email_account():
    name = questionary.text(
        "Enter email account name",
        validate=validate_email_account_name,
    ).ask()
    assert name.strip()
    username = questionary.text(
        "Enter email account username",
    ).ask()
    assert username.strip()
    password = questionary.password(
        "Enter email account password",
    ).ask()
    assert password.strip()
    smtp_server = questionary.text(
        "Enter email account SMTP server",
    ).ask()
    assert smtp_server.strip()
    smtp_port = questionary.text(
        "Enter email account SMTP port",
    ).ask()
    assert smtp_port.strip()

    email_account = EmailAccount.create(
        name=name.strip(),
        username=username.strip(),
        password=password.strip(),
        smtp_server=smtp_server.strip(),
        smtp_port=int(smtp_port.strip()),
    )
    questionary.print(f"Created {email_account}")
    return email_account


def import_targets_from_csv():
    file_path = questionary.path("Enter file path").ask()

    def process_row(row):
        email, data, groups_raw = row
        if validate_target_email(email) != True:
            raise Exception(f"Invalid email: {email}")

        if validate_target_data(data) != True:
            raise Exception(f"Invalid data: {data}")

        target = Target.create(
            email=email,
            data=json.loads(data),
            fingerprint=get_fingerprint(email),
        )

        groups = groups_raw.split(",")
        for group_name in groups:
            group, _ = Group.get_or_create(name=group_name.strip())
            TargetGroup.create(target=target, group=group)

    count = 0
    with db.transaction():
        with open(file_path, "r") as f:
            next(f)  # Skip header
            for row in csv.reader(f):
                process_row(row)
                count += 1

    questionary.print(f"Imported {count} targets")


def prompt_target():
    group_choices = Group.choices()
    answers = questionary.prompt(
        [
            {
                "type": "text",
                "name": "email",
                "message": "Enter target email",
                "validate": validate_target_email,
            },
            {
                "type": "text",
                "name": "data",
                "message": "Enter target data (JSON)",
                "default": "{}",
                "validate": validate_target_data,
            },
            {
                "type": "checkbox",
                "name": "groups",
                "message": "Select target group(s)",
                "choices": group_choices,
                "when": lambda answers: len(group_choices) > 0,
            },
        ]
    )
    assert answers["email"].strip()
    assert answers["data"].strip()

    target = Target.create(
        email=answers["email"].strip().lower(),
        data=answers["data"],
        fingerprint=get_fingerprint(answers["email"]),
    )

    for group_id in answers.get("groups", []):
        group = Group.get(id=int(group_id))
        TargetGroup.create(target=target, group=group)

    questionary.print(f"Created {target}")
    return target


def prompt_attachment():
    id = uuid.uuid4().hex[:8]
    name = questionary.text(
        "Enter the attachment name as seen by the target",
        validate=validate_attachment_name,
    ).ask()
    attachment = Attachment.create(
        id=id,
        name=name.strip(),
        path=os.path.join(os.getcwd(), f"attachments/{id}_{name.strip()}"),
    )
    with open(attachment.path, "w") as f:
        f.write("")

    questionary.print(f"Created {attachment}")
    questionary.print(f"Write attachment contents to: {attachment.path}")
    return attachment


def prompt_phishing_email():
    if Target.select().count() == 0:
        raise ValueError("No targets found")
    if Group.select().count() == 0:
        raise ValueError("No groups found")
    if EmailAccount.select().count() == 0:
        raise ValueError("No email accounts found")
    if PhishingEmailTemplate.select().count() == 0:
        raise ValueError("No phishing email templates found")
    if Attachment.select().count() == 0:
        raise ValueError("No attachments found")

    answers = questionary.prompt(
        [
            {
                "type": "select",
                "name": "single_or_group",
                "message": "Send a phishing email to a specific target or a group?",
                "choices": ["specific", "group"],
            },
            {
                "type": "checkbox",
                "name": "target_ids",
                "message": "Select target(s)",
                "choices": Target.choices(),
                "validator": lambda targets: (
                    True if len(targets) > 0 else "Please select at least one target"
                ),
                "when": lambda answers: answers["single_or_group"] == "specific",
            },
            {
                "type": "checkbox",
                "name": "target_groups",
                "message": "Select target group(s)",
                "choices": Group.choices(),
                "validator": lambda groups: (
                    True if len(groups) > 0 else "Please select at least one group"
                ),
                "when": lambda answers: answers["single_or_group"] == "group",
            },
            {
                "type": "select",
                "name": "email_account",
                "message": "Which email account to use?",
                "choices": EmailAccount.choices(),
            },
            {
                "type": "select",
                "name": "template",
                "message": "Which template to use?",
                "choices": PhishingEmailTemplate.choices(),
            },
            {
                "type": "select",
                "name": "attachments",
                "message": "Which attachment to use?",
                "choices": Attachment.choices(),
            },
            {
                "type": "confirm",
                "name": "random_offset",
                "message": "Add random offset to execution time?",
            },
            {
                "type": "text",
                "name": "random_offset_duration",
                "message": "Enter random offset duration (e.g. 1d2h3m5s)",
                "validate": validate_duration,
                "when": lambda answers: answers["random_offset"],
            },
        ]
    )

    template = PhishingEmailTemplate.get(id=answers["template"])
    attachment = Attachment.get(id=answers["attachments"])
    email_account = EmailAccount.get(id=answers["email_account"])

    for target in _get_targets(answers):
        phishing_email = PhishingEmail.create(
            target=target,
            template=template,
            attachment=attachment,
            email_account=email_account,
            celery_task_id=uuid.uuid4().hex,
            status="pending",
        )

        if answers["random_offset"]:
            max_offset = int(duration_to_seconds(answers["random_offset_duration"]))
            offset = random.randint(max_offset // 10, max_offset)
            task = send_phishing_email.apply_async(args=[phishing_email.id], countdown=offset)
        else:
            task = send_phishing_email.delay(phishing_email.id)

        phishing_email.celery_task_id = task.id
        phishing_email.save()

        questionary.print(f"Created {phishing_email}")


def _default_execution_prompt():
    if Target.select().count() == 0:
        raise ValueError("No targets found")
    if Group.select().count() == 0:
        raise ValueError("No groups found")

    return [
        {
            "type": "select",
            "name": "single_or_group",
            "message": "Execute against a specific target or a group?",
            "choices": ["specific", "group"],
        },
        {
            "type": "checkbox",
            "name": "target_ids",
            "message": "Select target(s)",
            "choices": Target.choices(),
            "validate": lambda targets: (
                True if len(targets) > 0 else "Please select at least one target"
            ),
            "when": lambda answers: answers["single_or_group"] == "specific",
        },
        {
            "type": "checkbox",
            "name": "target_groups",
            "message": "Select target group(s)",
            "choices": Group.choices(),
            "validate": lambda groups: (
                True if len(groups) > 0 else "Please select at least one group"
            ),
            "when": lambda answers: answers["single_or_group"] == "group",
        },
        {
            "type": "select",
            "name": "command_or_script",
            "message": "Execute a command or script?",
            "choices": ["command", "script"],
        },
        {
            "type": "text",
            "name": "command",
            "message": "Enter command",
            "when": lambda answers: answers["command_or_script"] == "command",
        },
        {
            "type": "path",
            "name": "script",
            "message": "Enter script path",
            "validate": lambda script: (
                True
                if os.path.exists(script)
                and os.path.isfile(script)
                and os.access(script, os.R_OK)
                else "Script does not exist or is not readable"
            ),
            "when": lambda answers: answers["command_or_script"] == "script",
        },
    ]


def _get_targets(answers):
    if answers["single_or_group"] == "specific":
        targets = Target.select().where(Target.id << answers["target_ids"])
    else:
        assert answers["target_groups"] and len(answers["target_groups"]) > 0
        targets = Target.select_in_groups(answers["target_groups"])

    return targets


def _get_command(answers):
    if answers["command_or_script"] == "script":
        with open(answers["script"], "r") as f:
            command = f.read()
    else:
        command = answers["command"]

    return command


def prompt_and_run_execution():
    answers = questionary.prompt(_default_execution_prompt())
    command = _get_command(answers)

    for target in _get_targets(answers):
        execution = Execution.create(
            target=target,
            status="pending",
            command=command,
            run_at=datetime.now(),
        )
        questionary.print(f"Created {execution}")


def prompt_and_schedule_execution():
    questions = _default_execution_prompt() + [
        {
            "type": "text",
            "name": "date",
            "message": "Enter date and time (ISO 8601)",
            "validate": validate_date,
        },
        {
            "type": "confirm",
            "name": "random_offset",
            "message": "Add random offset to execution time?",
        },
        {
            "type": "text",
            "name": "random_offset_duration",
            "message": "Enter random offset duration (e.g. 1d2h3m5s)",
            "validate": validate_duration,
            "when": lambda answers: answers["random_offset"],
        },
    ]

    answers = questionary.prompt(questions)
    command = _get_command(answers)

    for target in _get_targets(answers):
        run_at = datetime.fromisoformat(answers["date"])
        if "random_offset" in answers and answers["random_offset"]:
            max_offset = int(duration_to_seconds(answers["random_offset_duration"]))
            run_at += timedelta(seconds=random.randint(max_offset // 10, max_offset))

        execution = Execution.create(
            target=target,
            status="pending",
            command=command,
            run_at=run_at,
        )

        questionary.print(f"Created {execution}")
