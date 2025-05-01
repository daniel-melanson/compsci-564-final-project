import argparse
from models import db
from models import Target, TargetGroup, Implant, Template, Execution


def main():
    with db:
        db.create_tables([Target, TargetGroup, Implant, Template, Execution], safe=True)


    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(dest="command")

    target_parser = subparsers.add_parser("target")
    target_parser.add_argument("create", help="Create a target")
    target_parser.add_argument("import", help="Import targets from a file")
    target_parser.add_argument("list", help="List all targets")

    target_group_parser = subparsers.add_parser("target-group")
    target_group_parser.add_argument("create", help="Create a target group")
    target_group_parser.add_argument("list", help="List all target groups")

    implant_parser = subparsers.add_parser("implant")
    implant_parser.add_argument("create", help="Create an implant")
    implant_parser.add_argument("list", help="List all implants")

    template_parser = subparsers.add_parser("template")
    template_parser.add_argument("create", help="Create a template")
    template_parser.add_argument("list", help="List all templates")

    execution_parser = subparsers.add_parser("execution")
    execution_parser.add_argument("run", help="Run an execution")
    execution_parser.add_argument("schedule", help="Schedule an execution")
    execution_parser.add_argument("list", help="List all pending executions")

    args = parser.parse_args()
    match args.command:
        case "target":
            match args.subcommand:
                case "create":
                    Target.prompt_and_create()
                case "import":
                    Target.import_from_csv()
                case "list":
                    pass
        case "target-group":
            match args.subcommand:
                case "create":
                    TargetGroup.prompt_and_create()
                case "list":
                    pass
        case "implant":
            match args.subcommand:
                case "create":
                    Implant.prompt_and_create()
                case "list":
                    pass
        case "template":
            match args.subcommand:
                case "create":
                    Template.prompt_and_create()
                case "list":
                    pass
        case "execution":
            match args.subcommand:
                case "run":
                    Execution.prompt_and_run()
                case "schedule":
                    Execution.prompt_and_schedule()
                case "list":
                    pass


if __name__ == "__main__":
    main()
