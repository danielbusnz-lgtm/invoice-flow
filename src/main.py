from quickbooks.exceptions import QuickbooksException
import os.path
from enum import Enum
from pydantic import BaseModel
import base64
from bs4 import BeautifulSoup
from pydantic import BaseModel
from openai import OpenAI
import os
from typing import List, Literal, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from pathlib import Path
from pdf_parser import extract_text_from_pdf
from push_invoice import InvoiceDraft, InvoiceLine, QuickbooksInvoiceService
from attachments import fetch_messages_with_attachments
import time
from attachments import fetch_messages_with_attachments
import glob
import os

# If modifying these scopes, delete the file token.json.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.labels",
    "https://www.googleapis.com/auth/gmail.modify"
]


def load_creds():
  # Get project root directory (parent of src/)
  project_root = Path(__file__).parent.parent
  token_path = project_root / "token.json"
  credentials_path = project_root / "credentials.json"

  creds = None
  # The file token.json stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  if token_path.exists():
    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
          str(credentials_path), SCOPES
        )
        creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open(token_path, "w") as token:
      token.write(creds.to_json())
  return creds
service = build("gmail", "v1", credentials=load_creds())


#decode the emails using utf-8
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




#make sure there is a proper label
def get_or_create_label(service, label_name):
      """Get label ID by name, or create if it doesn't exist"""
      # List all labels
      results = service.users().labels().list(userId='me').execute()
      labels = results.get('labels', [])

      # Check if label exists
      for label in labels:
          if label['name'].lower() == label_name.lower():
              return label['id']

      # Create label if it doesn't exist
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


#structured output class
class LabelSort(BaseModel):
    label: Literal["invoice", "none"]



#function for using open ai to classifiy emails as either invoice or not


def invoice_label(message_text: str, attachments: list , client: Optional[OpenAI] = None):
    if client is None:
         client = OpenAI()

    context= message_text

    if attachments:
        context +="\n\nAttachments found:\n"
        for filename, data in attachments:
            context += f"- {filename}\n"
        print(context)
     
    response = client.responses.parse(
        model="gpt-4o-2024-08-06",
        input=[
        {"role": "system", "content": "Extract wheter or not the following email is an invoice or not. If there is an attachment, it is likely an invoice. If it is an email return: invoice and if not return: none."},
        {
            "role": "user",
            "content": context,
        },
    ],
        text_format=LabelSort,  # your structured output class
    )


    return response.output_parsed.label





def ai_invoice(message_text: str, attachments: list = None, client: Optional[OpenAI] = None):
    client = OpenAI()
    
       

    project_root = Path(__file__).parent.parent
    attachments_dir = project_root / "attachments"
       
    if attachments :
       
            file = attachments[0]
            filename = file[0]   
            temp_path = attachments_dir / filename 
        
            list_of_files = glob.glob(f"{attachments_dir}/*")
           
            latest_file= max(list_of_files, key=os.path.getctime)
             
          
            print(latest_file)           


            file = client. files.create(
                file = open(latest_file, "rb"),
                purpose = "user_data"
            )
            
                       
            
            response =  client.responses.create(
                model="gpt-4o-2024-08-06",
                input=[
                    {
                        "role":"user",
                        "content":[
                            {
                                "type":"input_file",
                                "file_id": file.id,
                            },
                            {
                                "type": "input_text",
                                "text": "parse this invoice",

                            },
                        ]
                    }
                ]

            )
            event = response.output_text
            return event

def build_invoice_draft(message_text: str, client: Optional[OpenAI] = None, attachments:list=None) -> Optional[InvoiceDraft]:
    if client is None:
        client = OpenAI()

    context= message_text
    if attachments:
        print("has attachments")
        context +="\n\nAttachments found:\n"
        for filename, data in attachments:
            context += f"-{filename}\n"
        print(context)

    response = client.responses.parse(
        model="gpt-4o-2024-08-06",
        input=[
            {
                "role": "system",
                "content": (
                    "Extract structured invoice data from the email. "
                    "Always respond with JSON matching the schema. "
                    "If you do not find invoice information, return an empty items list."
                    "Our company name is Cape Property Pros, and we are always the reciever of the invoice"
                ),
            },
            {"role": "user", "content": context},
        ],
        text_format=InvoiceDraft,
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
    )


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
    
    
    # Process messages
    for idx, (message_id, subject, message_text, attachments) in enumerate(messages, start=1):
        draft=None
        label = invoice_label(message_text, attachments, client=openai_client)
        print(f"[{idx}/{len(messages)}] {message_id}: subject -> {subject} label -> {label}")
        print(attachments)

        if label== "invoice":
            print("starting ai_invoice process")
            
            draft = ai_invoice(message_text=message_text, attachments=attachments,client=openai_client)
            print(draft)
            # If we have PDF attachments, try to extract invoice from them
           

        for filename, data in attachments:

                print(f"Attachment: {filename}, Type: {type(data).__name__}, IsString: {isinstance(data, str)}")
                if isinstance(data, str):  # PDF text already extracted
                    print(f"[{idx}/{len(messages)}] {message_id}: processing PDF {filename}")
                    pdf_draft = ai_invoice(message_text=data, client=openai_client)
                    if pdf_draft and pdf_draft.line_items:
                        draft = pdf_draft
                        break
                else:  # Binary attachment (non-PDF)
                    target = download_dir / filename
                    target.write_bytes(data)
                    print(f"[{idx}/{len(messages)}] {message_id}: saved attachment {filename}")

        # If we have a valid draft, push to QuickBooks
        if draft:
            print(f"[{idx}/{len(messages)}] {message_id}: line items:")
            #delete this line service = QuickbooksInvoiceService()

            ####TAKE A LOOK AT THIS
            qb_service.push_invoice(draft)
            for line in draft.line_items:
                print("   ", line.model_dump())

            # Calculate and verify total
            calculated_total = draft.total_amount.astype(float)
            #sum(line.amount for line in draft.line_items)+tax
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



