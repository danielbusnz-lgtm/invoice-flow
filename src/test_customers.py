from services.quickbooks_service import QuickbooksInvoiceService

qb = QuickbooksInvoiceService()

# Get customer context that will be sent to AI
customers_context = qb.get_customers_context()

print("CUSTOMER CONTEXT FOR AI:")
print("=" * 60)
print(customers_context)
print("=" * 60)
print("\nThis context will be included in AI prompts to help match invoices to customers.")
