import os
import requests
from typing import Optional
from dotenv import load_dotenv
from datetime import datetime

from models.invoice import InvoiceDraft, ShippingData, ClientData

load_dotenv()

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_VERSION = "2022-06-28"
NOTION_BASE_URL = "https://api.notion.com/v1"

# Database IDs from Notion
INVOICE_DB_ID = os.getenv("NOTION_INVOICE_DB_ID", "8bed64ad-5521-4dc7-a9f5-1cae5e2ea45c")
SHIPPING_DB_ID = os.getenv("NOTION_SHIPPING_DB_ID", "b0f6ea56-f5e5-47d1-8a16-a59929037f40")
CLIENT_COMMS_DB_ID = os.getenv("NOTION_CLIENT_DB_ID", "1daac1cd-036b-4025-82f1-b92e0037f09f")

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": NOTION_VERSION,
}


def _parse_date(date_str: Optional[str]) -> Optional[str]:
    """Convert MM/DD/YYYY date string to ISO-8601 format for Notion."""
    if not date_str:
        return None
    try:
        parsed = datetime.strptime(date_str, "%m/%d/%Y")
        return parsed.strftime("%Y-%m-%d")
    except ValueError:
        return date_str


def _build_rich_text(text: Optional[str]) -> list:
    """Build a Notion rich_text property value."""
    if not text:
        return []
    return [{"text": {"content": text[:2000]}}]


def _build_title(text: str) -> list:
    """Build a Notion title property value."""
    return [{"text": {"content": text[:2000]}}]


def _build_date(date_str: Optional[str]) -> Optional[dict]:
    """Build a Notion date property value."""
    iso_date = _parse_date(date_str)
    if not iso_date:
        return None
    return {"start": iso_date}


def _build_select(value: Optional[str]) -> Optional[dict]:
    """Build a Notion select property value."""
    if not value:
        return None
    return {"name": value}


def _build_number(value: Optional[float]) -> Optional[float]:
    """Return number or None."""
    return value


def _build_checkbox(value: Optional[bool]) -> bool:
    """Return checkbox value."""
    return bool(value)


def _create_page(database_id: str, properties: dict) -> dict:
    """Create a page in a Notion database."""
    payload = {
        "parent": {"database_id": database_id},
        "properties": properties,
    }

    response = requests.post(
        f"{NOTION_BASE_URL}/pages",
        headers=HEADERS,
        json=payload,
    )

    if response.status_code != 200:
        raise Exception(
            f"Failed to create Notion page: {response.status_code} {response.text}"
        )

    return response.json()


def push_invoice_to_notion(draft: InvoiceDraft, subject: str = "") -> dict:
    """Push an invoice draft to the Invoice Tracking database."""
    properties = {
        "Vendor": {"title": _build_title(draft.vendor_display_name)},
        "Invoice Number": {"rich_text": _build_rich_text(draft.invoice_number)},
        "Email Subject": {"rich_text": _build_rich_text(subject)},
        "Memo": {"rich_text": _build_rich_text(draft.memo)},
        "Job Site Address": {"rich_text": _build_rich_text(draft.job_site_address)},
        "Customer": {"rich_text": _build_rich_text(draft.customer_name)},
        "Status": {"select": _build_select("Pending")},
        "Is Receipt": {"checkbox": _build_checkbox(draft.is_receipt)},
    }

    if draft.total_amount is not None:
        properties["Total Amount"] = {"number": draft.total_amount}

    if draft.tax is not None:
        properties["Tax"] = {"number": draft.tax}

    if draft.invoice_date:
        date_val = _build_date(draft.invoice_date)
        if date_val:
            properties["Invoice Date"] = {"date": date_val}

    if draft.due_date:
        date_val = _build_date(draft.due_date)
        if date_val:
            properties["Due Date"] = {"date": date_val}

    return _create_page(INVOICE_DB_ID, properties)


