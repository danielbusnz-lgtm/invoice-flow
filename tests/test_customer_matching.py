"""Test suite for customer matching functionality"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from services.quickbooks_service import QuickbooksInvoiceService
from quickbooks.objects.customer import Customer


class TestCustomerMatching:
    """Test customer matching by name and address"""

    @pytest.fixture
    def qb_service(self):
        """Initialize QuickBooks service"""
        return QuickbooksInvoiceService()

    def test_get_customers_context(self, qb_service):
        """Test fetching customers with addresses for AI context"""
        context = qb_service.get_customers_context()
        
        assert context is not None
        assert isinstance(context, str)
        print(f"✓ Customer context retrieved:")
        print(context[:200] + "..." if len(context) > 200 else context)

    def test_find_customer_by_exact_address(self, qb_service):
        """Test finding customer by exact address match"""
        # Get first customer with an address
        customers = Customer.all(qb=qb_service.qb_client)
        test_customer = None
        test_address = None
        
        for customer in customers:
            if hasattr(customer, 'BillAddr') and customer.BillAddr and customer.BillAddr.Line1:
                test_customer = customer
                test_address = customer.BillAddr.Line1
                break
        
        if test_customer and test_address:
            customer_ref = qb_service.find_customer_by_address(test_address)
            assert customer_ref is not None
            assert customer_ref.name == test_customer.DisplayName
            print(f"✓ Found customer by address: {test_customer.DisplayName}")
        else:
            print("⊘ Skipped - no customers with addresses found")

    def test_find_customer_by_partial_address(self, qb_service):
        """Test finding customer by partial address match"""
        customers = Customer.all(qb=qb_service.qb_client)
        test_customer = None
        partial_address = None
        
        for customer in customers:
            if hasattr(customer, 'BillAddr') and customer.BillAddr and customer.BillAddr.City:
                test_customer = customer
                partial_address = customer.BillAddr.City  # Just city
                break
        
        if test_customer and partial_address:
            customer_ref = qb_service.find_customer_by_address(partial_address)
            assert customer_ref is not None
            print(f"✓ Found customer by partial address: {test_customer.DisplayName}")
        else:
            print("⊘ Skipped - no customers with city found")

    def test_no_match_returns_none(self, qb_service):
        """Test that non-existent address returns None"""
        customer_ref = qb_service.find_customer_by_address("123 Fake Street Nowhere City")
        assert customer_ref is None
        print("✓ Non-existent address correctly returns None")

    def test_empty_address_returns_none(self, qb_service):
        """Test that empty address returns None"""
        customer_ref = qb_service.find_customer_by_address("")
        assert customer_ref is None
        print("✓ Empty address correctly returns None")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
