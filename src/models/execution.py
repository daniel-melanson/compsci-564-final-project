from models.base import BaseModel
import os
from models.target import Target
from models.group import Group
from playhouse.postgres_ext import *
import questionary
import re
from datetime import datetime, timedelta
from tabulate import tabulate
import random


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


class Execution(BaseModel):
    id = AutoField(primary_key=True)
    target = ForeignKeyField(Target, on_delete="CASCADE", related_name="executions")
    status = CharField()
    command = TextField()
    run_at = DateTimeField()
    result = TextField(null=True)
    created_at = DateTimeField(default=lambda: datetime.now())

    def __str__(self):
        return f"Execution[{self.id}] (target={self.target}, status={self.status})"

    @classmethod
    def list(cls):
        query = cls.select().dicts()
        print(tabulate(query, headers="keys", tablefmt="psql"))

    @classmethod
    def clear(cls):
        cls.delete().execute()

    @classmethod
    def add_subparser(cls, subparsers):
        parser = subparsers.add_parser("execution", help="Manage executions")
        parser.add_argument("subcommand", choices=["run", "schedule", "list", "clear"])

    @classmethod
    def _default_prompt(cls):
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

    @classmethod
    def _get_targets(cls, answers):
        if answers["single_or_group"] == "specific":
            targets = Target.select().where(Target.id << answers["target_ids"])
        else:
            assert answers["target_groups"] and len(answers["target_groups"]) > 0
            targets = Target.select_in_groups(answers["target_groups"])

        return targets

    @classmethod
    def _get_command(cls, answers):
        if answers["command_or_script"] == "script":
            with open(answers["script"], "r") as f:
                command = f.read()
        else:
            command = answers["command"]

        return command

    @classmethod
    def prompt_and_run(cls):
        answers = questionary.prompt(cls._default_prompt())
        command = cls._get_command(answers)

        for target in cls._get_targets(answers):
            execution = cls.create(
                target=target,
                status="pending",
                command=command,
                run_at=datetime.now(),
            )
            questionary.print(f"Created {execution}")

    @classmethod
    def prompt_and_schedule(cls):
        questions = cls._default_prompt() + [
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
        command = cls._get_command(answers)

        for target in cls._get_targets(answers):
            run_at = datetime.fromisoformat(answers["date"])
            if "random_offset" in answers and answers["random_offset"]:
                max_offset = int(duration_to_seconds(answers["random_offset_duration"]))
                run_at += timedelta(
                    seconds=random.randint(max_offset // 10, max_offset)
                )

            execution = cls.create(
                target=target,
                status="pending",
                command=command,
                run_at=run_at,
            )

            questionary.print(f"Created {execution}")
