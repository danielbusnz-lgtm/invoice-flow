# AI Invoice Processor

Automated invoice processing system that extracts invoice data from Gmail attachments and creates bills in QuickBooks using AI.

## Features

### Core Processing
**Intelligent Email Classification** - AI-powered detection of invoice emails based on content, attachments, and context

**Format-Agnostic PDF Processing** - Automatically detects and handles text-based PDFs, scanned PDFs, and image files (JPEG, PNG, JPG)

**AI-Powered Data Extraction** - GPT-4 Vision extracts vendor, invoice number, dates, line items, tax, and total from any document format

### Smart Matching & Deduplication
**Intelligent Customer Matching** - AI-powered customer identification with address-based fallback and fuzzy name matching

**Automatic Vendor Management** - Fuzzy vendor matching with auto-creation for new vendors

**Duplicate Prevention** - Multi-level detection by invoice number, vendor, date, and amount to prevent duplicate entries

### QuickBooks Operations
**Invoice vs Receipt Detection** - Automatically routes unpaid invoices to Bills and already-paid expenses to Purchases

**Expense Category Mapping** - Intelligent mapping of extracted categories to QuickBooks expense accounts (materials, labor, equipment, fuel, permits, supplies, utilities, etc.)

**Transaction Creation** - Creates fully-formed Bill or Purchase transactions with line items, tax, customer assignments, and vendor references

**File Attachments** - Automatically attaches original invoice files to QuickBooks transactions with proper MIME typing

### Automation & Integration
**Gmail Integration** - Fetches unprocessed emails, extracts attachments, and labels processed messages

**Token Management** - Automatic OAuth token refresh with .env persistence

**Sandbox/Production Support** - Seamless environment switching for testing and production workflows

## Prerequisites

• Python 3.11+
• Gmail API credentials
• QuickBooks API credentials (production or sandbox)
• OpenAI API key
• poppler-utils (for PDF to image conversion)

## Installation

### 1. Install system dependencies

```bash
# Linux
sudo apt-get install poppler-utils

# macOS
brew install poppler
```

### 2. Clone and setup

```bash
git clone https://github.com/danielbusnz-lgtm/invoice-flow.git
cd invoice-flow
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file based on `.env.example`:

```env
# OpenAI
OPENAI_API_KEY=your_openai_key

# QuickBooks OAuth
CLIENT_ID=your_quickbooks_client_id
CLIENT_SECRET=your_quickbooks_client_secret
QB_REALM_ID=your_company_id
ENVIRONMENT=production
REDIRECT_URI=https://developer.intuit.com/v2/OAuth2Playground/RedirectUrl
REFRESH_TOKEN=your_refresh_token
```

### 4. Setup Gmail API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Gmail API
4. Create OAuth 2.0 credentials
5. Download credentials as `credentials.json` in project root

### 5. Setup QuickBooks API

1. Go to [QuickBooks Developer Portal](https://developer.intuit.com/)
2. Create an app
3. Get your Client ID and Client Secret
4. Use OAuth Playground to get refresh token
5. Add credentials to `.env` file

## Usage

Run the invoice processor:

```bash
python src/main.py
```

The script will:
1. Fetch unprocessed emails from Gmail
2. Classify emails as invoices or not
3. Extract invoice data using AI
4. Create bills in QuickBooks
5. Label processed emails

## Project Structure

```
invoice-flow/
├── src/
│   ├── main.py                      # Main application entry point
│   ├── api/                         # API endpoints
│   ├── models/
│   │   └── invoice.py               # Invoice data model
│   ├── parsers/
│   │   ├── pdf_parser.py            # PDF text extraction
│   │   └── ai_parser.py             # AI-powered data extraction
│   ├── services/
│   │   ├── gmail_service.py         # Gmail API integration
│   │   └── quickbooks_service.py    # QuickBooks API integration
│   └── utils/
│       └── auth.py                  # Authentication utilities
├── tests/
│   ├── test_bill_creation.py        # Bill creation tests
│   ├── test_customer_matching.py    # Customer matching tests
│   ├── test_vendor_management.py    # Vendor management tests
│   ├── test_duplicate_detection.py  # Duplicate detection tests
│   ├── test_receipt_creation.py     # Receipt creation tests
│   ├── test_category_mapping.py     # Category mapping tests
│   ├── test_attachments.py          # Attachment handling tests
│   └── run_all_tests.sh             # Test runner script
├── scripts/
│   ├── refresh_token.py             # Token refresh utility
│   ├── get_accounts.py              # Account retrieval utility
│   ├── duplicates.py                # Duplicate detection script
│   └── test_receipt.py              # Receipt testing utility
├── attachments/                     # Downloaded invoice files (gitignored)
├── credentials.json                 # Gmail OAuth credentials (gitignored)
├── token.json                       # Gmail access token (gitignored)
├── .env                             # Environment variables (gitignored)
├── requirements.txt                 # Python dependencies
└── README.md                        # This file
```

## How It Works

### 1. Email Fetching
Connects to Gmail API and fetches emails with PDF or image attachments that haven't been processed (no "ai_checked" label).

### 2. Invoice Classification
Uses OpenAI to classify whether an email contains an invoice based on:
• Email content
• Attachment filenames
• Contextual information

### 3. Format Detection & Processing
Intelligently routes attachments to the appropriate processor:
• **PDF files** - Attempts text extraction using pdfplumber
  • If text is found → processes as text-based PDF
  • If no text found → converts to images and uses vision processing
• **Image files** (JPEG, PNG, JPG) - Directly processes as vision documents
• All documents processed with OpenAI GPT-4 Vision for maximum accuracy

### 4. AI Data Extraction
Uses context-aware extraction to obtain:
• Vendor name
• Invoice number
• Invoice date and due date
• Line items (description, quantity, unit rate, category)
• Tax amount
• Total amount
• Job site address (if present)
• Payment status (invoice vs receipt)

The AI also receives context about existing customers in QuickBooks to improve matching accuracy.

### 5. Intelligent Matching & Validation

**Customer Matching:**
• AI attempts to identify the job site customer from invoice
• Falls back to address-based matching if no name found
• Uses fuzzy matching for similar customer names

**Vendor Management:**
• Checks if vendor exists in QuickBooks
• Uses fuzzy matching to find similar vendor names
• Automatically creates new vendors if no match found

**Duplicate Detection:**
• Checks for existing bills by invoice number
• Checks for vendor/date/amount combinations
• Prevents accidental duplicate entries

**Category Mapping:**
• Maps expense categories to QuickBooks accounts
• Supports categories: materials, labor, equipment, fuel, permits, supplies, disposal, plants, soil, sprinklers, repairs, telephone, utilities, gas/electric
• Falls back to default expense account if category not recognized

### 6. QuickBooks Transaction Creation

**For Invoices (unpaid):**
• Creates a Bill in QuickBooks
• Assigns vendor reference
• Sets transaction and due dates
• Adds line items with mapped expense accounts
• Assigns customer reference if found
• Adds tax as a separate line item

**For Receipts (already-paid):**
• Creates a Purchase transaction in QuickBooks
• Marks as already-paid (CreditCard payment type)
• Follows same line item and customer assignment logic
• Tracks as completed expense

**File Attachment:**
• Automatically attaches the original invoice file to the transaction
• Sets appropriate MIME type based on file format
• Links attachment to the transaction for audit trail

### 7. Gmail Labeling
Marks processed emails with "ai_checked" label to avoid reprocessing.

### 8. Token Management
Automatically saves refreshed QuickBooks OAuth tokens to .env file to maintain session validity.

## Configuration

### Environment Setup

In `.env` file:
```env
# OpenAI
OPENAI_API_KEY=your_openai_key

