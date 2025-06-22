# create_user_from_txt.py

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
    """Generates a random, secure password."""
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choices(characters, k=length))

def load_creds():
    """Loads Google Workspace API credentials from environment variables."""
    try:
        # Load token information from the environment variable.
        token_info = json.loads(os.environ['TOKEN_JSON'])
        creds = Credentials.from_authorized_user_info(token_info, SCOPES)
        
        # If credentials have expired and a refresh token is available, refresh them.
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        
        return creds
    except KeyError:
        print("[ERROR] 'TOKEN_JSON' environment variable not set. Please set it with your token credentials.")
        return None
    except json.JSONDecodeError:
        print("[ERROR] 'TOKEN_JSON' contains invalid JSON.")
        return None

def parse_txt(file_path):
    """Parses a key-value text file into a dictionary."""
    fields = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        for line in content.splitlines():
            # Skip empty lines or lines that are comments
            if not line or line.strip().startswith('#'):
                continue
            # Split line into key and value at the first colon
            if ':' in line:
                key, value = line.split(':', 1)
                fields[key.strip()] = value.strip()
    except FileNotFoundError:
        print(f"[ERROR] Input file not found at: {file_path}")
        return None
        
    return fields

def create_user(service, user_info):
    """
    Creates a new Google Workspace user using the provided information.
    Includes recovery and organizational details to ensure account stability.
    """
    password = generate_password()
    
    # Construct the user object for the API call.
    # Use .get() to safely access optional fields from the user_info dictionary.
    user_body = {
        "primaryEmail": user_info.get('primaryEmail'),
        "name": {
            "givenName": user_info.get('givenName'),
            "familyName": user_info.get('familyName')
        },
        "password": password,
        "changePasswordAtNextLogin": True,
        "recoveryEmail": user_info.get('recoveryEmail'),
        "recoveryPhone": user_info.get('recoveryPhone'),
        "orgUnitPath": user_info.get('orgUnitPath', '/') # Default to root OU if not specified
    }

    # The API will error if keys with None values are sent.
    # This dictionary comprehension removes them before making the call.
    user_body_cleaned = {k: v for k, v in user_body.items() if v is not None}
    
    # Check for essential fields before making the API call.
    if not all([user_body_cleaned.get('primaryEmail'), user_body_cleaned.get('name', {}).get('givenName'), user_body_cleaned.get('name', {}).get('familyName')]):
        print("[ERROR] Missing essential user information (primaryEmail, givenName, familyName). Cannot create user.")
        return None, None

    try:
        print(f"Attempting to create user: {user_body_cleaned.get('primaryEmail')}...")
        result = service.users().insert(body=user_body_cleaned).execute()
        print(f"Successfully created user: {result['primaryEmail']}")
        return result['primaryEmail'], password
    except HttpError as e:
        print(f"[ERROR] Failed to create user. API returned an error: {e}")
        return None, None

def load_email_template(filepath, values):
    """Loads an HTML email template and substitutes placeholder values."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            template = Template(f.read())
        return template.substitute(values)
    except FileNotFoundError:
        print(f"[ERROR] Email template not found at: {filepath}")
        return None
    except KeyError as e:
        print(f"[ERROR] Missing a value in the email template: {e}")
        return None

def send_email(to, username, password, given_name):
    """Sends the new account credentials to the specified email address."""
    html_content = load_email_template('templates/email_template.html', {
        'username': username,
        'password': password,
        'givenName': given_name
    })

    if not html_content:
        print("[INFO] Could not load email template. Skipping email notification.")
        return

    try:
        smtp_user = os.environ['EMAIL_SMTP_USER']
        smtp_pass = os.environ['EMAIL_SMTP_PASS']
    except KeyError as e:
        print(f"[ERROR] Missing environment variable for sending email: {e}. Skipping email notification.")
        return

    msg = MIMEMultipart('alternative')
    msg['Subject'] = 'Your New Google Workspace Account Details'
    msg['From'] = smtp_user
    msg['To'] = to
    msg.attach(MIMEText(html_content, 'html'))

    try:
        print(f"Sending credentials to {to}...")
        # Connect to Gmail's SMTP server over SSL
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        print("Email sent successfully.")
    except smtplib.SMTPException as e:
        print(f"[ERROR] Failed to send email. SMTP Error: {e}")

def main():
    """Main function to orchestrate the user creation process."""
    # Get the path to the input file from an environment variable.
    file_path = os.getenv('TXT_FILE')
    if not file_path:
        print("[ERROR] Environment variable 'TXT_FILE' is not set. Please specify the path to your user data file.")
        return
    
    print("--- Starting User Creation Script ---")
    user_info = parse_txt(file_path)
    if not user_info:
        return # Error message is handled in parse_txt

    creds = load_creds()
    if not creds:
        return # Error message is handled in load_creds

    try:
        service = build('admin', 'directory_v1', credentials=creds)
        username, password = create_user(service, user_info)
        
        if username and password:
            send_to_email = user_info.get('EmailToSendCred')
            if send_to_email:
                send_email(send_to_email, username, password, user_info['givenName'])
            else:
                print("[WARN] 'EmailToSendCred' not found in TXT file. Cannot send credentials email.")
        else:
            print("[INFO] User creation failed. No credentials to send.")
    except Exception as e:
        print(f"[FATAL_ERROR] An unexpected error occurred: {e}")
    
    print("--- Script Finished ---")


if __name__ == "__main__":
    main()

