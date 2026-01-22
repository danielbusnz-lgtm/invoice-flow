from services.quickbooks_service import QuickbooksInvoiceService
from quickbooks.objects.customer import Customer

qb = QuickbooksInvoiceService()

# Get all customers
customers = Customer.all(qb=qb.qb_client)

print("CUSTOMERS:")
for customer in customers:
    print(f"ID: {customer.Id}, Name: {customer.DisplayName}")
    addr =  customer.BillAddr
    print(addr)
