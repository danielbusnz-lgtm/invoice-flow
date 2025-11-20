import os
from intuitlib.client import AuthClient
from quickbooks import QuickBooks

print("=== Testing QuickBooks Authentication ===\n")

# Load credentials
client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
refresh_token = os.getenv("QB_REFRESH_TOKEN")
realm_id = os.getenv("QB_REALM_ID")
environment = os.getenv("QB_ENVIRONMENT", "production")

print(f"Environment: {environment}")
print(f"Realm ID: {realm_id}")
print(f"Client ID: {client_id}")
print(f"Refresh Token: {refresh_token[:10]}...{refresh_token[-10:]}\n")

# Step 1: Create auth client
print("Step 1: Creating auth client...")
auth_client = AuthClient(
    client_id=client_id,
    client_secret=client_secret,
    environment=environment,
    redirect_uri=os.getenv("QB_REDIRECT_URI", "http://localhost:8000/callback"),
)
print("[OK] Auth client created\n")

# Step 2: Create QuickBooks client
print("Step 2: Creating QuickBooks client and refreshing token...")
try:
    qb = QuickBooks(
        auth_client=auth_client,
        refresh_token=refresh_token,
        company_id=realm_id,
    )
    print("[OK] QuickBooks client created and token refreshed\n")
except Exception as e:
    print(f"[ERROR] Failed to create QuickBooks client: {e}\n")
    exit(1)

# Step 3: Try to get company info
print("Step 3: Fetching company info...")
try:
    from quickbooks.objects.company_info import CompanyInfo
    company_info = CompanyInfo.get(1, qb=qb)
    print(f"[OK] Company Name: {company_info.CompanyName}")
    print(f"[OK] Legal Name: {company_info.LegalName}")
    print(f"[OK] Company successfully connected[WARN]\n")
except Exception as e:
    print(f"[ERROR] Failed to get company info: {e}\n")
    exit(1)

# Step 4: Try to query accounts
print("Step 4: Testing Account query...")
try:
    from quickbooks.objects.account import Account
    accounts = Account.all(qb=qb)
    print(f"[OK] Found {len(accounts)} accounts")

    # Show first 5 accounts
    print("\nFirst 5 accounts:")
    for acc in accounts[:5]:
        print(f"  - {acc.Name} (Type: {acc.AccountType})")

    # Look for Job Expenses
    job_expenses = [a for a in accounts if "job" in a.Name.lower() and "expense" in a.Name.lower()]
    if job_expenses:
        print(f"\n[OK] Found 'Job Expenses' account: {job_expenses[0].Name} (ID: {job_expenses[0].Id})")
    else:
        print("\n[WARN] 'Job Expenses' account not found - you may need to create it or use a different name")

        # Show all expense accounts
        expense_accounts = [a for a in accounts if a.AccountType == "Expense"]
        print(f"\nAvailable Expense accounts ({len(expense_accounts)}):")
        for acc in expense_accounts:
            print(f"  - {acc.Name} (ID: {acc.Id})")

except Exception as e:
    print(f"[ERROR] Failed to query accounts: {e}\n")
    print("This is likely a permissions issue with your QuickBooks app.")
    exit(1)

print("\n[OK] All authentication tests passed[WARN]")
