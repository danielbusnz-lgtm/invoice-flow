from typing import Optional
from openai import OpenAI
from models.invoice import InvoiceData, InvoiceDraft, InvoiceLine, LabelSort


def invoice_label(message_text: str, attachments: list, client: Optional[OpenAI] = None):
    """Classify email as invoice or not using OpenAI"""
    if client is None:
        client = OpenAI()

    context = message_text

    if attachments:
        context += "\n\nAttachments found:\n"
        for filename, data in attachments:
            context += f"- {filename}\n"

    response = client.responses.parse(
        model="gpt-4o-2024-08-06",
        input=[
            {"role": "system", "content": "Extract wheter or not the following email is an invoice or not. If there is an attachment, it is likely an invoice. If it is an email return: invoice and if not return: none."},
            {
                "role": "user",
                "content": context,
            },
        ],
        text_format=LabelSort,
    )

    return response.output_parsed.label


def pdf_invoice(message_text: str, text, client: Optional[OpenAI] = None, customers_context: Optional[str] = None):
    """Extract invoice data from PDF text"""
    if client is None:
        client = OpenAI()

    system_prompt = (
        "Extract structured invoice data from this document. "
        "IMPORTANT: Determine if this is an INVOICE (requesting payment, unpaid) or RECEIPT (already paid, shows 'PAID', 'SOLD ON', etc.). "
        "Set is_receipt=true if it's a receipt/already paid. "
        "Look for any job site address, project address, or service location - extract as job_site_address. "
        "For each line item, categorize it (e.g., Materials, Labor, Equipment, Fuel, Permits, Supplies, etc.) based on the item description. "
        "REQUIRED: vendor_display_name, line_items (with item, rate, quantity, category), total_amount, is_receipt. "
        "OPTIONAL: invoice_number, invoice_date (format: MM/DD/YYYY), due_date (format: MM/DD/YYYY), tax, memo, job_site_address, customer_name. "
        "Return all dates in MM/DD/YYYY format."
    )

    if customers_context:
        system_prompt += (
            f"\n\nIMPORTANT - Match the job site address on the invoice to one of these customers:\n{customers_context}\n\n"
            "If you find a matching address, set customer_name to the exact customer name from the list above."
        )

    response = client.responses.parse(
        model="gpt-5",
        input=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": text,
            },
        ],
        text_format=InvoiceData,
    )

    payload = response.output_parsed

    line_items = [
        InvoiceLine(
            item=item.item,
            rate=item.rate,
            quantity=item.quantity,
            description=item.description,
            category=item.category,
        )
        for item in payload.line_items
    ]

    return InvoiceDraft(
        vendor_display_name=payload.vendor_display_name,
        memo=payload.memo,
        line_items=line_items,
        tax=payload.tax,
        total_amount=payload.total_amount,
        due_date=payload.due_date,
        invoice_number=payload.invoice_number,
        invoice_date=payload.invoice_date,
        job_site_address=payload.job_site_address,
        customer_name=payload.customer_name,
    )


def ai_invoice(message_text: str, file_path: str, client: Optional[OpenAI] = None, customers_context: Optional[str] = None) -> Optional[InvoiceDraft]:
    """Extract invoice data from image using OpenAI vision API"""
    if client is None:
        client = OpenAI()

    def create_file(file_path):
        with open(file_path, "rb") as file_content:
            result = client.files.create(
                file=file_content,
                purpose="vision",
            )
        return result.id

    file_id = create_file(file_path)

    prompt_text = (
        "Extract structured invoice data from this image. "
        "IMPORTANT: Determine if this is an INVOICE (requesting payment) or RECEIPT (already paid, shows 'PAID', 'SOLD ON', etc.). "
        "Set is_receipt=true if it's a receipt. "
        "Look for any job site address, project address, or service location - extract as job_site_address. "
        "For each line item, categorize it (e.g., Materials, Labor, Equipment, Fuel, Permits, Supplies, etc.). "
        "REQUIRED: vendor_display_name, line_items (with item, rate, quantity, category), total_amount, is_receipt. "
        "OPTIONAL: invoice_number, invoice_date, due_date, tax, memo, job_site_address, customer_name. "
        "Return all dates in MM/DD/YYYY format."
    )

    if customers_context:
        prompt_text += (
            f"\n\nIMPORTANT - Match the job site address on the invoice to one of these customers:\n{customers_context}\n\n"
            "If you find a matching address, set customer_name to the exact customer name from the list above."
        )

    response = client.responses.parse(
        model="gpt-5",
        input=[{
            "role": "user",
            "content": [
                {
                    "type": "input_text", "text": prompt_text},
                {
                    "type": "input_image",
                    "file_id": file_id,

                },
            ],
        }],
        text_format=InvoiceData,
    )
    payload = response.output_parsed

    print(payload)

    line_items = [
        InvoiceLine(
            item=item.item,
            rate=item.rate,
            quantity=item.quantity,
            description=item.description,
            category=item.category,
        )
        for item in payload.line_items
    ]
    return InvoiceDraft(
        vendor_display_name=payload.vendor_display_name,
        memo=payload.memo,
        line_items=line_items,
        tax=payload.tax,
        total_amount=payload.total_amount,
        due_date=payload.due_date,
        invoice_number=payload.invoice_number,
        invoice_date=payload.invoice_date,
        job_site_address=payload.job_site_address,
        customer_name=payload.customer_name,
    )
