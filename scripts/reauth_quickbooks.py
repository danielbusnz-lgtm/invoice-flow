"""Re-authenticate with QuickBooks to get new tokens"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from intuitlib.client import AuthClient
from intuitlib.enums import Scopes
from dotenv import load_dotenv
import os

load_dotenv()

environment = os.getenv('ENVIRONMENT')
if environment == 'sandbox':
    client_id = os.getenv('SAND_CLIENT_ID')
    client_secret = os.getenv('SAND_CLIENT_SECRET')
else:
    client_id = os.getenv('CLIENT_ID')
    client_secret = os.getenv('CLIENT_SECRET')

auth_client = AuthClient(
    client_id=client_id,
    client_secret=client_secret,
    environment=environment,
    redirect_uri=os.getenv('REDIRECT_URI'),
)

# Get authorization URL
scopes = [Scopes.ACCOUNTING]
auth_url = auth_client.get_authorization_url(scopes)

print("=" * 60)
print("QUICKBOOKS RE-AUTHENTICATION")
print("=" * 60)
print("\n1. Open this URL in your browser:\n")
print(auth_url)
print("\n2. Log in and authorize the app")
print("3. Copy the FULL redirect URL you get sent to")
print("4. Paste it here:\n")

redirect_response = input("Redirect URL: ").strip()

try:
    auth_client.get_bearer_token(redirect_response)
    
    refresh_token = auth_client.refresh_token
    realm_id = auth_client.realm_id
    
    print("\n✓ Authentication successful!")
    print(f"Realm ID: {realm_id}")
    print(f"Refresh Token: {refresh_token[:20]}...")
    
    # Update .env file
    env_path = Path(__file__).parent.parent / '.env'
    with open(env_path, 'r') as f:
        lines = f.readlines()
    
    updated_refresh = False
    updated_realm = False
    
    for i, line in enumerate(lines):
        if line.startswith('REFRESH_TOKEN='):
            lines[i] = f'REFRESH_TOKEN={refresh_token}\n'
            updated_refresh = True
        elif line.startswith('QB_REALM_ID='):
            lines[i] = f'QB_REALM_ID={realm_id}\n'
            updated_realm = True
    
    # Add if not found
    if not updated_refresh:
        lines.append(f'REFRESH_TOKEN={refresh_token}\n')
    if not updated_realm:
        lines.append(f'QB_REALM_ID={realm_id}\n')
    
    with open(env_path, 'w') as f:
        f.writelines(lines)
    
    print("\n✓ .env file updated!")
    print("\nYou can now run your scripts again.")
    
except Exception as e:
    print(f"\n✗ Authentication failed: {e}")
