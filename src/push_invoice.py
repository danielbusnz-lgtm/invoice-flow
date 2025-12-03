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

class InvoiceLine(BaseModel):
    item: str
    rate: float
    quantity: float = Field(default=1.0, gt=0)
    description: Optional[str] = None

    @property
    def amount(self) -> float:
        return self.rate * self.quantity


class InvoiceDraft(BaseModel):
    vendor_display_name: str
    vendor_company_name: Optional[str] = None
    line_items: List[InvoiceLine]
    memo: Optional[str] = None
    tax: Optional[float]=None
    total_amount: Optional[float] = None


class QuickbooksInvoiceService:
    def __init__(self) -> None:
        self.auth_client = AuthClient(
            client_id=os.getenv('CLIENT_ID'),
            client_secret=os.getenv('CLIENT_SECRET'),
            environment='production',
            redirect_uri='https://developer.intuit.com/v2/OAuth2Playground/RedirectUrl',
        )

        self.qb_client = QuickBooks(
            auth_client=self.auth_client,
            refresh_token=os.getenv('QB_REFRESH_TOKEN'),
            company_id=os.getenv('QB_REALM_ID'),
	    )
        self._save_refresh_token()
    
    def _save_refresh_token(self):
        new_token= self.qb_client.auth_client.refresh_token
        from pathlib import Path
        env_path = Path(__file__).parent.parent/ '.env'
        with open(env_path, 'r') as f:
            lines = f.readlines()
        with open(env_path, 'w') as f:
            for line in lines:
                if line.startswith('QB_REFRESH_TOKEN='):
                    f.write(f'QB_REFRESH_TOKEN={new_token}\n')
                else:
                    f.write(line)
        
    def ensure_vendors(self, draft) -> Vendor:
        all_vendors=Vendor.all(qb =self.qb_client)
       
        for vendor in all_vendors:
            if draft.vendor_display_name.lower().strip()==vendor.DisplayName.lower().strip():
                
                return vendor
        best_match= None
        best_ratio= 0.8
        vendor=Vendor() 

        
        for vendor in all_vendors:
            ratio = SequenceMatcher(None, draft.vendor_display_name.lower(),vendor.DisplayName.lower()).ratio()

    
            if ratio > best_ratio:
                best_ratio= ratio
                best_match=vendor
        if best_match:
                return best_match
       
        else:
                vendor = Vendor()
                vendor.DisplayName= draft.vendor_display_name
                vendor.save(qb=self.qb_client)
                return vendor

    def push_invoice(self,draft) -> Bill:
        bill = Bill()
        vendor = self.ensure_vendors(draft)
        bill.VendorRef=vendor.to_ref()
        total= draft.total_amount
        for line in draft.line_items:
            qb_line = AccountBasedExpenseLine()
            
            qb_line.DetailType = "AccountBasedExpenseLineDetail"
            qb_line.Amount=line.amount
            
            rounded_total= round(total,2)
            account_ref = Ref()
            account_ref.type = "Account"
            account_ref.value = 1  # Your expense account ID
            qb_line.AccountBasedExpenseLineDetail =AccountBasedExpenseLineDetail()
            qb_line.AccountBasedExpenseLineDetail.AccountRef = account_ref  
            qb_line.Description = f"{line.item} - Qty: {line.quantity} @${line.rate}" 
            bill.Line.append(qb_line)
        bill.save(qb=self.qb_client)
        print(f"Total '{rounded_total}'")
        return bill

       
