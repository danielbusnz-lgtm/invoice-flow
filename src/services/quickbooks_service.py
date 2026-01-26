# QuickBooks objects
from quickbooks.objects.attachable import Attachable, AttachableRef
from quickbooks.objects.customer import Customer
from quickbooks.objects.vendor import Vendor
from quickbooks.objects.bill import Bill
from quickbooks.objects.account import Account
from quickbooks.objects.item import Item
from quickbooks.objects.creditcardpayment import CreditChargeInfo, CreditChargeResponse, CreditCardPayment
from quickbooks.objects.billpayment import BillPayment, BillPaymentCreditCard
from quickbooks.objects.detailline import AccountBasedExpenseLine, AccountBasedExpenseLineDetail, ItemBasedExpenseLine
from quickbooks.objects.base import Ref
from quickbooks.objects.purchase import Purchase
from quickbooks import *

# Standard library imports
import os
from difflib import SequenceMatcher

# Third-party imports
from intuitlib.client import AuthClient
from dotenv import load_dotenv

# Local imports
from models.invoice import InvoiceLine, InvoiceDraft

load_dotenv()


class QuickbooksInvoiceService:
    def __init__(self) -> None:
            environment=os.getenv('ENVIRONMENT')
            if environment == 'sandbox':
                client_id=os.getenv('SAND_CLIENT_ID')
                client_secret=os.getenv('SAND_CLIENT_SECRET')
            else:

                client_id=os.getenv('CLIENT_ID')
                client_secret=os.getenv('CLIENT_SECRET')
            self.auth_client = AuthClient(
                client_id = client_id,
                client_secret =  client_secret,
                environment = environment,
                redirect_uri=os.getenv('REDIRECT_URI'),
            )


            self.qb_client = QuickBooks(
                auth_client=self.auth_client,
                refresh_token=os.getenv('REFRESH_TOKEN'),
                company_id=os.getenv('QB_REALM_ID'),
	        )

            # Save new refresh token after initialization
            self._save_refresh_token()

    def _save_refresh_token(self):
        """Save the new refresh token to .env file"""
        new_refresh_token = self.auth_client.refresh_token

        if not new_refresh_token:
            return

        # Read current .env file
        from pathlib import Path
        env_path = Path(__file__).parent.parent.parent / '.env'

        if not env_path.exists():
            return

        with open(env_path, 'r') as f:
            lines = f.readlines()

        # Update refresh token line
        updated = False
        for i, line in enumerate(lines):
            if line.startswith('REFRESH_TOKEN='):
                lines[i] = f'REFRESH_TOKEN={new_refresh_token}\n'
                updated = True
                break

        # Write back to .env
        if updated:
            with open(env_path, 'w') as f:
                f.writelines(lines)
            print(f"✓ Refresh token updated in .env")


    def get_customers_context(self) -> str:
        """Get all customers with addresses formatted for AI context"""
        customers = Customer.all(qb=self.qb_client)

        customer_list = []
        for customer in customers:
            addresses = []

            # Get billing address
            if hasattr(customer, 'BillAddr') and customer.BillAddr:
                bill_addr_parts = []
                if customer.BillAddr.Line1:
                    bill_addr_parts.append(customer.BillAddr.Line1)
                if customer.BillAddr.Line2:
                    bill_addr_parts.append(customer.BillAddr.Line2)
                if customer.BillAddr.City:
                    bill_addr_parts.append(customer.BillAddr.City)
                if bill_addr_parts:
                    addresses.append(", ".join(bill_addr_parts))

            # Get shipping address
            if hasattr(customer, 'ShipAddr') and customer.ShipAddr:
                ship_addr_parts = []
                if customer.ShipAddr.Line1:
                    ship_addr_parts.append(customer.ShipAddr.Line1)
                if customer.ShipAddr.Line2:
                    ship_addr_parts.append(customer.ShipAddr.Line2)
                if customer.ShipAddr.City:
                    ship_addr_parts.append(customer.ShipAddr.City)
                if ship_addr_parts:
                    ship_addr = ", ".join(ship_addr_parts)
                    if ship_addr not in addresses:  # Avoid duplicates
                        addresses.append(ship_addr)

            if addresses:
                customer_list.append(f"- {customer.DisplayName}: {' | '.join(addresses)}")

        return "\n".join(customer_list) if customer_list else "No customers with addresses found."

    def match_category_to_account(self, category: str):
        """Match expense category to QuickBooks account"""
        if not category:
            return os.getenv('QB_EXPENSE_ACCOUNT_ID', '31')

        category_lower = category.lower().strip()

        # Category to account mapping (customize based on your QB accounts)
        category_map = {
            'materials': '63',  # Job Materials
            'labor': '59',  # Cost of Labor
            'equipment': '29',  # Equipment Rental
            'fuel': '56',  # Fuel
            'permits': '68',  # Permits
            'supplies': '20',  # Supplies
            'disposal': '28',  # Disposal Fees
            'plants': '66',  # Plants and Soil
            'soil': '66',  # Plants and Soil
            'sprinklers': '67',  # Sprinklers and Drip Systems
            'repairs': '75',  # Equipment Repairs
            'telephone': '77',  # Telephone
            'utilities': '24',  # Utilities
            'gas': '76',  # Gas and Electric
            'electric': '76',  # Gas and Electric
        }

        # Try exact match
        if category_lower in category_map:
            return category_map[category_lower]

        # Try partial match
        for key, account_id in category_map.items():
            if key in category_lower or category_lower in key:
                print(f"Category matched: {category} -> Account {account_id}")
                return account_id

        # Default to uncategorized expense
        print(f"No category match for '{category}', using default account")
        return os.getenv('QB_EXPENSE_ACCOUNT_ID', '31')

    def find_customer_by_address(self, address: str):
        """Match job site address to QuickBooks Customer"""
        if not address:
            return None

        from quickbooks.objects.customer import Customer

        # Get all customers
        customers = Customer.all(qb=self.qb_client)

        if not customers:
            return None

        # Clean address for matching
        address_lower = address.lower().strip()

        # Try exact match on customer address
        for customer in customers:
            # Check billing address
            if hasattr(customer, 'BillAddr') and customer.BillAddr:
                bill_addr = f"{customer.BillAddr.Line1 or ''} {customer.BillAddr.Line2 or ''} {customer.BillAddr.City or ''}".lower()
                if address_lower in bill_addr or bill_addr in address_lower:
                    print(f"Customer matched: {customer.DisplayName} -> Address: {address}")
                    return customer.to_ref()

            # Check shipping address
            if hasattr(customer, 'ShipAddr') and customer.ShipAddr:
                ship_addr = f"{customer.ShipAddr.Line1 or ''} {customer.ShipAddr.Line2 or ''} {customer.ShipAddr.City or ''}".lower()
                if address_lower in ship_addr or ship_addr in address_lower:
                    print(f"Customer matched: {customer.DisplayName} -> Address: {address}")
                    return customer.to_ref()

        # Try fuzzy match on customer name
        best_match = None
        best_ratio = 0.7

        for customer in customers:
            ratio = SequenceMatcher(None, address_lower, customer.DisplayName.lower()).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = customer.to_ref()

        if best_match:
            print(f"Customer fuzzy matched: {best_match.name} -> Address: {address}")
        else:
            print(f"No customer match found for address: {address}")

        return best_match

    def ensure_vendors(self, draft) -> Vendor:
        all_vendors=Vendor.all(qb =self.qb_client)
       
        for vendor in all_vendors:
            if draft.vendor_display_name.strip()==vendor.DisplayName.strip():
                
                return vendor
        best_match= None
        best_ratio= 0.8

        for vendor in all_vendors:
            ratio = SequenceMatcher(None, draft.vendor_display_name, vendor.DisplayName).ratio()

    
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

    def check_duplicate_bill(self, draft):
        """Check if bill already exists"""
        from datetime import datetime

        bills = Bill.all(qb=self.qb_client)

        # Normalize draft date to YYYY-MM-DD format for comparison
        draft_date = draft.invoice_date
        if draft_date and '/' in draft_date:
            try:
                draft_date = datetime.strptime(draft_date, "%m/%d/%Y").strftime("%Y-%m-%d")
            except:
                pass

        for bill in bills:
            # Check by invoice number
            if draft.invoice_number and hasattr(bill, 'DocNumber') and bill.DocNumber:
                if bill.DocNumber == draft.invoice_number:
                    print(f"Duplicate bill found by invoice number: {bill.Id}")
                    return bill

            # Check by vendor + date + amount (calculate from line items if TotalAmt not populated)
            if (bill.VendorRef and
                bill.VendorRef.name == draft.vendor_display_name and
                bill.TxnDate == draft_date):

                # Calculate bill total from line items
                bill_total = sum(line.Amount for line in bill.Line if hasattr(line, 'Amount'))

                # Compare amounts (allow small rounding difference)
                if abs(bill_total - draft.total_amount) < 0.01:
                    print(f"Duplicate bill found by vendor/date/amount: {bill.Id}")
                    return bill

        return None

    def push_invoice(self, draft) -> Bill:
        # Check for duplicate
        existing = self.check_duplicate_bill(draft)
        if existing:
            print(f"Skipping duplicate bill: {existing.Id}")
            return existing

        # Validate total
        if not draft.total_amount or draft.total_amount <= 0:
            raise ValueError("Draft must have a valid total_amount")

        # Create bill
        bill = Bill()
        vendor = self.ensure_vendors(draft)
        bill.VendorRef = vendor.to_ref()

        # Set dates
        if draft.invoice_date:
            bill.TxnDate = draft.invoice_date
        if draft.due_date:
            bill.DueDate = draft.due_date

        # Set invoice number
        if draft.invoice_number:
            bill.DocNumber = draft.invoice_number

        # Find customer - prefer AI-matched name, fallback to address matching
        customer_ref = None
        if draft.customer_name:
            # AI provided customer name - find by exact name match
            print(f"AI matched customer: {draft.customer_name}")
            customers = Customer.all(qb=self.qb_client)
            for customer in customers:
                if customer.DisplayName == draft.customer_name:
                    customer_ref = customer.to_ref()
                    print(f"Customer found: {customer.DisplayName}")
                    break
            if not customer_ref:
                print(f"Warning: AI-matched customer '{draft.customer_name}' not found in QuickBooks")
        elif draft.job_site_address:
            # Fallback to address matching
            customer_ref = self.find_customer_by_address(draft.job_site_address)

        # Add line items
        rounded_total = round(draft.total_amount, 2)

        for line in draft.line_items:
            qb_line = AccountBasedExpenseLine()
            qb_line.DetailType = "AccountBasedExpenseLineDetail"
            qb_line.Amount = line.amount

            # Match category to account
            account_id = self.match_category_to_account(line.category)

            account_ref = Ref()
            account_ref.type = "Account"
            account_ref.value = account_id

            qb_line.AccountBasedExpenseLineDetail = AccountBasedExpenseLineDetail()
            qb_line.AccountBasedExpenseLineDetail.AccountRef = account_ref
            qb_line.Description = f"{line.item} - Qty: {line.quantity} @${line.rate}"

            # Assign to customer if found
            if customer_ref:
                qb_line.AccountBasedExpenseLineDetail.CustomerRef = customer_ref

            bill.Line.append(qb_line)

        # Add tax as separate line item if present
        if draft.tax and draft.tax > 0:
            tax_line = AccountBasedExpenseLine()
            tax_line.DetailType = "AccountBasedExpenseLineDetail"
            tax_line.Amount = draft.tax

            # Use default expense account for tax
            tax_account_id = os.getenv('QB_EXPENSE_ACCOUNT_ID', '31')

            tax_account_ref = Ref()
            tax_account_ref.type = "Account"
            tax_account_ref.value = tax_account_id

            tax_line.AccountBasedExpenseLineDetail = AccountBasedExpenseLineDetail()
            tax_line.AccountBasedExpenseLineDetail.AccountRef = tax_account_ref
            tax_line.Description = "Tax"

            # Assign to customer if found
            if customer_ref:
                tax_line.AccountBasedExpenseLineDetail.CustomerRef = customer_ref

            bill.Line.append(tax_line)
    
        bill.save(qb=self.qb_client)
        print(f"Bill created - Total: ${rounded_total}, Vendor: {vendor.DisplayName}")
        return bill

    def push_receipt(self, draft) -> Purchase:
        """Create a Purchase transaction for already-paid expenses (receipts)"""
        # Validate total
        if not draft.total_amount or draft.total_amount <= 0:
            raise ValueError("Draft must have a valid total_amount")

        # Create purchase
        purchase = Purchase()
        vendor = self.ensure_vendors(draft)
        purchase.EntityRef = vendor.to_ref()
        purchase.PaymentType = "CreditCard"  # Default to credit card, could be Cash/Check

        # Set date (convert from MM/DD/YYYY to YYYY-MM-DD)
        if draft.invoice_date:
            from datetime import datetime
            try:
                date_obj = datetime.strptime(draft.invoice_date, "%m/%d/%Y")
                purchase.TxnDate = date_obj.strftime("%Y-%m-%d")
            except:
                purchase.TxnDate = datetime.today().strftime("%Y-%m-%d")

        # Get bank/credit card account (you'll need to configure this)
        # For now, get first bank account
        accounts = Account.all(qb=self.qb_client)
        bank_account = None
        for acc in accounts:
            if acc.AccountType in ["Bank", "Credit Card"]:
                bank_account = acc
                print(f"Using account: {acc.Name} (Type: {acc.AccountType})")
                break

        if not bank_account:
            raise ValueError("No bank or credit card account found in QuickBooks. Please add one first.")

        purchase.AccountRef = bank_account.to_ref()

        # Find customer
        customer_ref = None
        if draft.customer_name:
            customers = Customer.all(qb=self.qb_client)
            for customer in customers:
                if customer.DisplayName == draft.customer_name:
                    customer_ref = customer.to_ref()
                    break
        elif draft.job_site_address:
            customer_ref = self.find_customer_by_address(draft.job_site_address)

        # Add line items
        for line in draft.line_items:
            qb_line = AccountBasedExpenseLine()
            qb_line.DetailType = "AccountBasedExpenseLineDetail"
            qb_line.Amount = line.amount

            # Match category to account
            account_id = self.match_category_to_account(line.category)

            account_ref = Ref()
            account_ref.type = "Account"
            account_ref.value = account_id

            qb_line.AccountBasedExpenseLineDetail = AccountBasedExpenseLineDetail()
            qb_line.AccountBasedExpenseLineDetail.AccountRef = account_ref
            qb_line.Description = f"{line.item} - Qty: {line.quantity} @${line.rate}"

            # Assign to customer if found
            if customer_ref:
                qb_line.AccountBasedExpenseLineDetail.CustomerRef = customer_ref

            purchase.Line.append(qb_line)

        # Add tax as separate line item if present
        if draft.tax and draft.tax > 0:
            tax_line = AccountBasedExpenseLine()
            tax_line.DetailType = "AccountBasedExpenseLineDetail"
            tax_line.Amount = draft.tax

            tax_account_id = os.getenv('QB_EXPENSE_ACCOUNT_ID', '31')

            tax_account_ref = Ref()
            tax_account_ref.type = "Account"
            tax_account_ref.value = tax_account_id

            tax_line.AccountBasedExpenseLineDetail = AccountBasedExpenseLineDetail()
            tax_line.AccountBasedExpenseLineDetail.AccountRef = tax_account_ref
            tax_line.Description = "Tax"

            if customer_ref:
                tax_line.AccountBasedExpenseLineDetail.CustomerRef = customer_ref

            purchase.Line.append(tax_line)

        purchase.save(qb=self.qb_client)
        print(f"Purchase created (already paid) - Total: ${draft.total_amount}, Vendor: {vendor.DisplayName}")
        return purchase

    def add_attachment(self, file_path, transaction):
        """Attach a file to a QuickBooks transaction (Bill or Purchase)"""
        import os
        from pathlib import Path

        attach = Attachable()
        attach._FilePath = file_path
        attach.FileName = Path(file_path).name

        # Set ContentType based on file extension
        file_ext = Path(file_path).suffix.lower()
        if file_ext == '.pdf':
            attach.ContentType = 'application/pdf'
        elif file_ext in ['.jpg', '.jpeg']:
            attach.ContentType = 'image/jpeg'
        elif file_ext == '.png':
            attach.ContentType = 'image/png'
        else:
            attach.ContentType = 'application/octet-stream'

        # Link attachment to the transaction (Bill or Purchase)
        attachable_ref = AttachableRef()
        # Create manual Ref since Purchase doesn't have to_ref()
        entity_ref = Ref()
        entity_ref.type = transaction.qbo_object_name
        entity_ref.value = transaction.Id
        attachable_ref.EntityRef = entity_ref
        attach.AttachableRef = [attachable_ref]

        attach.save(qb=self.qb_client)
        return attach
