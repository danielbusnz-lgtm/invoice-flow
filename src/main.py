# Standard library imports
import os
import os.path
import base64
import time
import glob
import tempfile
from enum import Enum
from pathlib import Path
from typing import List, Literal, Optional
import datetime
# Third-party imports
import pandas as pd
from bs4 import BeautifulSoup
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
from pdf2image import convert_from_path, convert_from_bytes

# Google API imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# QuickBooks imports
from quickbooks.exceptions import QuickbooksException

# Local imports
from pdf_parser import extract_text_from_pdf
from quickbooks_service import InvoiceDraft, InvoiceLine, QuickbooksInvoiceService
from gmail import fetch_messages_with_attachments


# Configuration
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env")
refresh_token = os.getenv('REFRESH_TOKEN')

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.labels",
    "https://www.googleapis.com/auth/gmail.modify"
]


# Pydantic Models
class LabelSort(BaseModel):
    label: Literal["invoice", "none"]


class InvoiceData(BaseModel):
    vendor_display_name: str
    memo: Optional[str] = None
    line_items: List[InvoiceLine]
    tax: Optional[float] = None
    total_amount: Optional[float] = None
    due_date: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None


# Gmail Authentication
def load_creds():
    project_root = Path(__file__).parent.parent
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

service = build("gmail", "v1", credentials=load_creds())


# Email Decoding Functions
def decode_data(encoded):
    if not encoded:
        return None
    padded = encoded + "=" * (-len(encoded) % 4)
    return base64.urlsafe_b64decode(padded).decode("utf-8")


def decode_bytes(encoded: str) -> bytes:
    if not encoded:
        return b""
    padded = encoded + "=" * (-len(encoded) % 4)
    return base64.urlsafe_b64decode(padded)


# Gmail Label Management
def get_or_create_label(service, label_name):
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


# AI Invoice Processing Functions
def invoice_label(message_text: str, attachments: list , client: Optional[OpenAI] = None):
    """Classify email as invoice or not using OpenAI"""
    if client is None:
         client = OpenAI()

    context= message_text

    if attachments:
        context +="\n\nAttachments found:\n"
        for filename, data in attachments:
            context += f"- {filename}\n"
        

    response = client.responses.parse(
        model="gpt-4o-2024-08-06",
        input=[
        {"role": "system", "content": "Extract wheter or not the following email is an invoice or not. If there is an attachment, it is likely an invoice. If it is an email return: invoice and if not return: none."},
        {
            "role": "user",
            "content": context,
        },
    ],
        text_format=LabelSort,
    )

    return response.output_parsed.label


def pdf_invoice(message_text: str, text , client: Optional[OpenAI] = None):
    """Extract invoice data from PDF text"""
    if client is None:
         client = OpenAI()

    response = client.responses.parse(
        model="gpt-5",
        input=[
        {"role": "system", "content":
            "Extract structured invoice data from this document. "
            "REQUIRED: vendor_display_name, line_items (with item, rate, quantity), total_amount. "
            "OPTIONAL: invoice_number, invoice_date (format: MM/DD/YYYY), due_date (format: MM/DD/YYYY), tax, memo. "
            "Return all dates in MM/DD/YYYY format."},
        {
            "role": "user",
            "content": text,
        },
    ],
        text_format=InvoiceData,
    )

    payload = response.output_parsed

    line_items = [
        InvoiceLine(
            item=item.item,
            rate=item.rate,
            quantity=item.quantity,
            description=item.description,
        )
        for item in payload.line_items
    ]

    return InvoiceDraft(
        vendor_display_name=payload.vendor_display_name,
        memo=payload.memo,
        line_items=line_items,
        tax=payload.tax,
        total_amount=payload.total_amount,
        due_date=payload.due_date,
        invoice_number=payload.invoice_number,
        invoice_date=payload.invoice_date,
    )


def ai_invoice(message_text: str, file_path: None, client: Optional[OpenAI] = None)-> Optional[InvoiceDraft]:
    """Extract invoice data from image using OpenAI vision API"""
    client = OpenAI()

    def create_file(file_path):
        with open(file_path, "rb") as file_content:
            result = client.files.create(
            file=file_content,
            purpose="vision",
        )
        return result.id

    file_id = create_file(file_path)

    response =  client.responses.parse(
        model="gpt-5",
        input=[{
            "role":"user",
            "content":[
                    {
                        "type":"input_text", "text"  : "Extract structured invoice data from this image. REQUIRED: vendor_display_name, line_items (with item, rate, quantity), total_amount. OPTIONAL: invoice_number, invoice_date, due_date, tax, memo. Return all dates in MM/DD/YYYY format."},
                    {
                        "type": "input_image",
                        "file_id": file_id,

                    },
                ],
            }],
             text_format=InvoiceData,
    )
    payload = response.output_parsed

    print(payload)

    line_items = [
        InvoiceLine(
            item=item.item,
            rate=item.rate,
            quantity=item.quantity,
            description=item.description,
        )
        for item in payload.line_items
    ]
    return InvoiceDraft(
        vendor_display_name=payload.vendor_display_name,
        memo=payload.memo,
        line_items=line_items,
        tax=payload.tax,
        total_amount=payload.total_amount,
        due_date=payload.due_date,
        invoice_number=payload.invoice_number,
        invoice_date=payload.invoice_date,
    )


