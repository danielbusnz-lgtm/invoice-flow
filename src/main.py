# Standard library imports
import glob
import tempfile
from pathlib import Path

# Third-party imports
from openai import OpenAI
from pdf2image import convert_from_path
from googleapiclient.discovery import build

# QuickBooks imports
from quickbooks.exceptions import QuickbooksException

# Local imports
from parsers.pdf_parser import extract_text_from_pdf
from parsers.ai_parser import invoice_label, pdf_invoice, ai_invoice
from services.quickbooks_service import QuickbooksInvoiceService
from services.gmail_service import fetch_messages_with_attachments
from utils.auth import load_creds, get_or_create_label


# Main Processing Function
def main():
    try:
        creds = load_creds()
        service = build("gmail", "v1", credentials=creds)
        get_or_create_label(service, "ai_checked")

    except QuickbooksException as e:
        print(f"quickbooks error '{e.message}'(code:'{e.error_code}'")
        print(f"quickbooks detail:'{e.detail}'")
        return

    project_root = Path(__file__).parent.parent
    download_dir = project_root / "attachments"
    download_dir.mkdir(exist_ok=True)
    qb_service = QuickbooksInvoiceService()
    openai_client = OpenAI()

    # Get customer context for AI matching
    print("Loading customer addresses for AI matching...")
    customers_context = qb_service.get_customers_context()

    messages = list(fetch_messages_with_attachments(max_results=10))

    # Process each message
    for idx, (message_id, subject, message_text, attachments) in enumerate(messages, start=1):
        draft = None
        label = invoice_label(message_text, attachments, client=openai_client)
        print(f"[{idx}/{len(messages)}] {message_id}: subject -> {subject} label -> {label}")

        project_root = Path(__file__).parent.parent
        attachments_dir = project_root / "attachments"

        # Get the actual attachment file for this email
        latest_file = None
        if attachments:
            attachment_filename = attachments[0][0]
            latest_file = str(attachments_dir / attachment_filename)


        if label == "invoice" and latest_file:
            print("starting ai_invoice process")
            draft = None

            if latest_file.lower().endswith('.pdf'):
                path = Path(latest_file)
                text = extract_text_from_pdf(path)

                if text is None or len(text.strip()) < 10:
                    # Image-based PDF - convert to images
                    print("PDF is image-based, converting to images")
                    with tempfile.TemporaryDirectory() as temp_dir:
                        images_from_path = convert_from_path(latest_file, output_folder=temp_dir, fmt='jpg')

                        image_files = glob.glob(f"{temp_dir}/*.jpg")
                        first_image = image_files[0] if image_files else None

                        if first_image:
                            print("Processing as image")
                            draft = ai_invoice(message_text, file_path=first_image, client=openai_client, customers_context=customers_context)
                else:
                    # Text-based PDF
                    print("PDF has extractable text")
                    draft = pdf_invoice(message_text, text=text, client=openai_client, customers_context=customers_context)

            elif latest_file.endswith(('.jpeg', '.jpg', '.png')):
                print('THIS IS A JPEG')
                draft = ai_invoice(message_text=message_text, file_path=latest_file, client=openai_client, customers_context=customers_context)

            print(f"Draft result: {draft}")

        # Push to QuickBooks if valid draft
        if draft:
            # Check if it's a receipt
            if hasattr(draft, 'is_receipt') and draft.is_receipt:
                print(f"[{idx}/{len(messages)}] {message_id}: RECEIPT detected - skipping (already paid)")
                continue

            print(f"[{idx}/{len(messages)}] {message_id}: line items:")

            for line in draft.line_items:
                print("   ", line.model_dump())

            # Verify total
            calculated_total = draft.total_amount
            if draft.total_amount is not None:
                if abs(draft.total_amount - calculated_total) > 0.01:
                    print(f"[{idx}/{len(messages)}] {message_id}: total mismatch (draft={draft.total_amount}, calculated={calculated_total})")
            else:
                draft.total_amount = calculated_total
                print(draft.total_amount)

            # Push to QuickBooks
            invoice = qb_service.push_invoice(draft)
            invoice_id = getattr(invoice, "Id", None)
            if invoice_id:
                print(f"[{idx}/{len(messages)}] {message_id}: QuickBooks invoice created (Id={invoice_id})")
            else:
                print(f"[{idx}/{len(messages)}] {message_id}: QuickBooks invoice created")
        else:
            print(f"[{idx}/{len(messages)}] {message_id}: no valid invoice data found")


if __name__ == "__main__":
    main()
