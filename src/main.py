import argparse
from models import db
from models import Target, TargetGroup, Implant, Template


def main():
    with db:
        db.create_tables([Target, TargetGroup, Implant, Template], safe=True)

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


if __name__ == "__main__":
    main()
