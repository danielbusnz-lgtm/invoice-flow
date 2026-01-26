import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.quickbooks_service import QuickbooksInvoiceService
from models.invoice import InvoiceLine, InvoiceDraft
import datetime

# Create test receipt data
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

draft = InvoiceDraft(
    vendor_display_name="Home Depot",
    invoice_number="RECEIPT-12345",
    invoice_date=datetime.date.today().strftime("%m/%d/%Y"),
    total_amount=175.00,
    tax=0.00,
    line_items=line_items,
    is_receipt=True,  # Mark as receipt
    job_site_address="123 Main St"
)

print("Creating test receipt (Purchase transaction)...")
print(f"Vendor: {draft.vendor_display_name}")
print(f"Total: ${draft.total_amount}")
print(f"Date: {draft.invoice_date}")
print(f"Is Receipt: {draft.is_receipt}")
print("\nLine items:")
for line in draft.line_items:
    print(f"  • {line.item}: ${line.amount}")

# Push to QuickBooks
qb = QuickbooksInvoiceService()
purchase = qb.push_receipt(draft)

print(f"\n✓ Purchase created!")
print(f"  ID: {purchase.Id}")
print(f"  Vendor: {draft.vendor_display_name}")
print(f"  Amount: ${draft.total_amount}")
print(f"\nThis receipt is recorded as an expense (already paid)")
