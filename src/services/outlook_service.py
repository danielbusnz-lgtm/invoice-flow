import os
import base64
import webbrowser
from pathlib import Path
from typing import Optional

import msal
import httpx
from dotenv import load_dotenv
from bs4 import BeautifulSoup

from parsers.pdf_parser import extract_text_from_pdf

load_dotenv()

MS_GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
SCOPES = ["User.Read", "Mail.ReadWrite"]

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
TOKEN_PATH = PROJECT_ROOT / "ms_refresh_token.txt"
ATTACHMENTS_DIR = PROJECT_ROOT / "attachments"


def _get_access_token():
    """Authenticate with Microsoft and return an access token.

    Uses a stored refresh token if available, otherwise opens
    a browser for interactive login.
    """
    client_id = os.getenv("MICROSOFT_CLIENT_ID")
    client_secret = os.getenv("MICROSOFT_CLIENT_SECRET")
    tenant_id = os.getenv("MICROSOFT_TENANT_ID")

    authority = f"https://login.microsoftonline.com/{tenant_id}"

    app = msal.ClientApplication(
        client_id=client_id,
        authority=authority,
        client_credential=client_secret,
    )

    # Try refresh token first
    refresh_token = None
    if TOKEN_PATH.exists():
        refresh_token = TOKEN_PATH.read_text().strip()

    if refresh_token:
        token_response = app.acquire_token_by_refresh_token(
            refresh_token, scopes=SCOPES
        )
    else:
        # Interactive login
        auth_url = app.get_authorization_request_url(SCOPES)
        webbrowser.open(auth_url)
        authorization_code = input("Enter the authorization code: ")

        if not authorization_code:
            raise ValueError("Authorization code is empty")

        token_response = app.acquire_token_by_authorization_code(
            code=authorization_code,
            scopes=SCOPES,
        )

    if "access_token" not in token_response:
        raise Exception(
            "Failed to acquire access token: " + str(token_response)
        )

    # Save refresh token for next time
    if "refresh_token" in token_response:
        TOKEN_PATH.write_text(token_response["refresh_token"])

    return token_response["access_token"]


def fetch_messages_with_attachments(max_results: int = 10, query: Optional[str] = None):
    """Fetch Outlook messages with attachments.

    Yields the same tuple format as gmail_service:
        (message_id, subject, message_text, attachments)
    """
    access_token = _get_access_token()
    headers = {"Authorization": f"Bearer {access_token}"}

    ATTACHMENTS_DIR.mkdir(exist_ok=True)

    # Fetch messages
    endpoint = f"{MS_GRAPH_BASE_URL}/me/messages"
    params = {
        "$top": max_results,
        "$select": "id,subject,body,hasAttachments,from",
        "$orderby": "receivedDateTime desc",
        "$filter": "hasAttachments eq true",
    }

    response = httpx.get(endpoint, headers=headers, params=params, timeout=30.0)
    if response.status_code != 200:
        raise Exception(f"Failed to retrieve emails: {response.text}")

    messages = response.json().get("value", [])

    for msg in messages:
        message_id = msg["id"]
        subject = msg.get("subject", "")

        # Extract body text
        body_content = msg.get("body", {}).get("content", "")
        body_type = msg.get("body", {}).get("contentType", "text")

        if body_type == "html":
            soup = BeautifulSoup(body_content, "html.parser")
            message_text = soup.get_text(separator="", strip=True)
        else:
            message_text = body_content

        # Fetch attachments
        attachments = []
        if msg.get("hasAttachments"):
            att_endpoint = f"{MS_GRAPH_BASE_URL}/me/messages/{message_id}/attachments"
            att_response = httpx.get(att_endpoint, headers=headers, timeout=30.0)

            if att_response.status_code == 200:
                for att in att_response.json().get("value", []):
                    # Skip inline images
                    if att.get("isInline", False):
                        continue

                    filename = att.get("name", "")
                    content_bytes_b64 = att.get("contentBytes", "")

                    if not filename or not content_bytes_b64:
                        continue

                    binary_data = base64.b64decode(content_bytes_b64)

                    if filename.lower().endswith(".pdf"):
                        temp_path = ATTACHMENTS_DIR / filename
                        temp_path.write_bytes(binary_data)
                        pdf_text = extract_text_from_pdf(temp_path)
                        attachments.append((filename, pdf_text))
                    else:
                        attachments.append((filename, binary_data))

        yield message_id, subject, message_text, attachments


# Mapping from internal label names to Outlook category names
LABEL_TO_CATEGORY = {
    "invoice": "Invoice",
    "shipping": "Shipping",
    "insurance": "Insurance",
    "client_communications": "Client Communications",
    "none": "Uncategorized",
}


def label_message(message_id: str, label: str):
    """Apply a category label to an Outlook message.

    Uses the Microsoft Graph API to set the categories
    property on the specified message.
    """
    access_token = _get_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    category = LABEL_TO_CATEGORY.get(label, label)
    endpoint = f"{MS_GRAPH_BASE_URL}/me/messages/{message_id}"

    response = httpx.patch(
        endpoint,
        headers=headers,
        json={"categories": [category]},
        timeout=30.0,
    )

    if response.status_code != 200:
        raise Exception(
            f"Failed to label message {message_id}: {response.text}"
        )

    return response.json()
