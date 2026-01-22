import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.quickbooks_service import QuickbooksInvoiceService
from quickbooks.objects.bill import Bill
from quickbooks.objects.purchase import Purchase
from quickbooks.objects.deposit import Deposit
from quickbooks.objects.payment import Payment
from quickbooks.objects.billpayment import BillPayment
from collections import defaultdict                                                                                                                     


qb = QuickbooksInvoiceService()


print("\n" + "="*60)
print("BILLS")
print("="*60)


bills = Bill.all(qb=qb.qb_client)



bill_groups = defaultdict(list)
for bill in bills:
    vendor_name = bill.VendorRef.name if bill.VendorRef else "Unknown" 
    key = (vendor_name, bill.TotalAmt, bill.TxnDate)
    bill_groups[key].append(bill)
    

duplicates = {k: v for k, v in bill_groups.items() if len(v) > 1}


if duplicates:
    print(f"{len(duplicates)} duplicates found(Vendor, Amount, Date match)")
    for (vendor, amount, date), bills_list in duplicates.items():
        print(f"Vendor: {vendor}, Amount: ${amount}, Date: {date}")
        for bill in bills_list:
            vendor_name = bill.VendorRef.name if bill.VendorRef else "Unknown"
            print(f"  - {vendor_name} (ID: {bill.Id})")


else:
    print("no duplicates found\n")
print("\n")

soft_groups = defaultdict(list)
for bill in bills:
    vendor_name = bill.VendorRef.name if bill.VendorRef else "Unknown"
    key = (bill.TotalAmt, bill.TxnDate)
    soft_groups[key].append(bill)

soft_duplicates =  {k: v for k, v in soft_groups.items() if len(v) > 1}


if soft_duplicates:
    print(f"{len(soft_duplicates)} soft duplicates found (Amount and Date match)")
    for (amount, date), bills_list in soft_duplicates.items():
        print(f"Amount: ${amount}, Date: {date}")
        for bill in bills_list:
            vendor_name = bill.VendorRef.name if bill.VendorRef else "Unknown"
            print(f"  - {vendor_name} (ID: {bill.Id})")
        print("-" * 40)
else:
    print("no soft duplicates found")

print("\n" + "="*60)
print("PURCHASES (Expenses/Checks)")
print("="*60)

purchases = Purchase.all(qb=qb.qb_client)
purchase_groups = defaultdict(list)

for purchase in purchases:
    entity_name = purchase.EntityRef.name if purchase.EntityRef else "Unknown"
    key = (entity_name, purchase.TotalAmt, purchase.TxnDate)
    purchase_groups[key].append(purchase)

purchase_duplicates = {k: v for k, v in purchase_groups.items() if len(v) > 1}

if purchase_duplicates:
    print(f"{len(purchase_duplicates)} duplicate purchases found")
    for (entity, amount, date), purchases_list in purchase_duplicates.items():
        print(f"Entity: {entity}, Amount: ${amount}, Date: {date}")
        for p in purchases_list:
            print(f"  - ID: {p.Id}")
        print("-" * 40)
else:
    print("No duplicate purchases found")

# Soft matches for purchases
purchase_soft_groups = defaultdict(list)
for purchase in purchases:
    entity_name = purchase.EntityRef.name if purchase.EntityRef else "Unknown"
    key = (purchase.TotalAmt, purchase.TxnDate)
    purchase_soft_groups[key].append(purchase)

purchase_soft_duplicates = {k: v for k, v in purchase_soft_groups.items() if len(v) > 1}

if purchase_soft_duplicates:
    print(f"\n{len(purchase_soft_duplicates)} purchase soft matches found (Amount and Date match)")
    for (amount, date), purchases_list in purchase_soft_duplicates.items():
        print(f"Amount: ${amount}, Date: {date}")
        for p in purchases_list:
            entity_name = p.EntityRef.name if p.EntityRef else "Unknown"
            print(f"  - {entity_name} (ID: {p.Id})")
        print("-" * 40)
else:
    print("\nNo purchase soft matches found")

print("\n" + "="*60)
print("DEPOSITS")
print("="*60)

deposits = Deposit.all(qb=qb.qb_client)
deposit_groups = defaultdict(list)

