from playhouse.postgres_ext import *
import psycopg2

conn = psycopg2.connect(
    host="db", user="postgres", password="postgres", database="postgres"
)
conn.autocommit = True
cursor = conn.cursor()
cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = 'c2_server'")
exists = cursor.fetchone()
if not exists:
    cursor.execute("CREATE DATABASE c2_server")
conn.close()

db = PostgresqlExtDatabase(
    "c2_server", user="postgres", password="postgres", host="db", port=5432
)

from .base import BaseModel
from .target import Target
from .group import Group
from .target_group import TargetGroup
from .phishing_email_template import PhishingEmailTemplate
from .execution import Execution
from .attachment import Attachment
from .phishing_email import PhishingEmail

__all__ = [
    "db",
    "BaseModel",
    "Target",
    "Group",
    "TargetGroup",
    "PhishingEmailTemplate",
    "Execution",
    "Attachment",
    "PhishingEmail",
]
