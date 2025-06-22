import os
import json
import base64
import smtplib
from string import Template
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Load email template
EMAIL_TEMPLATE_PATH = "templates/email_template.html"

def load_template(path):
    with open(path, "r", encoding="utf-8") as f:
        return Template(f.read())

def parse_txt(file_path):
    with open(file_path, 'r') as f:
        lines = [line.strip() for line in f.readlines() if line.strip() and ':' in line]
    data = {}
    for line in lines:
        key, value = map(str.strip, line.split(':', 1))
        data[key] = value
    return data

def create_user(service, user_info, password):
    user_body = {
        "primaryEmail": user_info["primaryEmail"],
        "name": {
            "givenName": user_info["givenName"],
            "familyName": user_info.get("familyName", "User")
        },
        "password": password,
        "changePasswordAtNextLogin": True
    }

    if user_info.get("recoveryEmail"):
        user_body["recoveryEmail"] = user_info["recoveryEmail"]
    if user_info.get("recoveryPhone"):
        user_body["recoveryPhone"] = user_info["recoveryPhone"]
    if user_info.get("orgUnitPath"):
        user_body["orgUnitPath"] = user_info["orgUnitPath"]

    return service.users().insert(body=user_body).execute()

def send_email(smtp_user, smtp_pass, to_email, subject, html_content):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to_email

    part2 = MIMEText(html_content, "html")
    msg.attach(part2)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, to_email, msg.as_string())

def main():
    txt_file = os.getenv("TXT_FILE")
    if not txt_file or not os.path.exists(txt_file):
        raise FileNotFoundError(f"No TXT file found at: {txt_file}")

    user_info = parse_txt(txt_file)
    creds = Credentials.from_authorized_user_info(json.loads(os.getenv("TOKEN_JSON")), [
        'https://www.googleapis.com/auth/admin.directory.user']
    )
    service = build('admin', 'directory_v1', credentials=creds)

    password = base64.urlsafe_b64encode(os.urandom(8)).decode("utf-8")
    user = create_user(service, user_info, password)

    email_template = load_template(EMAIL_TEMPLATE_PATH)
    email_html = email_template.substitute(
        name=user_info["givenName"],
        email=user_info["primaryEmail"],
        password=password
    )

    send_email(
        smtp_user=os.getenv("EMAIL_SMTP_USER"),
        smtp_pass=os.getenv("EMAIL_SMTP_PASS"),
        to_email=user_info["EmailToSendCred"],
        subject="Your new Google Workspace account",
        html_content=email_html
    )

if __name__ == "__main__":
    main()