def build_invoice_draft(message_text: str, client: Optional[OpenAI] = None, attachments:list=None) -> Optional[InvoiceDraft]:
    """Build invoice draft from email text"""
    if client is None:
        client = OpenAI()

    context= message_text
    if attachments:
        print("has attachments")
        context +="\qun\nAttachments found:\n"
        for filename, data in attachments:
            context += f"-{filename}\n"
        print(context)

    response = client.responses.parse(
        model="gpt-5",
        input=[
            {
                "role": "system",
                "content": (
                    "Extract structured invoice data from this email. "
                    "REQUIRED: vendor_display_name, line_items (with item, rate, quantity), total_amount. "
                    "OPTIONAL: invoice_number, invoice_date, due_date, tax, memo. "
                    "Return all dates in MM/DD/YYYY format. "
                    "NOTE: Our company is Cape Property Pros (the receiver). "
                    "If no invoice data found, return empty line_items list."
                ),
            },
            {"role": "user", "content": context},
        ],
        text_format=InvoiceData


    )
    payload = response.output_parsed
    print(f"Payload: {payload}")
    if payload:
        print(f"Items: {payload.line_items}")
        print(f"Vendor: {payload.vendor_display_name}")


    if not payload or not payload.line_items:
        return None

    line_items = [
        InvoiceLine(
            item=item.item,
            rate=item.rate,
            quantity=item.quantity,
            description=item.description,
        )
        for item in payload.line_items
        if item.item and item.rate is not None
    ]
    if not line_items or not payload.vendor_display_name:
        return None

    return InvoiceDraft(
        vendor_display_name=payload.vendor_display_name,
        memo=payload.memo,
        line_items=line_items,
        tax=payload.tax,
        total_amount=payload.total_amount,
        due_date=payload.due_date,
        invoice_number=payload.invoice_number,
        invoice_date=payload.invoice_date,
    )


# Main Processing Function
def main():
    try:
        creds = load_creds()
        service = build("gmail", "v1", credentials=creds)
        get_or_create_label(service,"ai_checked")

    except QuickboooksException as e:
        print(f"quickbooks error '{e.message}'(code:'{e.error_code}'")
        print(f"quickbooks detail:'{e.detail}'")
        return

    project_root = Path(__file__).parent.parent
    download_dir = project_root / "attachments"
    download_dir.mkdir(exist_ok=True)
    qb_service = QuickbooksInvoiceService()
    openai_client = OpenAI()
    messages = list(fetch_messages_with_attachments(max_results=10))

    # Process each message
    for idx, (message_id, subject, message_text, attachments) in enumerate(messages, start=1):
        draft=None
        label = invoice_label(message_text, attachments, client=openai_client)
        print(f"[{idx}/{len(messages)}] {message_id}: subject -> {subject} label -> {label}")
        

        project_root = Path(__file__).parent.parent
        attachments_dir = project_root / "attachments"

        # Get the actual attachment file for this email
        latest_file = None
        if attachments:
            attachment_filename = attachments[0][0]
            latest_file = str(attachments_dir / attachment_filename)

        if label== "invoice" and latest_file:
            print("starting ai_invoice process")
            draft = None

            if latest_file.lower().endswith('.pdf'):
                path = Path(latest_file)
                text = extract_text_from_pdf(path)

                if text is None or len(text.strip()) < 10:
                    # Image-based PDF - convert to images
                    print("PDF is image-based, converting to images")
                    with tempfile.TemporaryDirectory() as temp_dir:
                        images_from_path = convert_from_path(latest_file, output_folder=temp_dir, fmt='jpg')

                        image_files = glob.glob(f"{temp_dir}/*.jpg")
                        first_image = image_files[0] if image_files else None

                        if first_image:
                            print("Processing as image")
                            draft = ai_invoice(message_text, file_path=first_image, client=openai_client)
                else:
                    # Text-based PDF
                    print("PDF has extractable text")
                    draft = pdf_invoice(message_text, text=text, client=openai_client)

            elif latest_file.endswith(('.jpeg', '.jpg', '.png')):
                print('THIS IS A JPEG')
                draft = ai_invoice(message_text=message_text, file_path=latest_file, client=openai_client)

            print(f"Draft result: {draft}")

        # Push to QuickBooks if valid draft
        if draft:
            print(f"[{idx}/{len(messages)}] {message_id}: line items:")

            for line in draft.line_items:
                print("   ", line.model_dump())

            # Verify total
            calculated_total = draft.total_amount
            if draft.total_amount is not None:
                if abs(draft.total_amount - calculated_total) > 0.01:
                    print(f"[{idx}/{len(messages)}] {message_id}: total mismatch (draft={draft.total_amount}, calculated={calculated_total})")
            else:
                draft.total_amount = calculated_total
                print(draft.total_amount)

            # Push to QuickBooks
            invoice = qb_service.push_invoice(draft)
            invoice_id = getattr(invoice, "Id", None)
            if invoice_id:
                print(f"[{idx}/{len(messages)}] {message_id}: QuickBooks invoice created (Id={invoice_id})")
            else:
                print(f"[{idx}/{len(messages)}] {message_id}: QuickBooks invoice created")
        else:
            print(f"[{idx}/{len(messages)}] {message_id}: no valid invoice data found")


if __name__ == "__main__":
    main()
