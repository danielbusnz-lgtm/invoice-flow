import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.quickbooks_service import QuickbooksInvoiceService
from models.invoice import InvoiceDraft, InvoiceLine

# Create line items
line_items = [
    InvoiceLine(
        item="Test Item 1",
        rate=60.00,
        quantity=2.0,
        description="Test description"
    ),
    InvoiceLine(
        item="Test Item 2",
        rate=40.00,
        quantity=1.0
    )
]

# Calculate total
tax = 20.00
items_total = sum(line.amount for line in line_items)
total_amount = items_total + tax

# Create test invoice
draft = InvoiceDraft(
    vendor_display_name="Test Vendor LLC",
    invoice_number="TEST-010",
    invoice_date="2026-01-22",
    due_date="2026-02-22",
    total_amount=total_amount,
    tax=tax,
    memo="Test invoice",
    line_items=line_items
)

# Push to QuickBooks
qb = QuickbooksInvoiceService()
bill = qb.push_invoice(draft)

print(f"Success! Bill ID: {bill.Id}")
print(f"Vendor: {bill.VendorRef.name}")
print(f"Total: ${bill.TotalAmt}")
