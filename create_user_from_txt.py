# create_user_from_txt.py

import os, json, random, string, smtplib
from string import Template
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/admin.directory.user']

def generate_password(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def load_creds():
    token = json.loads(os.environ['TOKEN_JSON'])
    creds = Credentials.from_authorized_user_info(token, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds

def parse_txt(file_path):
    with open(file_path, 'r') as f:
        content = f.read()
    fields = {}
    for line in content.splitlines():
        key, value = line.split(':', 1)
        fields[key.strip()] = value.strip()
    return fields

def create_user(service, user_info):
    password = generate_password()
    user = {
        "primaryEmail": user_info['primaryEmail'],
        "name": {
            "givenName": user_info['givenName'],
            "familyName": "User"
        },
        "password": password,
    }
    result = service.users().insert(body=user).execute()
    return result['primaryEmail'], password

def load_email_template(filepath, values):
    with open(filepath, 'r', encoding='utf-8') as f:
        template = Template(f.read())
    return template.substitute(values)

def send_email(to, username, password, given_name):
    html = load_email_template('templates/email_template.html', {
        'username': username,
        'password': password,
        'givenName': given_name
    })

    msg = MIMEMultipart('alternative')
    msg['Subject'] = 'Your Google Workspace Account Details'
    msg['From'] = os.environ['EMAIL_SMTP_USER']
    msg['To'] = to

    msg.attach(MIMEText(html, 'html'))

    server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    server.login(os.environ['EMAIL_SMTP_USER'], os.environ['EMAIL_SMTP_PASS'])
    server.send_message(msg)
    server.quit()

def main():
    file_path = os.getenv('TXT_FILE')
    user_info = parse_txt(file_path)
    creds = load_creds()
    service = build('admin', 'directory_v1', credentials=creds)
    username, password = create_user(service, user_info)
    send_email(user_info['EmailToSendCred'], username, password, user_info['givenName'])

if __name__ == "__main__":
    main()