for deposit in deposits:
    key = (deposit.TotalAmt, deposit.TxnDate)
    deposit_groups[key].append(deposit)

deposit_duplicates = {k: v for k, v in deposit_groups.items() if len(v) > 1}

if deposit_duplicates:
    print(f"{len(deposit_duplicates)} duplicate deposits found")
    for (amount, date), deposits_list in deposit_duplicates.items():
        print(f"Amount: ${amount}, Date: {date}")
        for d in deposits_list:
            print(f"  - ID: {d.Id}")
        print("-" * 40)
else:
    print("No duplicate deposits found")

print("\n" + "="*60)
print("PAYMENTS (Customer Payments)")
print("="*60)

payments = Payment.all(qb=qb.qb_client)
payment_groups = defaultdict(list)

for payment in payments:
    customer_name = payment.CustomerRef.name if payment.CustomerRef else "Unknown"
    key = (customer_name, payment.TotalAmt, payment.TxnDate)
    payment_groups[key].append(payment)

payment_duplicates = {k: v for k, v in payment_groups.items() if len(v) > 1}

if payment_duplicates:
    print(f"{len(payment_duplicates)} duplicate payments found")
    for (customer, amount, date), payments_list in payment_duplicates.items():
        print(f"Customer: {customer}, Amount: ${amount}, Date: {date}")
        for p in payments_list:
            print(f"  - ID: {p.Id}")
        print("-" * 40)
else:
    print("No duplicate payments found")

# Soft matches for payments
payment_soft_groups = defaultdict(list)
for payment in payments:
    customer_name = payment.CustomerRef.name if payment.CustomerRef else "Unknown"
    key = (payment.TotalAmt, payment.TxnDate)
    payment_soft_groups[key].append(payment)

payment_soft_duplicates = {k: v for k, v in payment_soft_groups.items() if len(v) > 1}

if payment_soft_duplicates:
    print(f"\n{len(payment_soft_duplicates)} payment soft matches found (Amount and Date match)")
    for (amount, date), payments_list in payment_soft_duplicates.items():
        print(f"Amount: ${amount}, Date: {date}")
        for p in payments_list:
            customer_name = p.CustomerRef.name if p.CustomerRef else "Unknown"
            print(f"  - {customer_name} (ID: {p.Id})")
        print("-" * 40)
else:
    print("\nNo payment soft matches found")

print("\n" + "="*60)
print("BILL PAYMENTS")
print("="*60)

bill_payments = BillPayment.all(qb=qb.qb_client)
bill_payment_groups = defaultdict(list)

for bp in bill_payments:
    vendor_name = bp.VendorRef.name if bp.VendorRef else "Unknown"
    key = (vendor_name, bp.TotalAmt, bp.TxnDate)
    bill_payment_groups[key].append(bp)

bill_payment_duplicates = {k: v for k, v in bill_payment_groups.items() if len(v) > 1}

if bill_payment_duplicates:
    print(f"{len(bill_payment_duplicates)} duplicate bill payments found")
    for (vendor, amount, date), bp_list in bill_payment_duplicates.items():
        print(f"Vendor: {vendor}, Amount: ${amount}, Date: {date}")
        for bp in bp_list:
            print(f"  - ID: {bp.Id}")
        print("-" * 40)
else:
    print("No duplicate bill payments found")

# Soft matches for bill payments
bp_soft_groups = defaultdict(list)
for bp in bill_payments:
    vendor_name = bp.VendorRef.name if bp.VendorRef else "Unknown"
    key = (bp.TotalAmt, bp.TxnDate)
    bp_soft_groups[key].append(bp)

bp_soft_duplicates = {k: v for k, v in bp_soft_groups.items() if len(v) > 1}

if bp_soft_duplicates:
    print(f"\n{len(bp_soft_duplicates)} bill payment soft matches found (Amount and Date match)")
    for (amount, date), bp_list in bp_soft_duplicates.items():
        print(f"Amount: ${amount}, Date: {date}")
        for bp in bp_list:
            vendor_name = bp.VendorRef.name if bp.VendorRef else "Unknown"
            print(f"  - {vendor_name} (ID: {bp.Id})")
        print("-" * 40)
else:
    print("\nNo bill payment soft matches found")
