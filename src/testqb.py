from quickbooks.objects.customer import Customer
from quickbooks.objects.vendor import Vendor
from quickbooks.objects.bill import Bill
from quickbooks.objects.account import Account
from quickbooks.objects.item import Item
from quickbooks.objects.payment import Payment
from pydantic import BaseModel, Field
from typing import List, Optional
import os
from quickbooks import *
from difflib import SequenceMatcher
from quickbooks.objects.detailline import AccountBasedExpenseLine, AccountBasedExpenseLineDetail, ItemBasedExpenseLine
from quickbooks.objects.base import Ref
from intuitlib.client import AuthClient
from dotenv import load_dotenv
load_dotenv()


client_id=os.getenv('CLIENT_ID')
print(client_id)





