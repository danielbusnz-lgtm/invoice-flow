from quickbooks.objects.customer import Customer
from quickbooks import *
from quickbooks.objects.vendor import Vendor
from quickbooks.objects.bill import Bill
from quickbooks.objects.account import Account
from quickbooks.objects.item import Item
from quickbooks.objects.payment import Payment
from pydantic import BaseModel, Field
from typing import List, Optional
import os
from difflib import SequenceMatcher
from quickbooks.objects.detailline import AccountBasedExpenseLine, AccountBasedExpenseLineDetail
from quickbooks.objects.base import Ref
from intuitlib.client import AuthClient


class InvoiceLine(BaseModel):
    item: str
    rate: float
    quantity: float = Field(default=1.0, gt=0)
    description: Optional[str] = None

    @property
    def amount(self) -> float:
        return self.rate * self.quantity
class InvoiceDraft(BaseModel):
    customer_display_name: str
    customer_company_name: Optional[str] = None
    line_items: List[InvoiceLine]
    memo: Optional[str] = None
    total_amount: Optional[float] = None



class QuickbooksInvoiceService:
    def __init__(self) -> None:
        self.auth_client = AuthClient(
            client_id=os.environ['CLIENT_ID'],
            client_secret=os.environ['CLIENT_SECRET'],
            environment='production',
            redirect_uri='https://developer.intuit.com/v2/OAuth2Playground/RedirectUrl',
        )

        self.client = QuickBooks(
            auth_client=self.auth_client,
            refresh_token=os.environ['REFRESH_TOKEN'],
            company_id=os.environ['COMPANY_ID'],
	    )


    def ensure_vendors(display_name: str, company_name: Optional[str]=None) -> Vendor:
        all_vendors=Vendor.all(qb =client)
       
        for vendor in all_vendors:
            if vendor.DisplayName and vendor.DisplayName.lower().strip() == display_name.lower().strip():
                print(f"found a match'{vendor.DisplayName}'")
                return vendor    
        best_match= None
        best_ratio= 0.8
        for vendor in all_vendors:
            if vendor.DisplayName:
                ratio= SequenceMatcher(None, vendor.DisplayName.lower(),display_name.lower()).ratio()
                if ratio> best_ratio:
                    best_ratio= ratio
                    best_match=vendor
        if best_match:
            print(f"found the best match'{best_match}'")
            return best_match
       
        else:
            vendor = Vendor()
            vendor.DisplayName= display_name
            if company_name:
                vendor.CompanyName =company_name
            vendor.save(qb=client)
            print("made new vendor")
            print(f"'{vendor.DisplayName}'")
            return vendor

    def push_invoice(self) -> Bill:
        bill = Bill()
        line = AccountBasedExpenseLine()
        line.Amount = 200
        line.DetailType = "AccountBasedExpenseLineDetail"
        account_ref = Ref()
        account_ref.type = "Account"
        account_ref.value = 1
        line.AccountBasedExpenseLineDetail = AccountBasedExpenseLineDetail()
        line.AccountBasedExpenseLineDetail.AccountRef = account_ref
        bill.Line.append(line)
        vendor = Vendor.all(max_results=1, qb=self.client)[0]
        bill.VendorRef = vendor.to_ref()
        print(line.Amount)
service = QuickbooksInvoiceService()
service.push_invoice()