# QuickBooks (Sandbox)
SAND_CLIENT_ID=sandbox_client_id
SAND_CLIENT_SECRET=sandbox_client_secret

# QuickBooks (Production)
CLIENT_ID=production_client_id
CLIENT_SECRET=production_client_secret
QB_REALM_ID=your_company_id
REFRESH_TOKEN=your_refresh_token

# Environment selection
ENVIRONMENT=production  # or 'sandbox'
REDIRECT_URI=https://developer.intuit.com/v2/OAuth2Playground/RedirectUrl

# Default expense account
QB_EXPENSE_ACCOUNT_ID=31

# Gmail
GOOGLE_OAUTH_SCOPES=...
```

### Adjusting Email Fetch Count

In `main.py`, modify:
```python
messages = list(fetch_messages_with_attachments(max_results=10))
```

### Customizing Category to Account Mapping

In `src/services/quickbooks_service.py`, update the `match_category_to_account()` method:
```python
category_map = {
    'materials': '63',      # Job Materials
    'labor': '59',          # Cost of Labor
    'equipment': '29',      # Equipment Rental
    'fuel': '56',          # Fuel
    'permits': '68',        # Permits
    # Add more categories as needed
}
```

### Switching Between Sandbox and Production

Change the `ENVIRONMENT` variable in `.env`:
```env
ENVIRONMENT=sandbox    # For testing
ENVIRONMENT=production # For live data
```

The system will automatically use the appropriate credentials based on this setting.

## Error Handling

The system gracefully handles:
• Invalid or corrupted PDFs - falls back to image processing
• Missing invoice data - skips incomplete invoices with logging
• QuickBooks API errors - catches and logs API exceptions
• OAuth token expiration - automatically refreshes tokens
• Missing attachments - skips emails without files
• Duplicate entries - detects and prevents duplicate bills
• Missing vendors/customers - creates new entities as needed
• Account/category mismatches - uses default accounts

## Limitations

• Requires valid Gmail and QuickBooks API credentials
• OpenAI API calls incur costs (especially for vision processing)
• QuickBooks refresh tokens expire after 101 days (auto-renewed on each run)
• Tax is added as a line item, not as formal tax tracking
• Processes one email at a time (sequential processing, no parallel workers)
• Requires existing QuickBooks customers for proper job site matching
• Line item categorization relies on AI extraction accuracy
• Image-based PDFs may require higher quality scans for accurate extraction

## Troubleshooting

### Token Expiration
If you get OAuth errors:
```bash
python scripts/refresh_token.py
```

### Checking QB Accounts
To see available accounts for category mapping:
```bash
python scripts/get_accounts.py
```

### Testing Invoice Processing
To test a single receipt file:
```bash
python scripts/test_receipt.py
```

## Future Enhancements

• Bank transaction matching and reconciliation
• Web dashboard for invoice review and approval
• Email notifications for processing results
• Invoice approval workflow with human-in-the-loop
• Batch processing with parallel workers
• Advanced OCR for complex invoice formats
• Multi-currency support
• Automated payment processing
• Invoice analytics and reporting
• Custom field mapping for QuickBooks
• Support for multiple QB realms/companies

## License

MIT

## Author

Daniel Brooks
