import base64
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.labels",
    "https://www.googleapis.com/auth/gmail.modify"
]


def load_creds():
    """Load Gmail OAuth credentials"""
    project_root = Path(__file__).parent.parent.parent
    token_path = project_root / "token.json"
    credentials_path = project_root / "credentials.json"

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(credentials_path), SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(token_path, "w") as token:
            token.write(creds.to_json())

    return creds


def decode_data(encoded):
    """Decode base64 URL-safe encoded string"""
    if not encoded:
        return None
    padded = encoded + "=" * (-len(encoded) % 4)
    return base64.urlsafe_b64decode(padded).decode("utf-8")


def decode_bytes(encoded: str) -> bytes:
    """Decode base64 URL-safe encoded bytes"""
    if not encoded:
        return b""
    padded = encoded + "=" * (-len(encoded) % 4)
    return base64.urlsafe_b64decode(padded)


def get_or_create_label(service, label_name):
    """Get or create a Gmail label"""
    results = service.users().labels().list(userId='me').execute()
    labels = results.get('labels', [])

    for label in labels:
        if label['name'].lower() == label_name.lower():
            return label['id']

    label_object = {
        'name': label_name,
        'labelListVisibility': 'labelShow',
        'messageListVisibility': 'show'
    }
    created_label = service.users().labels().create(
        userId='me',
        body=label_object
    ).execute()

    return created_label['id']
