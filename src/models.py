from peewee import *
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

db = PostgresqlDatabase(
    "c2_server", user="postgres", password="postgres", host="db", port=5432
)


class BaseModel(Model):
    class Meta:
        database = db


class Target(BaseModel):
    id = AutoField(primary_key=True)
    first_name = CharField()
    last_name = CharField()
    email = CharField()
    data = TextField()
    ip = CharField()
    port = IntegerField()


class TargetGroup(BaseModel):
    id = AutoField(primary_key=True)
    name = CharField()
    targets = ManyToManyField(Target, backref="target_groups")


class Implant(BaseModel):
    id = AutoField(primary_key=True)
    name = CharField()
    path = CharField()


class Template(BaseModel):
    id = AutoField(primary_key=True)
    name = CharField()
    path = CharField()
