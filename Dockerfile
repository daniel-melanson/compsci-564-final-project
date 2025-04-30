# Python virtual environment
FROM docker.io/python:3.13 AS builder

ENV PROJECT_NAME=c2-server
ENV PROJECT_DIR=/usr/src/${PROJECT_NAME}

WORKDIR ${PROJECT_DIR}
COPY Pipfile Pipfile.lock ${PROJECT_DIR}/

# Tell pipenv to install the virtual environment in the project directory
ENV PIPENV_VENV_IN_PROJECT=1
RUN pip install pipenv
RUN pipenv install

# Runtime
FROM docker.io/python:3.13 AS runtime

ENV PROJECT_NAME=c2-server
ENV PROJECT_DIR=/usr/src/${PROJECT_NAME}

# Copy python and virtual environment from builder
RUN mkdir -p ${PROJECT_DIR}/.venv
COPY --from=builder ${PROJECT_DIR}/.venv/ ${PROJECT_DIR}/.venv/

RUN ${PROJECT_DIR}/.venv/bin/python -c "import celery; print(celery.__version__)"

WORKDIR ${PROJECT_DIR}

COPY ./src ${PROJECT_DIR}/src