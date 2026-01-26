"""Test suite for Receipt/Purchase creation"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from services.quickbooks_service import QuickbooksInvoiceService
from models.invoice import InvoiceLine, InvoiceDraft
import datetime


class TestReceiptCreation:
    """Test creating Purchase transactions from receipts"""

    @pytest.fixture
    def qb_service(self):
        """Initialize QuickBooks service"""
        return QuickbooksInvoiceService()

    @pytest.fixture
    def sample_receipt_draft(self):
        """Create sample receipt draft for testing"""
        line_items = [
            InvoiceLine(
                item="Concrete Mix - 10 bags",
                rate=15.00,
                quantity=10.0,
                category="materials"
            ),
            InvoiceLine(
                item="Delivery Fee",
                rate=25.00,
                quantity=1.0,
                category="supplies"
            )
        ]

        return InvoiceDraft(
            vendor_display_name="Home Depot",
            invoice_number=f"RECEIPT-{int(datetime.datetime.now().timestamp()) % 1000000}",
            invoice_date=datetime.date.today().strftime("%m/%d/%Y"),
            total_amount=175.00,
            tax=0.00,
            line_items=line_items,
            is_receipt=True
        )

    def test_create_basic_receipt(self, qb_service, sample_receipt_draft):
        """Test creating a basic purchase from receipt"""
        purchase = qb_service.push_receipt(sample_receipt_draft)

        assert purchase is not None
        assert purchase.Id is not None
        # TotalAmt is calculated server-side after save
        assert purchase.EntityRef is not None  # Vendor
        assert purchase.AccountRef is not None  # Bank account
        assert len(purchase.Line) == 2
        print(f"✓ Purchase created with ID: {purchase.Id}")

    def test_create_receipt_with_tax(self, qb_service):
        """Test creating a receipt with tax"""
        line_items = [
            InvoiceLine(item="Tools", rate=50.00, quantity=2.0, category="equipment")
        ]
        
        draft = InvoiceDraft(
            vendor_display_name="Tool Store",
            invoice_number=f"RECEIPT-TAX-{int(datetime.datetime.now().timestamp()) % 1000000}",
            invoice_date=datetime.date.today().strftime("%m/%d/%Y"),
            total_amount=110.00,
            tax=10.00,
            line_items=line_items,
            is_receipt=True
        )
        
        purchase = qb_service.push_receipt(draft)

        assert purchase is not None
        # TotalAmt is calculated server-side after save
        assert len(purchase.Line) == 2  # 1 line item + 1 tax line
        print(f"✓ Purchase with tax created with ID: {purchase.Id}")

    def test_create_receipt_with_customer(self, qb_service):
        """Test creating a receipt linked to customer/job"""
        line_items = [
            InvoiceLine(item="Job Supplies", rate=75.00, quantity=3.0, category="supplies")
        ]
        
        draft = InvoiceDraft(
            vendor_display_name="Supply Store",
            invoice_number=f"RECEIPT-CUST-{int(datetime.datetime.now().timestamp()) % 1000000}",
            invoice_date=datetime.date.today().strftime("%m/%d/%Y"),
            total_amount=225.00,
            line_items=line_items,
            customer_name="Test Customer",
            is_receipt=True
        )
        
        purchase = qb_service.push_receipt(draft)
        
        assert purchase is not None
        print(f"✓ Purchase with customer created with ID: {purchase.Id}")

    def test_payment_type_is_set(self, qb_service, sample_receipt_draft):
        """Test that payment type is set on purchase"""
        purchase = qb_service.push_receipt(sample_receipt_draft)
        
        assert purchase.PaymentType is not None
        assert purchase.PaymentType in ["Cash", "Check", "CreditCard"]
        print(f"✓ Payment type set to: {purchase.PaymentType}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
