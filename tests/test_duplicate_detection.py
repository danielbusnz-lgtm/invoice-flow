"""Test suite for duplicate bill detection"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from services.quickbooks_service import QuickbooksInvoiceService
from models.invoice import InvoiceLine, InvoiceDraft
import datetime


class TestDuplicateDetection:
    """Test duplicate bill detection logic"""

    @pytest.fixture
    def qb_service(self):
        """Initialize QuickBooks service"""
        return QuickbooksInvoiceService()

    @pytest.fixture
    def unique_draft(self):
        """Create a unique invoice draft"""
        timestamp = int(datetime.datetime.now().timestamp()) % 1000000
        
        line_items = [
            InvoiceLine(item="Test Item", rate=100.00, quantity=1.0, category="supplies")
        ]
        
        return InvoiceDraft(
            vendor_display_name="Test Vendor",
            invoice_number=f"DUP-TEST-{timestamp}",
            invoice_date=datetime.date.today().strftime("%m/%d/%Y"),
            total_amount=100.00,
            line_items=line_items,
            is_receipt=False
        )

    def test_duplicate_by_invoice_number(self, qb_service, unique_draft):
        """Test that bills with same invoice number are detected as duplicates"""
        # Create first bill
        bill1 = qb_service.push_invoice(unique_draft)
        assert bill1 is not None
        
        # Try to create duplicate
        bill2 = qb_service.push_invoice(unique_draft)
        
        # Should return same bill
        assert bill1.Id == bill2.Id
        print(f"✓ Duplicate detected by invoice number: {bill1.Id}")

    def test_duplicate_by_vendor_amount_date(self, qb_service):
        """Test duplicate detection by vendor + amount + date combo"""
        timestamp = int(datetime.datetime.now().timestamp()) % 1000000
        
        line_items = [
            InvoiceLine(item="Item", rate=150.00, quantity=1.0, category="supplies")
        ]
        
        draft1 = InvoiceDraft(
            vendor_display_name="Duplicate Test Vendor",
            invoice_number=f"NUM1-{timestamp}",
            invoice_date=datetime.date.today().strftime("%m/%d/%Y"),
            total_amount=150.00,
            line_items=line_items,
            is_receipt=False
        )
        
        # Create first bill
        bill1 = qb_service.push_invoice(draft1)
        
        # Create second draft with different invoice number but same vendor/amount/date
        draft2 = InvoiceDraft(
            vendor_display_name="Duplicate Test Vendor",
            invoice_number=f"NUM2-{timestamp}",  # Different number
            invoice_date=datetime.date.today().strftime("%m/%d/%Y"),
            total_amount=150.00,
            line_items=line_items,
            is_receipt=False
        )
        
        # Try to create duplicate
        bill2 = qb_service.push_invoice(draft2)
        
        # Should return same bill (detected by vendor+amount+date)
        assert bill1.Id == bill2.Id
        print(f"✓ Duplicate detected by vendor/amount/date: {bill1.Id}")

    def test_different_amounts_not_duplicate(self, qb_service):
        """Test that bills with different amounts are not duplicates"""
        timestamp = int(datetime.datetime.now().timestamp()) % 1000000
        
        draft1 = InvoiceDraft(
            vendor_display_name="Amount Test Vendor",
            invoice_number=f"AMT1-{timestamp}",
            invoice_date=datetime.date.today().strftime("%m/%d/%Y"),
            total_amount=100.00,
            line_items=[InvoiceLine(item="Item", rate=100.00, quantity=1.0)],
            is_receipt=False
        )
        
        draft2 = InvoiceDraft(
            vendor_display_name="Amount Test Vendor",
            invoice_number=f"AMT2-{timestamp}",
            invoice_date=datetime.date.today().strftime("%m/%d/%Y"),
            total_amount=200.00,  # Different amount
            line_items=[InvoiceLine(item="Item", rate=200.00, quantity=1.0)],
            is_receipt=False
        )
        
        bill1 = qb_service.push_invoice(draft1)
        bill2 = qb_service.push_invoice(draft2)
        
        assert bill1.Id != bill2.Id
        print(f"✓ Different amounts not treated as duplicate: {bill1.Id} vs {bill2.Id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
