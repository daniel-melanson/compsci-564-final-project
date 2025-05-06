import csv
import json
import random

import faker

fake = faker.Faker()


def rand_department():
    return random.choice(
        [
            "L530",
            "L531",
            "L532",
            "L533",
            "L534",
            "P720",
            "P721",
            "P722",
            "P723",
            "P724",
        ]
    )


def rand_employee():
    data = {
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "company": "MITRE",
        "job_title": fake.job(),
        "phone_number": fake.phone_number(),
        "department": rand_department(),
        "manager": fake.name(),
    }

    email = f"{data['first_name'].lower()}.{data['last_name'].lower()}@mitre.org"
    groups = f"MITRE,MITRE_{data['department']}"

    return email, json.dumps(data), groups


with open("targets.csv", "w") as f:
    writer = csv.writer(f)
    writer.writerow(["email", "data", "groups"])

    _, data, groups = rand_employee()
    writer.writerow(["cs564-melanson-lacy@proton.me", data, groups])

    for _ in range(9):
        writer.writerow(rand_employee())
