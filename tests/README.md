# Test Suite for Invoice Flow

Comprehensive test coverage for all QuickBooks invoice automation features.

## Test Files

• **test_bill_creation.py** - Test creating Bills from unpaid invoices
• **test_receipt_creation.py** - Test creating Purchases from receipts
• **test_customer_matching.py** - Test customer matching by name/address
• **test_vendor_management.py** - Test vendor creation and matching
• **test_category_mapping.py** - Test expense category to account mapping
• **test_duplicate_detection.py** - Test duplicate bill prevention
• **test_attachments.py** - Test file attachment functionality

## Running Tests

**Run all tests:**
```bash
pytest tests/
```

**Run specific test file:**
```bash
pytest tests/test_bill_creation.py
```

**Run with verbose output:**
```bash
pytest tests/ -v
```

**Run specific test:**
```bash
pytest tests/test_bill_creation.py::TestBillCreation::test_create_basic_bill
```

## Requirements

Install pytest:
```bash
pip install pytest
```

## Environment Setup

Tests use the same QuickBooks sandbox environment as the main application. Make sure your .env file is configured with:
• ENVIRONMENT=sandbox
• SAND_CLIENT_ID
• SAND_CLIENT_SECRET
• REFRESH_TOKEN
• QB_REALM_ID

## Notes

• Tests create real transactions in QuickBooks sandbox
• Some tests may be skipped if required data (customers, vendors) doesn't exist
• Each test run may create multiple test records
• Test data uses unique timestamps to avoid conflicts
