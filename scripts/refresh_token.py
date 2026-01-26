"""Manually refresh QuickBooks token"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from intuitlib.client import AuthClient
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

old_refresh_token = os.getenv('REFRESH_TOKEN')
print(f"Old refresh token: {old_refresh_token[:20]}...")

try:
    auth_client.refresh(refresh_token=old_refresh_token)
    new_refresh_token = auth_client.refresh_token
    
    print(f"✓ Token refreshed successfully!")
    print(f"New refresh token: {new_refresh_token[:20]}...")
    
    # Update .env file
    env_path = Path(__file__).parent.parent / '.env'
    with open(env_path, 'r') as f:
        lines = f.readlines()
    
    for i, line in enumerate(lines):
        if line.startswith('REFRESH_TOKEN='):
            lines[i] = f'REFRESH_TOKEN={new_refresh_token}\n'
            break
    
    with open(env_path, 'w') as f:
        f.writelines(lines)
    
    print("✓ .env file updated with new refresh token")
    
except Exception as e:
    print(f"✗ Token refresh failed: {e}")
    print("\nYou need to re-authenticate:")
    print("1. Go to QuickBooks Developer Portal")
    print("2. Get new authorization code")
    print("3. Exchange for new tokens")
    print("4. Update REFRESH_TOKEN in .env")
