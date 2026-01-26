"""Test suite for file attachment functionality"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from services.quickbooks_service import QuickbooksInvoiceService
from models.invoice import InvoiceLine, InvoiceDraft
import datetime
import tempfile


class TestAttachments:
    """Test file attachment to QuickBooks transactions"""

    @pytest.fixture
    def qb_service(self):
        """Initialize QuickBooks service"""
        return QuickbooksInvoiceService()

    @pytest.fixture
    def test_bill(self, qb_service):
        """Create a test bill to attach files to"""
        line_items = [
            InvoiceLine(item="Test Item", rate=100.00, quantity=1.0, category="supplies")
        ]
        
        draft = InvoiceDraft(
            vendor_display_name="Attachment Test Vendor",
            invoice_number=f"ATTACH-{int(datetime.datetime.now().timestamp()) % 1000000}",
            total_amount=100.00,
            line_items=line_items,
            is_receipt=False
        )
        
        return qb_service.push_invoice(draft)

    @pytest.fixture
    def test_pdf_file(self):
        """Create a temporary PDF file for testing"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False) as f:
            f.write('%PDF-1.4\nTest PDF content')
            return f.name

    @pytest.fixture
    def test_jpg_file(self):
        """Create a temporary JPG file for testing"""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.jpg', delete=False) as f:
            # Minimal JPEG header
            f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF')
            return f.name

    def test_attach_pdf_to_bill(self, qb_service, test_bill, test_pdf_file):
        """Test attaching a PDF file to a bill"""
        attach = qb_service.add_attachment(test_pdf_file, test_bill)
        
        assert attach is not None
        assert attach.Id is not None
        assert attach.ContentType == 'application/pdf'
        print(f"✓ PDF attached to bill with ID: {attach.Id}")

    def test_attach_jpg_to_bill(self, qb_service, test_bill, test_jpg_file):
        """Test attaching a JPG file to a bill"""
        attach = qb_service.add_attachment(test_jpg_file, test_bill)
        
        assert attach is not None
        assert attach.Id is not None
        assert attach.ContentType == 'image/jpeg'
        print(f"✓ JPG attached to bill with ID: {attach.Id}")

    def test_attachment_has_filename(self, qb_service, test_bill, test_pdf_file):
        """Test that attachment has correct filename"""
        attach = qb_service.add_attachment(test_pdf_file, test_bill)
        
        assert attach.FileName is not None
        assert attach.FileName.endswith('.pdf')
        print(f"✓ Attachment has filename: {attach.FileName}")

    def test_attachment_linked_to_bill(self, qb_service, test_bill, test_pdf_file):
        """Test that attachment is linked to the bill"""
        attach = qb_service.add_attachment(test_pdf_file, test_bill)
        
        assert attach.AttachableRef is not None
        assert len(attach.AttachableRef) > 0
        assert attach.AttachableRef[0].EntityRef.value == test_bill.Id
        print(f"✓ Attachment linked to bill: {test_bill.Id}")

    def test_attach_to_purchase(self, qb_service, test_pdf_file):
        """Test attaching file to a Purchase transaction"""
        line_items = [
            InvoiceLine(item="Receipt Item", rate=50.00, quantity=1.0, category="supplies")
        ]
        
        draft = InvoiceDraft(
            vendor_display_name="Purchase Test Vendor",
            invoice_number=f"PURCH-ATTACH-{int(datetime.datetime.now().timestamp()) % 1000000}",
            invoice_date=datetime.date.today().strftime("%m/%d/%Y"),
            total_amount=50.00,
            line_items=line_items,
            is_receipt=True
        )
        
        purchase = qb_service.push_receipt(draft)
        attach = qb_service.add_attachment(test_pdf_file, purchase)
        
        assert attach is not None
        assert attach.AttachableRef[0].EntityRef.value == purchase.Id
        print(f"✓ File attached to purchase: {purchase.Id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
