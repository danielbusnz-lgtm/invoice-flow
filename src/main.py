# Standard library imports
import glob
import tempfile
from pathlib import Path

# Third-party imports
from openai import OpenAI
from pdf2image import convert_from_path

# QuickBooks imports
from quickbooks.exceptions import QuickbooksException

# Local imports
from parsers.pdf_parser import extract_text_from_pdf
from parsers.ai_parser import invoice_label, pdf_invoice, ai_invoice, parse_shipping, parse_client_communication
from services.quickbooks_service import QuickbooksInvoiceService
from services.outlook_service import fetch_messages_with_attachments, label_message
from services.notion_service import push_invoice_to_notion, push_shipping_to_notion, push_client_comm_to_notion
from services.tracker import is_processed, mark_processed


# Main Processing Function
def main():
    project_root = Path(__file__).parent.parent
    download_dir = project_root / "attachments"
    download_dir.mkdir(exist_ok=True)
    openai_client = OpenAI()

    # Lazy-init QuickBooks (only needed for invoices)
    qb_service = None
    customers_context = ""

    def get_qb_service():
        nonlocal qb_service, customers_context
        if qb_service is None:
            qb_service = QuickbooksInvoiceService()
            print("Loading customer addresses for AI matching...")
            customers_context = qb_service.get_customers_context()
        return qb_service

    messages = list(fetch_messages_with_attachments(max_results=10))

    # Process each message
    for idx, (message_id, subject, message_text, attachments) in enumerate(messages, start=1):
        if is_processed(message_id):
            print(f"[{idx}/{len(messages)}] {message_id}: already processed, skipping")
            continue

        draft = None
        label = invoice_label(message_text, attachments, client=openai_client)
        print(f"[{idx}/{len(messages)}] {message_id}: subject -> {subject} label -> {label}")

        # Apply the label to the email in Outlook
        try:
            label_message(message_id, label)
            print(f"[{idx}/{len(messages)}] {message_id}: Outlook category set to '{label}'")
        except Exception as e:
            print(f"[{idx}/{len(messages)}] {message_id}: Failed to set Outlook category: {e}")

        project_root = Path(__file__).parent.parent
        attachments_dir = project_root / "attachments"

        # Get the actual attachment file for this email
        latest_file = None
        if attachments:
            attachment_filename = attachments[0][0]
            latest_file = str(attachments_dir / attachment_filename)



        if label == "shipping":
            print(f"[{idx}/{len(messages)}] {message_id}: parsing shipping data...")
            shipping_data = parse_shipping(message_text, attachments, client=openai_client)
            if shipping_data:
                print(f"  Carrier: {shipping_data.carrier}")
                print(f"  Tracking: {shipping_data.tracking_number}")
                print(f"  Status: {shipping_data.delivery_status}")
                print(f"  Destination: {shipping_data.destination_address}")
                if shipping_data.items:
                    for item in shipping_data.items:
                        print(f"  Item: {item.description} (qty: {item.quantity})")
                try:
                    notion_page = push_shipping_to_notion(shipping_data, subject)
                    print(f"[{idx}/{len(messages)}] {message_id}: pushed to Notion Shipping Tracker")
                except Exception as e:
                    print(f"[{idx}/{len(messages)}] {message_id}: failed to push to Notion: {e}")
            else:
                print(f"[{idx}/{len(messages)}] {message_id}: could not extract shipping data")
            mark_processed(message_id)
            continue

        if label == "client_communications":
            print(f"[{idx}/{len(messages)}] {message_id}: parsing client communication...")
            client_data = parse_client_communication(message_text, attachments, client=openai_client)
            if client_data:
                print(f"  Client: {client_data.client_name}")
                print(f"  Project: {client_data.project_name}")
                print(f"  Summary: {client_data.summary}")
                print(f"  Urgency: {client_data.urgency}")
                print(f"  Response needed: {client_data.response_needed}")
                if client_data.action_items:
                    print(f"  Action items:")
                    for action in client_data.action_items:
                        print(f"    * {action}")
                if client_data.key_dates:
                    print(f"  Key dates:")
                    for date in client_data.key_dates:
                        print(f"    * {date}")
                try:
                    notion_page = push_client_comm_to_notion(client_data, subject)
                    print(f"[{idx}/{len(messages)}] {message_id}: pushed to Notion Client Communications")
                except Exception as e:
                    print(f"[{idx}/{len(messages)}] {message_id}: failed to push to Notion: {e}")
            else:
                print(f"[{idx}/{len(messages)}] {message_id}: could not extract client data")
            mark_processed(message_id)
            continue

        if label == "insurance":
            print(f"[{idx}/{len(messages)}] {message_id}: classified as 'insurance' - logged for review")
            mark_processed(message_id)
            continue

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

            # Route to correct QuickBooks transaction type
            qb = get_qb_service()
            if hasattr(draft, 'is_receipt') and draft.is_receipt:
                # Receipt (already paid) → Create Purchase
                print(f"[{idx}/{len(messages)}] {message_id}: RECEIPT detected - creating Purchase (already paid)")
                transaction = qb.push_receipt(draft)
            else:
                # Invoice (unpaid) → Create Bill
                transaction = qb.push_invoice(draft)

            # Attach the file
            if latest_file:
                print(f"Attaching file: {latest_file}")
                attach = qb.add_attachment(latest_file, transaction)

            transaction_id = getattr(transaction, "Id", None)
            if transaction_id:
                print(f"[{idx}/{len(messages)}] {message_id}: QuickBooks transaction created (Id={transaction_id})")
            else:
                print(f"[{idx}/{len(messages)}] {message_id}: QuickBooks transaction created")

            # Push to Notion Invoice Tracking
            try:
                notion_page = push_invoice_to_notion(draft, subject)
                print(f"[{idx}/{len(messages)}] {message_id}: pushed to Notion Invoice Tracking")
            except Exception as e:
                print(f"[{idx}/{len(messages)}] {message_id}: failed to push to Notion: {e}")
        else:
            print(f"[{idx}/{len(messages)}] {message_id}: no valid invoice data found")

        mark_processed(message_id)


if __name__ == "__main__":
    main()
