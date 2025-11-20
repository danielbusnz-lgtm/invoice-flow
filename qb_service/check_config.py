import os

print("=== QuickBooks Configuration Check ===\n")

required_vars = {
    "CLIENT_ID": os.getenv("CLIENT_ID"),
    "CLIENT_SECRET": os.getenv("CLIENT_SECRET"),
    "QB_REALM_ID": os.getenv("QB_REALM_ID"),
    "QB_REFRESH_TOKEN": os.getenv("QB_REFRESH_TOKEN"),
}

optional_vars = {
    "QB_ENVIRONMENT": os.getenv("QB_ENVIRONMENT", "sandbox"),
    "QB_REDIRECT_URI": os.getenv("QB_REDIRECT_URI", "http://localhost:8000/callback"),
    "QB_EXPENSE_ACCOUNT_ID": os.getenv("QB_EXPENSE_ACCOUNT_ID"),
    "QB_EXPENSE_ACCOUNT_NAME": os.getenv("QB_EXPENSE_ACCOUNT_NAME"),
}

print("Required Environment Variables:")
for key, value in required_vars.items():
    if value:
        if "SECRET" in key or "TOKEN" in key:
            print(f"  [OK] {key}: {value[:10]}...{value[-10:] if len(value) > 20 else ''} (length: {len(value)})")
        else:
            print(f"  [OK] {key}: {value}")
    else:
        print(f"  [MISSING] {key}: NOT SET")

print("\nOptional Environment Variables:")
for key, value in optional_vars.items():
    if value:
        print(f"  [OK] {key}: {value}")
    else:
        print(f"  [DEFAULT] {key}: Not set (using default)")

print("\n=== Common Issues ===")
print("1. CLIENT_ID/CLIENT_SECRET must match the app that generated the refresh token")
print("2. QB_REALM_ID must be the exact company ID you authorized")
print("3. QB_ENVIRONMENT must match where you got the token (sandbox vs production)")
print("4. Refresh token must be from the SAME app with the SAME scopes")
print("\n=== Next Steps ===")
print("If all variables are set correctly:")
print("1. Go to developer.intuit.com")
print("2. Check your app's Keys & OAuth")
print("3. Verify the Realm ID matches your company")
print("4. Generate a NEW token from the OAuth Playground for THIS specific app")
