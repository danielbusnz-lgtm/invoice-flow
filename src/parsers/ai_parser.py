from typing import Optional
from openai import OpenAI, OpenAIError, AuthenticationError    
from models.invoice import InvoiceData, InvoiceDraft, InvoiceLine, LabelSort, ShippingData, ClientData
import logging

logger = logging.getLogger(__name__) 

def invoice_label(message_text: str, attachments: list, client: Optional[OpenAI] = None):
    """Classify email as invoice or not using OpenAI"""
    if client is None:
        try:
            client = OpenAI()
        except OpenAIError as e:
            logger.error("OpenAI auth failed: %s", e)
            return None
    
    context = message_text

    if attachments:
        context += "\n\nAttachments found:\n"
        for filename, data in attachments:
            context += f"- {filename}\n"

    try:
        response = client.responses.parse(
            model="gpt-4o-2024-08-06",
            input=[
                {"role": "system", "content": (
                    "Classify the following email into one of these categories:\n"
                    "- invoice: Bills, receipts, payment requests, invoices with attached documents requesting or confirming payment.\n"
                    "- shipping: Delivery confirmations, tracking numbers, shipment notifications, freight or courier updates.\n"
                    "- insurance: Insurance policies, claims, certificates of insurance, coverage documents, liability or workers comp.\n"
                    "- client_communications: General client emails, project updates, questions, scheduling, meeting requests, status reports.\n"
                    "- none: Spam, newsletters, promotions, or anything that does not fit the above categories.\n\n"
                    "Return only the label."
                )},
                {
                    "role": "user",
                    "content": context,
                },
            ],
            text_format=LabelSort,
        )
    except AuthenticationError as e: 
        logger.error("OpenAI auth failed: %s", e)
        return None
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


def parse_shipping(message_text: str, attachments: list, client: Optional[OpenAI] = None) -> Optional[ShippingData]:
    """Extract structured shipping data from an email and its attachments"""
    if client is None:
        try:
            client = OpenAI()
        except OpenAIError as e:
            logger.error("OpenAI auth failed: %s", e)
            return None

    context = message_text

    if attachments:
        context += "\n\nAttachment contents:\n"
        for filename, data in attachments:
            if isinstance(data, str):
                context += f"\n--- {filename} ---\n{data}\n"
            else:
                context += f"\n--- {filename} (binary file) ---\n"

    system_prompt = (
        "Extract structured shipping and delivery data from this email.\n"
        "Look for:\n"
        "- Carrier name (FedEx, UPS, USPS, freight company, etc.)\n"
        "- Tracking number(s)\n"
        "- Order or reference number\n"
        "- Shipment date and estimated delivery date (format: MM/DD/YYYY)\n"
        "- Delivery status (shipped, in transit, delivered, etc.)\n"
        "- Origin and destination addresses\n"
        "- Items being shipped with quantities and weights\n"
        "- Vendor or sender name\n"
        "- Any additional notes\n\n"
        "REQUIRED: At least one of tracking_number, order_number, or carrier.\n"
        "OPTIONAL: All other fields. Return all dates in MM/DD/YYYY format."
    )

    try:
        response = client.responses.parse(
            model="gpt-4o-2024-08-06",
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context},
            ],
            text_format=ShippingData,
        )
    except AuthenticationError as e:
        logger.error("OpenAI auth failed: %s", e)
        return None

    return response.output_parsed


def parse_client_communication(message_text: str, attachments: list, client: Optional[OpenAI] = None) -> Optional[ClientData]:
    """Extract structured data from a client communication email"""
    if client is None:
        try:
            client = OpenAI()
        except OpenAIError as e:
            logger.error("OpenAI auth failed: %s", e)
            return None

    context = message_text

    if attachments:
        context += "\n\nAttachment contents:\n"
        for filename, data in attachments:
            if isinstance(data, str):
                context += f"\n--- {filename} ---\n{data}\n"
            else:
                context += f"\n--- {filename} (binary file) ---\n"

    system_prompt = (
        "Extract structured data from this client communication email.\n"
        "Look for:\n"
        "- Client name (who sent or is referenced in the email)\n"
        "- Subject or main topic of the email\n"
        "- Project name or reference if mentioned\n"
        "- A brief summary of the email content (2-3 sentences)\n"
        "- Action items: specific tasks or requests that need to be done\n"
        "- Key dates: any dates or deadlines mentioned (format: MM/DD/YYYY - description)\n"
        "- Whether a response is needed (true/false)\n"
        "- Urgency level: low (general info), medium (needs attention soon), high (urgent/time-sensitive)\n"
        "- Any additional notes\n\n"
        "REQUIRED: summary.\n"
        "OPTIONAL: All other fields. Return all dates in MM/DD/YYYY format."
    )

    try:
        response = client.responses.parse(
            model="gpt-4o-2024-08-06",
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context},
            ],
            text_format=ClientData,
        )
    except AuthenticationError as e:
        logger.error("OpenAI auth failed: %s", e)
        return None

    return response.output_parsed