def push_shipping_to_notion(data: ShippingData, subject: str = "") -> dict:
    """Push shipping data to the Shipping Tracker database."""
    # Build title from carrier + tracking or order number
    title_parts = []
    if data.carrier:
        title_parts.append(data.carrier)
    if data.tracking_number:
        title_parts.append(data.tracking_number)
    elif data.order_number:
        title_parts.append(data.order_number)
    shipment_title = " - ".join(title_parts) if title_parts else "Shipment"

    # Map delivery status to select options
    status_map = {
        "shipped": "Shipped",
        "in transit": "In Transit",
        "delivered": "Delivered",
    }
    status = status_map.get(
        (data.delivery_status or "").lower(), "Unknown"
    )

    # Map carrier to select options
    carrier_map = {
        "fedex": "FedEx",
        "ups": "UPS",
        "usps": "USPS",
        "freight": "Freight",
    }
    carrier = carrier_map.get(
        (data.carrier or "").lower(), "Other"
    ) if data.carrier else None

    # Format items as text
    items_text = ""
    if data.items:
        item_lines = []
        for item in data.items:
            line = item.description
            if item.quantity:
                line += f" (qty: {item.quantity})"
            if item.weight:
                line += f" [{item.weight}]"
            item_lines.append(line)
        items_text = "\n".join(item_lines)

    properties = {
        "Shipment": {"title": _build_title(shipment_title)},
        "Tracking Number": {"rich_text": _build_rich_text(data.tracking_number)},
        "Order Number": {"rich_text": _build_rich_text(data.order_number)},
        "Origin": {"rich_text": _build_rich_text(data.origin_address)},
        "Destination": {"rich_text": _build_rich_text(data.destination_address)},
        "Vendor": {"rich_text": _build_rich_text(data.vendor_name)},
        "Items": {"rich_text": _build_rich_text(items_text)},
        "Notes": {"rich_text": _build_rich_text(data.notes)},
        "Email Subject": {"rich_text": _build_rich_text(subject)},
        "Status": {"select": _build_select(status)},
    }

    if carrier:
        properties["Carrier"] = {"select": _build_select(carrier)}

    if data.shipment_date:
        date_val = _build_date(data.shipment_date)
        if date_val:
            properties["Shipment Date"] = {"date": date_val}

    if data.estimated_delivery:
        date_val = _build_date(data.estimated_delivery)
        if date_val:
            properties["Estimated Delivery"] = {"date": date_val}

    return _create_page(SHIPPING_DB_ID, properties)


def push_client_comm_to_notion(data: ClientData, subject: str = "") -> dict:
    """Push client communication data to the Client Communications database."""
    # Use the parsed subject or fall back to email subject
    title = data.subject or subject or "Client Communication"

    # Map urgency to select options
    urgency_map = {
        "low": "Low",
        "medium": "Medium",
        "high": "High",
    }
    urgency = urgency_map.get(
        (data.urgency or "").lower()
    )

    # Format action items as text
    action_text = ""
    if data.action_items:
        action_text = "\n".join(f"* {item}" for item in data.action_items)

    # Format key dates as text
    dates_text = ""
    if data.key_dates:
        dates_text = "\n".join(f"* {date}" for date in data.key_dates)

    properties = {
        "Subject": {"title": _build_title(title)},
        "Client Name": {"rich_text": _build_rich_text(data.client_name)},
        "Project": {"rich_text": _build_rich_text(data.project_name)},
        "Summary": {"rich_text": _build_rich_text(data.summary)},
        "Action Items": {"rich_text": _build_rich_text(action_text)},
        "Key Dates": {"rich_text": _build_rich_text(dates_text)},
        "Notes": {"rich_text": _build_rich_text(data.notes)},
        "Email Subject": {"rich_text": _build_rich_text(subject)},
        "Response Needed": {"checkbox": _build_checkbox(data.response_needed)},
    }

    if urgency:
        properties["Urgency"] = {"select": _build_select(urgency)}

    return _create_page(CLIENT_COMMS_DB_ID, properties)
