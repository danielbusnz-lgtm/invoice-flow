from services.quickbooks_service import QuickbooksInvoiceService
from quickbooks.objects.purchase import Purchase
from quickbooks.objects.account import Account
from quickbooks.objects.detailline import AccountBasedExpenseLine, AccountBasedExpenseLineDetail
from quickbooks.objects.base import Ref
from quickbooks.objects.vendor import Vendor
import datetime

qb = QuickbooksInvoiceService()

# Get a vendor (or use existing one)
vendors = Vendor.all(qb=qb.qb_client)
test_vendor = vendors[0] if vendors else None

if not test_vendor:
    print("No vendors found. Create a vendor first.")
    exit()

# Get a checking account (bank account)
accounts = Account.all(qb=qb.qb_client)
bank_account = None
for acc in accounts:
    if acc.AccountType == "Bank":
        bank_account = acc
        print(f"Using bank account: {acc.Name} (ID: {acc.Id})")
        break

if not bank_account:
    print("No bank accounts found.")
    exit()

# Create a test purchase (bank transaction)
purchase = Purchase()
purchase.PaymentType = "Cash"  # or "Check", "CreditCard"
purchase.TxnDate = datetime.date.today().strftime("%Y-%m-%d")

# Set the bank account where money came from
purchase.AccountRef = bank_account.to_ref()

# Set vendor
if test_vendor:
    purchase.EntityRef = test_vendor.to_ref()

# Add expense line
line = AccountBasedExpenseLine()
line.DetailType = "AccountBasedExpenseLineDetail"
line.Amount = 180.00  # Match your test bill amount

# Use expense account
account_ref = Ref()
account_ref.type = "Account"
account_ref.value = "31"  # Uncategorized Expense

line.AccountBasedExpenseLineDetail = AccountBasedExpenseLineDetail()
line.AccountBasedExpenseLineDetail.AccountRef = account_ref
line.Description = "Test bank transaction - matching test bill"

purchase.Line.append(line)

# Save purchase
purchase.save(qb=qb.qb_client)

print(f"\n✓ Test bank transaction created!")
print(f"  ID: {purchase.Id}")
print(f"  Vendor: {test_vendor.DisplayName}")
print(f"  Amount: ${line.Amount}")
print(f"  Date: {purchase.TxnDate}")
print(f"  Bank Account: {bank_account.Name}")
print(f"\nYou can now test matching this transaction to bills!")
