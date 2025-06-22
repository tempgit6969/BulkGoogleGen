# create_user_from_txt.py (Final Version)

import os
import json
import random
import string
import smtplib
from string import Template
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# The scopes required for the Admin SDK Directory API to manage users.
SCOPES = ['https://www.googleapis.com/auth/admin.directory.user']

def generate_password(length=12):
    """Generates a random, secure password (used internally for API)."""
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choices(characters, k=length))

def load_creds():
    """Loads Google Workspace API credentials from environment variables."""
    try:
        token_info = json.loads(os.environ['TOKEN_JSON'])
        creds = Credentials.from_authorized_user_info(token_info, SCOPES)
        
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        
        return creds
    except KeyError:
        print("[ERROR] 'TOKEN_JSON' environment variable not set.")
        return None
    except json.JSONDecodeError:
        print("[ERROR] 'TOKEN_JSON' contains invalid JSON.")
        return None

def parse_txt(file_path):
    """Parses a key-value text file into a dictionary."""
    fields = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip() or line.strip().startswith('#'):
                    continue
                if ':' in line:
                    key, value = line.split(':', 1)
                    fields[key.strip()] = value.strip()
    except FileNotFoundError:
        print(f"[ERROR] Input file not found at: {file_path}")
        return None
    return fields

def create_user(service, user_info):
    """
    Creates a new Google Workspace user.
    The password generated here is a placeholder to satisfy the API and is never used.
    """
    placeholder_password = generate_password()
    
    user_body = {
        "primaryEmail": user_info.get('primaryEmail'),
        "name": {
            "givenName": user_info.get('givenName'),
            "familyName": user_info.get('familyName')
        },
        "password": placeholder_password,
        "changePasswordAtNextLogin": True,
        "recoveryEmail": user_info.get('recoveryEmail'),
        "recoveryPhone": user_info.get('recoveryPhone'),
        "orgUnitPath": user_info.get('orgUnitPath', '/')
    }

    user_body_cleaned = {k: v for k, v in user_body.items() if v}
    
    if not all(user_body_cleaned.get(key) for key in ['primaryEmail', 'name']):
        print("[ERROR] Missing essential user information. Cannot create user.")
        return None

    try:
        print(f"Attempting to create user: {user_body_cleaned.get('primaryEmail')}...")
        result = service.users().insert(body=user_body_cleaned).execute()
        print(f"Successfully created user: {result['primaryEmail']}")
        # We only return the username, as the password is not to be used.
        return result['primaryEmail']
    except HttpError as e:
        print(f"[ERROR] Failed to create user. API returned an error: {e}")
        return None

def send_activation_email(to, username, given_name):
    """Sends an email with instructions for the user to set their own password."""
    # Note: This function no longer accepts a 'password' argument.
    html_content = load_email_template('templates/email_template.html', {
        'username': username,
        'givenName': given_name
    })

    if not html_content:
        print("[INFO] Could not load email template. Skipping email notification.")
        return

    try:
        smtp_user = os.environ['EMAIL_SMTP_USER']
        smtp_pass = os.environ['EMAIL_SMTP_PASS']
    except KeyError as e:
        print(f"[ERROR] Missing environment variable for sending email: {e}. Skipping email.")
        return

    msg = MIMEMultipart('alternative')
    msg['Subject'] = 'Activate Your New Google Workspace Account'
    msg['From'] = smtp_user
    msg['To'] = to
    msg.attach(MIMEText(html_content, 'html'))

    try:
        print(f"Sending activation instructions to {to}...")
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        print("Email sent successfully.")
    except smtplib.SMTPException as e:
        print(f"[ERROR] Failed to send email. SMTP Error: {e}")

def load_email_template(filepath, values):
    """Loads an HTML email template and substitutes placeholder values."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            template = Template(f.read())
        return template.substitute(values)
    except FileNotFoundError:
        print(f"[ERROR] Email template not found at: {filepath}")
        return None

def main():
    """Main function to orchestrate the user creation process."""
    file_path = os.getenv('TXT_FILE')
    if not file_path:
        print("[ERROR] Environment variable 'TXT_FILE' is not set.")
        return
    
    print("--- Starting User Creation Script (Secure Activation Flow) ---")
    user_info = parse_txt(file_path)
    if not user_info:
        return

    creds = load_creds()
    if not creds:
        return

    try:
        service = build('admin', 'directory_v1', credentials=creds)
        username = create_user(service, user_info)
        
        if username:
            send_to_email = user_info.get('EmailToSendCred')
            given_name = user_info.get('givenName')
            if send_to_email and given_name:
                send_activation_email(send_to_email, username, given_name)
            else:
                print("[WARN] 'EmailToSendCred' or 'givenName' not found in TXT file. Cannot send activation email.")
        else:
            print("[INFO] User creation failed. No activation email sent.")
    except Exception as e:
        print(f"[FATAL_ERROR] An unexpected error occurred: {e}")
    
    print("--- Script Finished ---")


if __name__ == "__main__":
    main()
