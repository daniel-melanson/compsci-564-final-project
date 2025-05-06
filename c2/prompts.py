import csv
import json
import shutil
import uuid

import questionary
from models.attachment import Attachment, validate_attachment_name
from models.group import Group, validate_group_name
from models.phishing_email import PhishingEmail
from models.phishing_email_template import (
    PhishingEmailTemplate,
    validate_template_name,
    validate_template_subject,
)
from models.target import (
    Target,
    TargetGroup,
    get_fingerprint,
    validate_target_data,
    validate_target_email,
)
from tasks import send_phishing_email
from models import db


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
        path=f"templates/{id}_{name.strip().lower().replace(' ', '_')}.html",
    )
    shutil.copyfile("templates/default.html", template.path)
    questionary.print(f"Created {template}")
    questionary.print(f"Write template contents to: {template.path}")
    return template


def import_targets_from_csv():
    file_path = questionary.path("Enter file path").ask()

    def process_row(row):
        email, data, groups_raw = row
        if validate_target_email(email) != True:
            raise Exception(f"Invalid email: {email}")

        if validate_target_data(data) != True:
            raise Exception(f"Invalid data: {data}")

        target = cls.create(
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
        id=id, name=name.strip(), path=f"attachments/{id}_{name.strip()}"
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
                "name": "template",
                "message": "Select template",
                "choices": PhishingEmailTemplate.choices(),
                "validator": lambda template: (
                    True if len(template) > 0 else "Please select at least one template"
                ),
            },
            {
                "type": "checkbox",
                "name": "attachments",
                "message": "Select attachment",
                "choices": Attachment.choices(),
            },
        ]
    )

    if answers["single_or_group"] == "specific":
        targets = Target.select().where(Target.id << answers["target_ids"])
    else:
        assert answers["target_groups"] and len(answers["target_groups"]) > 0
        targets = Target.select_in_groups(answers["target_groups"])

    template = PhishingEmailTemplate.get(id=answers["template"])
    attachment = Attachment.get(id=answers["attachments"])

    for target in targets:
        phishing_email = PhishingEmail.create(
            target=target,
            template=template,
            attachment=attachment,
            celery_task_id=uuid.uuid4().hex,
            status="pending",
        )

        task = send_phishing_email.delay(phishing_email.id)
        phishing_email.celery_task_id = task.id
        phishing_email.save()

        questionary.print(f"Created {phishing_email}")

    return phishing_email
