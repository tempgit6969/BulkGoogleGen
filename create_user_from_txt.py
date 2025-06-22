# create_user_google_workspace.py
import os
import json
import logging
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Required API scopes
SCOPES = [
    'https://www.googleapis.com/auth/admin.directory.user',
    'https://www.googleapis.com/auth/admin.directory.user.security'
]

def load_creds():
    """Load Google Workspace API credentials from environment."""
    try:
        token_info = json.loads(os.environ['TOKEN_JSON'])
        creds = Credentials.from_authorized_user_info(token_info, SCOPES)
        
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        
        return creds
    except KeyError:
        logger.error("'TOKEN_JSON' environment variable not set")
        return None
    except json.JSONDecodeError:
        logger.error("'TOKEN_JSON' contains invalid JSON")
        return None

def parse_txt(file_path):
    """Parse key-value text file into dictionary."""
    fields = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if ':' in line:
                    key, value = line.split(':', 1)
                    fields[key.strip()] = value.strip()
        return fields
    except FileNotFoundError:
        logger.error(f"Input file not found: {file_path}")
        return None
    except Exception as e:
        logger.error(f"Error parsing TXT file: {e}")
        return None

def create_user(service, user_info):
    """Create Google Workspace user and trigger official reset email."""
    # Validate required fields
    required_fields = ['primaryEmail', 'givenName', 'familyName']
    if not all(field in user_info for field in required_fields):
        logger.error("Missing essential user information")
        return None

    user_body = {
        "primaryEmail": user_info['primaryEmail'],
        "name": {
            "givenName": user_info['givenName'],
            "familyName": user_info['familyName']
        },
        "password": "TemporaryPassword123!",  # Placeholder
        "changePasswordAtNextLogin": True,
        "orgUnitPath": user_info.get('orgUnitPath', '/'),
        "recoveryEmail": user_info.get('recoveryEmail', ''),
        "recoveryPhone": user_info.get('recoveryPhone', '')
    }

    # Remove empty fields
    user_body = {k: v for k, v in user_body.items() if v}

    try:
        logger.info(f"Creating user: {user_info['primaryEmail']}")
        result = service.users().insert(
            body=user_body,
            sendEmail=True  # Trigger Google's official welcome email
        ).execute()
        
        logger.info(f"Successfully created user: {result['primaryEmail']}")
        return result['primaryEmail']
    except HttpError as e:
        error_details = json.loads(e.content.decode('utf-8'))
        logger.error(f"API Error: {error_details['error']['message']}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error creating user: {e}")
        return None

def send_custom_welcome_email(primary_email, given_name):
    """Send supplemental welcome email with instructions."""
    try:
        # Load HTML template
        with open('templates/welcome_email_template.html', 'r') as f:
            html_template = f.read()
        
        # Personalize content
        html_content = html_template.replace('${givenName}', given_name)
        
        # Get SMTP credentials
        smtp_user = os.environ['EMAIL_SMTP_USER']
        smtp_pass = os.environ['EMAIL_SMTP_PASS']
        
        # Create email
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Your Google Workspace Account Setup'
        msg['From'] = smtp_user
        msg['To'] = primary_email
        msg.attach(MIMEText(html_content, 'html'))
        
        # Send email
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, primary_email, msg.as_string())
        
        logger.info(f"Sent welcome instructions to {primary_email}")
    except FileNotFoundError:
        logger.error("Welcome email template not found")
    except KeyError:
        logger.warning("SMTP credentials not set - skipping supplemental email")
    except Exception as e:
        logger.error(f"Error sending welcome email: {e}")

def main():
    """Orchestrate user creation process."""
    logger.info("--- Google Workspace User Provisioning Started ---")
    
    # Validate environment
    file_path = os.getenv('TXT_FILE')
    if not file_path:
        logger.error("'TXT_FILE' environment variable not set")
        return
    
    # Process user info
    user_info = parse_txt(file_path)
    if not user_info:
        return
    
    creds = load_creds()
    if not creds:
        return
    
    try:
        service = build('admin', 'directory_v1', credentials=creds)
        primary_email = create_user(service, user_info)
        
        if primary_email:
            send_custom_welcome_email(
                primary_email,
                user_info.get('givenName', 'there')
            )
            logger.info(f"Provisioning completed for {primary_email}")
        else:
            logger.error("User creation failed - no further actions")
    
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        logger.info("--- Process Completed ---")

if __name__ == "__main__":
    main()
