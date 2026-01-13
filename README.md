# AI Invoice Processor

Automated invoice processing system that extracts invoice data from Gmail attachments and creates bills in QuickBooks using AI.

## Features

• **Smart Email Classification** - Automatically identifies invoice emails using AI
• **Dual PDF Processing** - Handles both text-based and image-based (scanned) PDF invoices
• **AI Data Extraction** - Uses OpenAI GPT-4 to extract structured invoice data
• **QuickBooks Integration** - Automatically creates vendor bills with line items and tax
• **Invoice Tracking** - Captures invoice numbers, dates, and due dates
• **Gmail Automation** - Fetches unprocessed emails and labels them after processing

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
│   ├── main.py              # Main application logic
│   ├── gmail.py             # Gmail attachment fetching
│   ├── pdf_parser.py        # PDF text extraction
│   └── quickbooks_service.py # QuickBooks bill creation
├── attachments/             # Downloaded invoice files (gitignored)
├── credentials.json         # Gmail OAuth credentials (gitignored)
├── token.json              # Gmail access token (gitignored)
├── .env                    # Environment variables (gitignored)
└── requirements.txt        # Python dependencies
```

## How It Works

### 1. Email Fetching
Connects to Gmail API and fetches emails with PDF or image attachments that haven't been processed (no "ai_checked" label).

### 2. Invoice Classification
Uses OpenAI to classify whether an email contains an invoice based on:
• Email content
• Attachment filenames
• Contextual information

### 3. Data Extraction

**For text-based PDFs:**
• Extracts text using pdfplumber
• Sends text to OpenAI for structured data extraction

**For image-based PDFs:**
• Converts PDF pages to images using pdf2image
• Uploads images to OpenAI Files API
• Uses GPT-4 Vision to extract invoice data

**Extracted data includes:**
• Vendor name
• Invoice number
• Invoice date and due date
• Line items (description, quantity, rate)
• Tax amount
• Total amount

### 4. QuickBooks Bill Creation
Creates a vendor bill in QuickBooks with:
• Vendor matching or creation
• Line items with descriptions
• Separate tax line item
• Invoice metadata

### 5. Gmail Labeling
Marks processed emails with "ai_checked" label to avoid reprocessing.

## Configuration

### Adjusting Email Fetch Count

In `main.py`, modify:
```python
messages = list(fetch_messages_with_attachments(max_results=10))
```

### Changing QuickBooks Account

In `push_invoice.py`, update the account reference:
```python
account_ref.value = 1  # Change to your expense account ID
```

## Error Handling

The system handles:
• Invalid or corrupted PDFs
• Missing invoice data
• QuickBooks API errors
• OAuth token expiration
• Missing attachments

## Limitations

• Requires valid Gmail and QuickBooks API credentials
• OpenAI API calls incur costs
• QuickBooks refresh tokens expire after 101 days
• Tax is added as a line item, not proper tax tracking
• Processes one email at a time (no parallel processing)

## Future Enhancements

• Bank transaction matching to invoices
• Multi-page invoice support
• Batch processing
• Web dashboard
• Email notifications
• Invoice approval workflow

## License

MIT

## Author

Daniel Brooks
