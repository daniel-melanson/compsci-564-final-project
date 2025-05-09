"""
This is a C2 CLI for managing a phishing campaign.

Usage:
    c2 <command>

    c2 start-app                        - Start the C2 server that the implants connect to
    c2 target <subcommand>              - Manage targets (users to phish)
    c2 group <subcommand>               - Manage groups (collections of targets)
    c2 template <subcommand>            - Manage phishing email templates
    c2 execution <subcommand>           - Manage executions (commands to run on target machines)
    c2 attachment <subcommand>          - Manage attachments (files to send to targets in phishing emails)
    c2 phishing-email <subcommand>      - Manage phishing emails (emails to send to targets)
    c2 email-account <subcommand>       - Manage email accounts (email accounts to send phishing emails from)
"""
import argparse

import questionary

from c2.app import app
from c2.models import (
    Attachment,
    Execution,
    Group,
    PhishingEmail,
    PhishingEmailTemplate,
    Target,
    TargetGroup,
    db,
)
from c2.models.email_account import EmailAccount
from c2.prompts import (
    import_targets_from_csv,
    prompt_and_run_execution,
    prompt_and_schedule_execution,
    prompt_attachment,
    prompt_email_account,
    prompt_group,
    prompt_phishing_email,
    prompt_phishing_email_template,
    prompt_target,
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
                EmailAccount,
            ],
            safe=True,
        )

    parser = argparse.ArgumentParser()


    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("start-app")
    Target.add_subparser(subparsers)
    Group.add_subparser(subparsers)
    PhishingEmailTemplate.add_subparser(subparsers)
    Execution.add_subparser(subparsers)
    Attachment.add_subparser(subparsers)
    PhishingEmail.add_subparser(subparsers)
    EmailAccount.add_subparser(subparsers)

    args = parser.parse_args()
    match args.command:
        case "start-app":
            app.run(debug=True, host="0.0.0.0", port=8000)
            app.logger.info("Server started on port 8000")
        case "target":
            match args.subcommand:
                case "create":
                    prompt_target()
                case "import":
                    import_targets_from_csv()
                case "list":
                    Target.list()
                case "clear":
                    if questionary.confirm(
                        "Are you sure you want to delete all targets?"
                    ).ask():
                        Target.clear()
        case "group":
            match args.subcommand:
                case "create":
                    prompt_group()
                case "list":
                    Group.list()
                case "clear":
                    if questionary.confirm(
                        "Are you sure you want to delete all groups?"
                    ).ask():
                        Group.clear()
        case "template":
            match args.subcommand:
                case "create":
                    prompt_phishing_email_template()
                case "list":
                    PhishingEmailTemplate.list()
                case "clear":
                    if questionary.confirm(
                        "Are you sure you want to delete all templates?"
                    ).ask():
                        PhishingEmailTemplate.clear()
        case "execution":
            match args.subcommand:
                case "run":
                    prompt_and_run_execution()
                case "schedule":
                    prompt_and_schedule_execution()
                case "list":
                    Execution.list()
                case "clear":
                    if questionary.confirm(
                        "Are you sure you want to delete all executions?"
                    ).ask():
                        Execution.clear()
        case "attachment":
            match args.subcommand:
                case "create":
                    prompt_attachment()
                case "list":
                    Attachment.list()
                case "clear":
                    if questionary.confirm(
                        "Are you sure you want to delete all attachments?"
                    ).ask():
                        Attachment.clear()
        case "phishing-email":
            match args.subcommand:
                case "send":
                    prompt_phishing_email()
                case "list":
                    PhishingEmail.list()
                case "clear":
                    if questionary.confirm(
                        "Are you sure you want to delete all phishing emails?"
                    ).ask():
                        PhishingEmail.clear()
        case "email-account":
            match args.subcommand:
                case "create":
                    prompt_email_account()
                case "list":
                    EmailAccount.list()
                case "clear":
                    if questionary.confirm(
                        "Are you sure you want to delete all email accounts?"
                    ).ask():
                        EmailAccount.clear()


if __name__ == "__main__":
    main()
