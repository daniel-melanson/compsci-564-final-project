"""
This module contains all database logic and ORM models for the C2 server.
"""
import psycopg2
from playhouse.postgres_ext import *

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

from .attachment import Attachment
from .base import BaseModel
from .email_account import EmailAccount
from .execution import Execution
from .group import Group
from .phishing_email import PhishingEmail
from .phishing_email_template import PhishingEmailTemplate
from .target import Target, TargetGroup

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
    "EmailAccount",
]
