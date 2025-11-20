from quickstart import QuickBooksInvoiceService


def main():
    # Initialize the QuickBooks service (requires environment variables)
    qb_service = QuickBooksInvoiceService()

    # Test vendor lookup
    vendor = qb_service.ensure_vendor("Nauset Disposal", None)
 


if __name__ == "__main__":
    main()
