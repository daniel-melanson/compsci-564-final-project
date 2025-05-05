from models.base import BaseModel
from models.group import Group
from models.target import Target


class TargetGroup(BaseModel):
    group = ForeignKeyField(Group, on_delete="CASCADE", related_name="targets")
    target = ForeignKeyField(Target, on_delete="CASCADE", related_name="groups")

    class Meta:
        unique_together = ("group", "target")
