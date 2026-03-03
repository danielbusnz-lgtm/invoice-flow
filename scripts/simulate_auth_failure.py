"""Simulate QuickBooks auth failure to test auto-refresh flow"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv
load_dotenv()


def simulate_auth_failure():
    """
    Simulates what happens when QuickBooks auth fails on startup.

    Flow we expect:
    1. QuickBooks() constructor raises an auth error
    2. __init__ catches it and calls _refresh_and_reconnect()
    3. _refresh_and_reconnect() refreshes the token
    4. Second QuickBooks() call succeeds
    """

    call_count = 0

    def mock_quickbooks_init(*args, **kwargs):
        """First call fails, second call succeeds"""
        nonlocal call_count
        call_count += 1

        if call_count == 1:
            raise Exception("AuthorizationException: Token expired or revoked")

        # Second call succeeds, return a mock client
        mock_client = MagicMock()
        mock_client.company_id = "test_realm"
        return mock_client

    # Mock both QuickBooks constructor and AuthClient
    with patch("services.quickbooks_service.QuickBooks", side_effect=mock_quickbooks_init) as mock_qb, \
         patch("services.quickbooks_service.AuthClient") as mock_auth_class, \
         patch("services.quickbooks_service.load_dotenv"):

        # Set up mock AuthClient instance
        mock_auth_instance = MagicMock()
        mock_auth_instance.refresh_token = "fake_refreshed_token_12345"
        mock_auth_class.return_value = mock_auth_instance

        # Mock _save_refresh_token so it doesn't touch real .env
        with patch(
            "services.quickbooks_service.QuickbooksInvoiceService._save_refresh_token"
        ):
            from services.quickbooks_service import QuickbooksInvoiceService

            print("=" * 50)
            print("SIMULATING QUICKBOOKS AUTH FAILURE")
            print("=" * 50)
            print()

            try:
                service = QuickbooksInvoiceService()
                print()
                print("=" * 50)
                print("RESULT: Service recovered successfully")
                print(f"QuickBooks() was called {call_count} times")
                print("  Call 1: FAILED (simulated expired token)")
                print("  Call 2: SUCCEEDED (after token refresh)")
                print("=" * 50)

            except Exception as e:
                print()
                print("=" * 50)
                print(f"RESULT: Service failed to recover: {e}")
                print("=" * 50)


if __name__ == "__main__":
    simulate_auth_failure()
