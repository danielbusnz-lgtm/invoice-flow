#!/usr/bin/env python3
"""
Test a single invoice file (PDF or image)
"""
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
import sys
from pdf_parser import extract_text_from_pdf
from push_invoice import InvoiceDraft

# Load environment variables
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env")


def build_invoice_draft(message_text: str, client: OpenAI) -> InvoiceDraft | None:
    """Extract invoice data from text using OpenAI"""
    try:
        response = client.responses.parse(
            model="gpt-4o-2024-08-06",
            input=[
                {
                    "role": "system",
                    "content": (
                        "Extract structured invoice data from the provided text. "
                        "Always respond with JSON matching the schema. "
                        "If you do not find invoice information, return an empty items list. "
                        "Our company name is Cape Property Pros, and we are always the receiver of the invoice."
                    ),
                },
                {"role": "user", "content": message_text},
            ],
            text_format=InvoiceDraft,
        )
        return response.output_parsed
    except Exception as e:
        print(f"Error: {e}")
        return None


def test_pdf(file_path: Path):
    """Test a PDF invoice"""
    print(f"\nTesting PDF: {file_path.name}")
    print("=" * 70)

    # Extract text from PDF
    pdf_text = extract_text_from_pdf(file_path)
    print(f"Extracted {len(pdf_text)} characters of text\n")

    if len(pdf_text) < 50:
        print("✗ ERROR: Insufficient text extracted from PDF")
        return

    # Show first 500 chars of extracted text
    print("First 500 characters of extracted text:")
    print("-" * 70)
    print(pdf_text[:500])
    print("-" * 70)

    # Build invoice
    client = OpenAI()
    invoice = build_invoice_draft(pdf_text, client)

    if invoice and invoice.line_items:
        print("\n✓ SUCCESS! Invoice data extracted:")
        print(f"  Vendor: {invoice.vendor_display_name}")
        print(f"  Total: ${invoice.total_amount:.2f}" if invoice.total_amount else "  Total: Not specified")
        print(f"  Tax: ${invoice.tax:.2f}" if invoice.tax else "  Tax: Not specified")
        if invoice.memo:
            print(f"  Memo: {invoice.memo}")
        print(f"\n  Line Items ({len(invoice.line_items)}):")
        for i, item in enumerate(invoice.line_items, 1):
            amount = item.quantity * item.rate
            print(f"    {i}. {item.item}")
            print(f"       Qty: {item.quantity} × ${item.rate:.2f} = ${amount:.2f}")
            if item.description:
                print(f"       Description: {item.description}")
    else:
        print("\n✗ FAILED: No valid invoice data extracted")


def test_image(file_path: Path):
    """Test an image invoice using OpenAI Vision"""
    print(f"\nTesting Image: {file_path.name}")
    print("=" * 70)

    import base64

    # Read and encode image
    with open(file_path, 'rb') as f:
        image_data = base64.b64encode(f.read()).decode('utf-8')

    # Determine image type
    ext = file_path.suffix.lower()
    mime_type = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp'
    }.get(ext, 'image/jpeg')

    client = OpenAI()

    try:
        response = client.responses.parse(
            model="gpt-4o-2024-08-06",
            input=[
                {
                    "role": "system",
                    "content": (
                        "Extract structured invoice data from the invoice image. "
                        "Always respond with JSON matching the schema. "
                        "If you do not find invoice information, return an empty items list. "
                        "Our company name is Cape Property Pros, and we are always the receiver of the invoice."
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_data}"
                            }
                        },
                        {
                            "type": "text",
                            "text": "Extract the invoice data from this image."
                        }
                    ]
                },
            ],
            text_format=InvoiceDraft,
        )
        invoice = response.output_parsed

        if invoice and invoice.line_items:
            print("\n✓ SUCCESS! Invoice data extracted:")
            print(f"  Vendor: {invoice.vendor_display_name}")
            print(f"  Total: ${invoice.total_amount:.2f}" if invoice.total_amount else "  Total: Not specified")
            print(f"  Tax: ${invoice.tax:.2f}" if invoice.tax else "  Tax: Not specified")
            if invoice.memo:
                print(f"  Memo: {invoice.memo}")
            print(f"\n  Line Items ({len(invoice.line_items)}):")
            for i, item in enumerate(invoice.line_items, 1):
                amount = item.quantity * item.rate
                print(f"    {i}. {item.item}")
                print(f"       Qty: {item.quantity} × ${item.rate:.2f} = ${amount:.2f}")
                if item.description:
                    print(f"       Description: {item.description}")
        else:
            print("\n✗ FAILED: No valid invoice data extracted")

    except Exception as e:
        print(f"\n✗ ERROR: {e}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_single_invoice.py <file_path>")
        sys.exit(1)

    file_path = Path(sys.argv[1])

    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    # Determine file type and test accordingly
    if file_path.suffix.lower() == '.pdf':
        test_pdf(file_path)
    elif file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
        test_image(file_path)
    else:
        print(f"Error: Unsupported file type: {file_path.suffix}")
        sys.exit(1)


if __name__ == "__main__":
    main()
