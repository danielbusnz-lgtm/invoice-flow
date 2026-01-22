import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.quickbooks_service import QuickbooksInvoiceService
from quickbooks.objects.account import Account

qb = QuickbooksInvoiceService()

# Get all accounts
accounts = Account.all(qb=qb.qb_client)

print("EXPENSE ACCOUNTS:")
for acc in accounts:
    if acc.AccountType == "Expense":
        print(f"ID: {acc.Id}, Name: {acc.Name}")
