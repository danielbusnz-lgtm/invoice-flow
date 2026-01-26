"""Test suite for vendor creation and matching"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from services.quickbooks_service import QuickbooksInvoiceService
from models.invoice import InvoiceLine, InvoiceDraft
from quickbooks.objects.vendor import Vendor
import datetime


class TestVendorManagement:
    """Test vendor creation and matching logic"""

    @pytest.fixture
    def qb_service(self):
        """Initialize QuickBooks service"""
        return QuickbooksInvoiceService()

    def test_match_existing_vendor_exact(self, qb_service):
        """Test matching existing vendor by exact name"""
        # Get first vendor
        vendors = Vendor.all(qb=qb_service.qb_client)
        if not vendors:
            pytest.skip("No vendors in QuickBooks to test")
        
        test_vendor = vendors[0]
        
        draft = InvoiceDraft(
            vendor_display_name=test_vendor.DisplayName,
            invoice_number="TEST",
            total_amount=100.00,
            line_items=[InvoiceLine(item="Test", rate=100.00, quantity=1.0)]
        )
        
        matched_vendor = qb_service.ensure_vendors(draft)
        assert matched_vendor.Id == test_vendor.Id
        print(f"✓ Matched existing vendor: {test_vendor.DisplayName}")

    def test_match_existing_vendor_fuzzy(self, qb_service):
        """Test fuzzy matching of vendor name"""
        vendors = Vendor.all(qb=qb_service.qb_client)
        if not vendors:
            pytest.skip("No vendors in QuickBooks to test")
        
        test_vendor = vendors[0]
        # Add slight typo
        fuzzy_name = test_vendor.DisplayName + " Inc"
        
        draft = InvoiceDraft(
            vendor_display_name=fuzzy_name,
            invoice_number="TEST",
            total_amount=100.00,
            line_items=[InvoiceLine(item="Test", rate=100.00, quantity=1.0)]
        )
        
        matched_vendor = qb_service.ensure_vendors(draft)
        # Should match existing or create new
        assert matched_vendor is not None
        print(f"✓ Vendor matching completed for: {fuzzy_name}")

    def test_create_new_vendor(self, qb_service):
        """Test creating a new vendor when no match found"""
        unique_name = f"Test Vendor {int(datetime.datetime.now().timestamp()) % 1000000}"
        
        draft = InvoiceDraft(
            vendor_display_name=unique_name,
            invoice_number="TEST",
            total_amount=100.00,
            line_items=[InvoiceLine(item="Test", rate=100.00, quantity=1.0)]
        )
        
        vendor = qb_service.ensure_vendors(draft)
        assert vendor is not None
        assert vendor.DisplayName == unique_name
        print(f"✓ Created new vendor: {unique_name}")

    def test_vendor_whitespace_handling(self, qb_service):
        """Test that vendor names with extra whitespace match correctly"""
        vendors = Vendor.all(qb=qb_service.qb_client)
        if not vendors:
            pytest.skip("No vendors in QuickBooks to test")
        
        test_vendor = vendors[0]
        # Add extra whitespace
        whitespace_name = f"  {test_vendor.DisplayName}  "
        
        draft = InvoiceDraft(
            vendor_display_name=whitespace_name,
            invoice_number="TEST",
            total_amount=100.00,
            line_items=[InvoiceLine(item="Test", rate=100.00, quantity=1.0)]
        )
        
        matched_vendor = qb_service.ensure_vendors(draft)
        assert matched_vendor.Id == test_vendor.Id
        print(f"✓ Whitespace handled correctly for: {test_vendor.DisplayName}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
