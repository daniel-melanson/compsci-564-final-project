from datetime import datetime
from playhouse.postgres_ext import *
from tabulate import tabulate

from .base import BaseModel
from .target import Target


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
