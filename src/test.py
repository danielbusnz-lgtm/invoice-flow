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

from main import get_or_create_label
from main import load_creds

service = build("gmail", "v1", credentials=load_creds())


label = get_or_create_label(service, "daniel" )

