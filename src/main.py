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
        db.drop_tables([PhishingEmailTemplate], cascade=True)
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

    Target.add_subparser(subparsers)
    Group.add_subparser(subparsers)
    PhishingEmailTemplate.add_subparser(subparsers)
    Execution.add_subparser(subparsers)
    Attachment.add_subparser(subparsers)
    PhishingEmail.add_subparser(subparsers)

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
