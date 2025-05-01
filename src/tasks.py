from celery import Celery

app = Celery('c2_server', broker='redis://redis:6379/0', backend='redis://redis:6379/0')

@app.task
def execute_command(target, command):
    pass

@app.task
def execute_script(target, command):
    pass
