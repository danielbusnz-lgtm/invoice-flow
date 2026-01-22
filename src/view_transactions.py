from services.quickbooks_service import QuickbooksInvoiceService
from quickbooks.objects.purchase import Purchase
from quickbooks.objects.bill import Bill

qb = QuickbooksInvoiceService()

print("\n" + "=" * 60)
print("RECENT BILLS")
print("=" * 60)
bills = Bill.all(qb=qb.qb_client, max_results=5)
for bill in bills:
    vendor = bill.VendorRef.name if bill.VendorRef else "Unknown"
    print(f"Bill ID: {bill.Id}")
    print(f"  Vendor: {vendor}")
    print(f"  Amount: ${bill.TotalAmt}")
    print(f"  Date: {bill.TxnDate}")
    print(f"  Doc#: {bill.DocNumber if hasattr(bill, 'DocNumber') and bill.DocNumber else 'N/A'}")
    print()

print("\n" + "=" * 60)
print("RECENT PURCHASES (Bank Transactions)")
print("=" * 60)
purchases = Purchase.all(qb=qb.qb_client, max_results=5)
for purchase in purchases:
    entity = purchase.EntityRef.name if hasattr(purchase, 'EntityRef') and purchase.EntityRef else "N/A"
    print(f"Purchase ID: {purchase.Id}")
    print(f"  Entity: {entity}")
    print(f"  Amount: ${purchase.TotalAmt}")
    print(f"  Date: {purchase.TxnDate}")
    print(f"  Payment Type: {purchase.PaymentType}")
    print()

print("\nYou can match these by vendor + amount + date")
