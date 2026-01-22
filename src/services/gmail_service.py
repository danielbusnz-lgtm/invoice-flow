import os.path
import base64
from pathlib import Path
from typing import Optional
from bs4 import BeautifulSoup
from googleapiclient.discovery import build

# Local imports
from parsers.pdf_parser import extract_text_from_pdf
from utils.auth import load_creds, decode_data, decode_bytes, get_or_create_label

# Build Gmail service
service = build("gmail", "v1", credentials=load_creds())


def fetch_messages_with_attachments(max_results: int = 10, query: Optional[str] = None):
    """Fetch Gmail messages with attachments"""
    # Get project root directory for attachments
    project_root = Path(__file__).parent.parent.parent
    attachments_dir = project_root / "attachments"

    list_params = {
        "userId": "me",
        "maxResults": max_results,
        #"q": " -label:ai_checked"
    }
    results = service.users().messages().list(**list_params).execute()
    for ref in results.get("messages", []):
        msg = service.users().messages().get(
            userId="me",
            id=ref["id"],
            format="full",
        ).execute()
        payload = msg.get("payload", {})
        headers = {
            h.get("name", "").lower(): h.get("value", "")
            for h in payload.get("headers", [])
        }
        subject = headers.get("subject", "")
        body = payload.get("body", {})
        raw_data = body.get("data", "")
        label_id = get_or_create_label(service, "ai_checked")
        service.users().messages().modify(
            userId='me',
            id=ref["id"],
            body={'addLabelIds': [label_id]}
        ).execute()

        if not raw_data:
            for part in payload.get("parts", []):
                raw_data = part.get("body", {}).get("data", "")
                if raw_data:
                    break

        message_text = ""
        if raw_data:
            decoded = decode_data(raw_data)
            if decoded:
                soup = BeautifulSoup(decoded, "html.parser")
                message_text = soup.get_text(separator="", strip=True)

        attachments = []
        parts_to_inspect = [payload]
        while parts_to_inspect:
            part = parts_to_inspect.pop()
            filename = part.get("filename")
            part_body = part.get("body", {})
            inline_data = part_body.get("data")
            if filename and inline_data:
                binary_data = decode_bytes(inline_data)

                if filename.endswith('.pdf'):
                    temp_path = attachments_dir / filename
                    temp_path.parent.mkdir(exist_ok=True)
                    temp_path.write_bytes(binary_data)
                    pdf_text = extract_text_from_pdf(temp_path)
                    attachments.append((filename, pdf_text))
                else:
                    attachments.append((filename, binary_data))
                continue

            attachment_id = part_body.get("attachmentId")
            if filename and attachment_id:
                attachment = service.users().messages().attachments().get(
                    userId="me",
                    messageId=ref["id"],
                    id=attachment_id,
                ).execute()
                binary_data = decode_bytes(attachment.get("data", ""))
                if filename.lower().endswith('.pdf'):
                    temp_path = attachments_dir / filename
                    temp_path.parent.mkdir(exist_ok=True)
                    temp_path.write_bytes(binary_data)
                    pdf_text = extract_text_from_pdf(temp_path)
                    attachments.append((filename, pdf_text))
                else:
                    attachments.append((filename, binary_data))

            parts_to_inspect.extend(part.get("parts", []))

        yield ref["id"], subject, message_text, attachments
