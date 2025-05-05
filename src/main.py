import argparse

import questionary
from models import db
from models import (
    Target,
    Group,
    TargetGroup,
    PhishingEmailTemplate,
    Execution,
    Attachment,
    PhishingEmail,
)


def main():
    with db:
        db.create_tables(
            [
                Target,
                Group,
                TargetGroup,
                PhishingEmailTemplate,
                Execution,
                Attachment,
                PhishingEmail,
            ],
            safe=True,
        )

    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(dest="command")

    target_parser = subparsers.add_parser("target")
    target_subparsers = target_parser.add_subparsers(dest="subcommand")
    target_subparsers.add_parser("create", help="Create a target")
    target_subparsers.add_parser("import", help="Import targets from a file")
    target_subparsers.add_parser("list", help="List all targets")
    target_subparsers.add_parser("clear", help="Delete all targets")

    group_parser = subparsers.add_parser("group")
    group_subparsers = group_parser.add_subparsers(dest="subcommand")
    group_subparsers.add_parser("create", help="Create a group")
    group_subparsers.add_parser("list", help="List all groups")
    group_subparsers.add_parser("clear", help="Delete all groups")

    template_parser = subparsers.add_parser("template")
    template_subparsers = template_parser.add_subparsers(dest="subcommand")
    template_subparsers.add_parser("create", help="Create a template")
    template_subparsers.add_parser("list", help="List all templates")

    execution_parser = subparsers.add_parser("execution")
    execution_subparsers = execution_parser.add_subparsers(dest="subcommand")
    execution_subparsers.add_parser("run", help="Run an execution")
    execution_subparsers.add_parser("schedule", help="Schedule an execution")
    execution_subparsers.add_parser("list", help="List all pending executions")

    attachment_parser = subparsers.add_parser("attachment")
    attachment_subparsers = attachment_parser.add_subparsers(dest="subcommand")
    attachment_subparsers.add_parser("create", help="Create an attachment")
    attachment_subparsers.add_parser("list", help="List all attachments")

    phishing_email_parser = subparsers.add_parser("phishing-email")
    phishing_email_subparsers = phishing_email_parser.add_subparsers(dest="subcommand")
    phishing_email_subparsers.add_parser("send", help="Send a phishing email")
    phishing_email_subparsers.add_parser("list", help="List all phishing emails")

    args = parser.parse_args()
    match args.command:
        case "target":
            match args.subcommand:
                case "create":
                    Target.prompt_and_create()
                case "import":
                    Target.import_from_csv()
                case "list":
                    Target.list()
                case "clear":
                    if questionary.confirm(
                        "Are you sure you want to delete all targets?"
                    ).ask():
                        Target.delete().execute()
        case "group":
            match args.subcommand:
                case "create":
                    Group.prompt_and_create()
                case "list":
                    Group.list()
                case "clear":
                    if questionary.confirm(
                        "Are you sure you want to delete all groups?"
                    ).ask():
                        Group.delete().execute()
        case "template":
            match args.subcommand:
                case "create":
                    PhishingEmailTemplate.prompt_and_create()
                case "list":
                    PhishingEmailTemplate.list()
        case "execution":
            match args.subcommand:
                case "run":
                    Execution.prompt_and_run()
                case "schedule":
                    Execution.prompt_and_schedule()
                case "list":
                    pass
        case "attachment":
            match args.subcommand:
                case "create":
                    Attachment.prompt_and_create()
                case "list":
                    pass
        case "phishing-email":
            match args.subcommand:
                case "send":
                    PhishingEmail.prompt_and_send()
                case "list":
                    pass


if __name__ == "__main__":
    main()
