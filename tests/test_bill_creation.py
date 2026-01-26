"""Test suite for Bill creation from invoices"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from services.quickbooks_service import QuickbooksInvoiceService
from models.invoice import InvoiceLine, InvoiceDraft
import datetime


class TestBillCreation:
    """Test creating Bills in QuickBooks from invoice data"""

    @pytest.fixture
    def qb_service(self):
        """Initialize QuickBooks service"""
        return QuickbooksInvoiceService()

    @pytest.fixture
    def sample_invoice_draft(self):
        """Create sample invoice draft for testing"""
        line_items = [
            InvoiceLine(
                item="Labor - 8 hours",
                rate=50.00,
                quantity=8.0,
                category="labor"
            ),
            InvoiceLine(
                item="Materials - Wood",
                rate=100.00,
                quantity=5.0,
                category="materials"
            )
        ]

        return InvoiceDraft(
            vendor_display_name="Test Vendor LLC",
            invoice_number=f"TEST-INV-{int(datetime.datetime.now().timestamp()) % 1000000}",
            invoice_date=datetime.date.today().strftime("%m/%d/%Y"),
            due_date=(datetime.date.today() + datetime.timedelta(days=30)).strftime("%m/%d/%Y"),
            total_amount=900.00,
            tax=0.00,
            line_items=line_items,
            is_receipt=False
        )

    def test_create_basic_bill(self, qb_service, sample_invoice_draft):
        """Test creating a basic bill with line items"""
        bill = qb_service.push_invoice(sample_invoice_draft)
        
        assert bill is not None
        assert bill.Id is not None
        assert bill.VendorRef is not None
        assert len(bill.Line) == 2
        print(f"✓ Bill created with ID: {bill.Id}")

    def test_create_bill_with_tax(self, qb_service):
        """Test creating a bill with tax line item"""
        line_items = [
            InvoiceLine(item="Service", rate=100.00, quantity=1.0, category="supplies")
        ]
        
        draft = InvoiceDraft(
            vendor_display_name="Tax Test Vendor",
            invoice_number=f"TAX-TEST-{int(datetime.datetime.now().timestamp()) % 1000000}",
            total_amount=110.00,
            tax=10.00,
            line_items=line_items,
            is_receipt=False
        )
        
        bill = qb_service.push_invoice(draft)
        
        assert bill is not None
        assert len(bill.Line) == 2  # 1 line item + 1 tax line
        print(f"✓ Bill with tax created with ID: {bill.Id}")

    def test_create_bill_with_customer(self, qb_service):
        """Test creating a bill linked to a customer"""
        line_items = [
            InvoiceLine(item="Job Materials", rate=200.00, quantity=1.0, category="materials")
        ]
        
        draft = InvoiceDraft(
            vendor_display_name="Customer Test Vendor",
            invoice_number=f"CUST-TEST-{int(datetime.datetime.now().timestamp()) % 1000000}",
            total_amount=200.00,
            line_items=line_items,
            customer_name="Test Customer",  # This should match a QB customer
            is_receipt=False
        )
        
        bill = qb_service.push_invoice(draft)
        
        assert bill is not None
        print(f"✓ Bill with customer created with ID: {bill.Id}")

    def test_duplicate_detection(self, qb_service, sample_invoice_draft):
        """Test that duplicate bills are detected"""
        # Create first bill
        bill1 = qb_service.push_invoice(sample_invoice_draft)
        
        # Try to create duplicate with same invoice number
        bill2 = qb_service.push_invoice(sample_invoice_draft)
        
        # Should return existing bill, not create new one
        assert bill1.Id == bill2.Id
        print(f"✓ Duplicate detection working - returned existing bill ID: {bill1.Id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
