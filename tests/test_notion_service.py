"""Test suite for Notion service - pushing parsed data to Notion databases"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from services.notion_service import (
    push_invoice_to_notion,
    push_shipping_to_notion,
    push_client_comm_to_notion,
    query_invoice_by_number,
    _parse_date,
    _build_rich_text,
    _build_title,
    _build_date,
    _build_select,
    _build_checkbox,
    _build_email_link,
    _build_tracking_link,
    _build_file_property,
    INVOICE_DB_ID,
    SHIPPING_DB_ID,
    CLIENT_COMMS_DB_ID,
)
from models.invoice import InvoiceDraft, InvoiceLine, ShippingData, ShippingItem, ClientData


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------

class TestHelperFunctions:

    def test_parse_date_mm_dd_yyyy(self):
        assert _parse_date("03/15/2026") == "2026-03-15"
        print("MM/DD/YYYY date parsed correctly")

    def test_parse_date_none(self):
        assert _parse_date(None) is None
        print("None date returns None")

    def test_parse_date_empty(self):
        assert _parse_date("") is None
        print("Empty date returns None")

    def test_parse_date_already_iso(self):
        result = _parse_date("2026-03-15")
        assert result is not None
        print("ISO date passed through")

    def test_build_rich_text(self):
        result = _build_rich_text("Hello world")
        assert len(result) == 1
        assert result[0]["text"]["content"] == "Hello world"
        print("Rich text built correctly")

    def test_build_rich_text_none(self):
        result = _build_rich_text(None)
        assert result == []
        print("None rich text returns empty list")

    def test_build_rich_text_truncates(self):
        long_text = "x" * 3000
        result = _build_rich_text(long_text)
        assert len(result[0]["text"]["content"]) == 2000
        print("Rich text truncated to 2000 chars")

    def test_build_title(self):
        result = _build_title("My Title")
        assert result[0]["text"]["content"] == "My Title"
        print("Title built correctly")

    def test_build_date(self):
        result = _build_date("03/15/2026")
        assert result == {"start": "2026-03-15"}
        print("Date built correctly")

    def test_build_date_none(self):
        result = _build_date(None)
        assert result is None
        print("None date returns None")

    def test_build_select(self):
        result = _build_select("Pending")
        assert result == {"name": "Pending"}
        print("Select built correctly")

    def test_build_select_none(self):
        result = _build_select(None)
        assert result is None
        print("None select returns None")

    def test_build_checkbox_true(self):
        assert _build_checkbox(True) is True
        print("Checkbox true")

    def test_build_checkbox_false(self):
        assert _build_checkbox(False) is False
        print("Checkbox false")

    def test_build_checkbox_none(self):
        assert _build_checkbox(None) is False
        print("Checkbox None becomes False")

    def test_build_email_link(self):
        result = _build_email_link("msg-abc-123")
        assert result == "https://outlook.office365.com/mail/id/msg-abc-123"
        print("Email link built correctly")

    def test_build_email_link_none(self):
        assert _build_email_link(None) is None
        print("None message_id returns None")

    def test_build_tracking_link_fedex(self):
        result = _build_tracking_link("FedEx", "794644790138")
        assert result == "https://www.trackingmore.com/track?number=794644790138&express=fedex"
        print("FedEx tracking link built correctly")

    def test_build_tracking_link_ups(self):
        result = _build_tracking_link("UPS", "1Z999AA10123456784")
        assert result == "https://www.trackingmore.com/track?number=1Z999AA10123456784&express=ups"
        print("UPS tracking link built correctly")

    def test_build_tracking_link_usps(self):
        result = _build_tracking_link("USPS", "9400111899223")
        assert result == "https://www.trackingmore.com/track?number=9400111899223&express=usps"
        print("USPS tracking link built correctly")

    def test_build_tracking_link_unknown_carrier(self):
        result = _build_tracking_link("DHL", "123456")
        assert result is None
        print("Unknown carrier returns None")

    def test_build_tracking_link_none_carrier(self):
        assert _build_tracking_link(None, "123") is None
        print("None carrier returns None")

    def test_build_tracking_link_none_tracking(self):
        assert _build_tracking_link("FedEx", None) is None
        print("None tracking number returns None")

    def test_build_file_property(self):
        result = _build_file_property("invoice.pdf", "http://example.com/invoice.pdf")
        assert len(result) == 1
        assert result[0]["name"] == "invoice.pdf"
        assert result[0]["type"] == "external"
        assert result[0]["external"]["url"] == "http://example.com/invoice.pdf"
        print("File property built correctly")

    def test_build_file_property_empty_url(self):
        result = _build_file_property("invoice.pdf", "")
        assert result == []
        print("Empty file URL returns empty list")


# ---------------------------------------------------------------------------
# Invoice dedup tests
# ---------------------------------------------------------------------------

class TestQueryInvoice:

    @patch("services.notion_service.requests.post")
    def test_query_finds_duplicate(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"results": [{"id": "existing-page"}]}
        mock_post.return_value = mock_resp

        assert query_invoice_by_number("INV-1234") is True
        print("Duplicate invoice detected")

    @patch("services.notion_service.requests.post")
    def test_query_no_duplicate(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"results": []}
        mock_post.return_value = mock_resp

        assert query_invoice_by_number("INV-9999") is False
        print("No duplicate found")

    def test_query_empty_number(self):
        assert query_invoice_by_number("") is False
        assert query_invoice_by_number(None) is False
        print("Empty invoice number returns False")

    @patch("services.notion_service.requests.post")
    def test_query_api_error_returns_false(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_post.return_value = mock_resp

        assert query_invoice_by_number("INV-1234") is False
        print("API error returns False (safe to proceed)")


# ---------------------------------------------------------------------------
# Invoice push tests
# ---------------------------------------------------------------------------

class TestPushInvoice:

    def _sample_draft(self):
        return InvoiceDraft(
            vendor_display_name="Acme Supplies",
            invoice_number="INV-1234",
            invoice_date="03/01/2026",
            due_date="03/31/2026",
            total_amount=1500.00,
            tax=75.00,
            line_items=[
                InvoiceLine(item="Lumber", rate=500.00, quantity=2.0, category="Materials"),
                InvoiceLine(item="Labor", rate=50.00, quantity=10.0, category="Labor"),
            ],
            is_receipt=False,
            job_site_address="123 Main St, Portland, OR",
            customer_name="Smith Residence",
            memo="March delivery",
        )

    @patch("services.notion_service.requests.post")
    def test_push_invoice_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "page-123", "url": "https://notion.so/page-123"}
        mock_post.return_value = mock_resp

        result = push_invoice_to_notion(self._sample_draft(), "Invoice from Acme", "msg-inv-001")

        assert result["id"] == "page-123"
        call_json = mock_post.call_args.kwargs["json"]
        assert call_json["parent"]["database_id"] == INVOICE_DB_ID
        props = call_json["properties"]
        assert props["Name"]["title"][0]["text"]["content"] == "Acme Supplies"
        assert props["Vendor"]["rich_text"][0]["text"]["content"] == "Acme Supplies"
        assert props["PO Number"]["rich_text"][0]["text"]["content"] == "INV-1234"
        assert props["Amount"]["number"] == 1500.00
        assert props["Status"]["select"]["name"] == "Received"
        assert props["Notes"]["rich_text"][0]["text"]["content"] == "March delivery"
        assert props["Email Link"]["url"] == "https://outlook.office365.com/mail/id/msg-inv-001"
        print("Invoice pushed to Notion correctly")

    @patch("services.notion_service.requests.post")
    def test_push_invoice_with_dates(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "page-456"}
        mock_post.return_value = mock_resp

        push_invoice_to_notion(self._sample_draft())

        props = mock_post.call_args.kwargs["json"]["properties"]
        assert props["Date"]["date"]["start"] == "2026-03-01"
        assert props["Due Date"]["date"]["start"] == "2026-03-31"
        print("Invoice dates formatted correctly")

    @patch("services.notion_service.requests.post")
    def test_push_invoice_minimal(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "page-789"}
        mock_post.return_value = mock_resp

        draft = InvoiceDraft(
            vendor_display_name="Test Vendor",
            line_items=[],
        )
        push_invoice_to_notion(draft)

        props = mock_post.call_args.kwargs["json"]["properties"]
        assert props["Name"]["title"][0]["text"]["content"] == "Test Vendor"
        assert "Amount" not in props
        assert "Date" not in props
        assert "Email Link" not in props
        print("Minimal invoice pushed correctly")

    @patch("services.notion_service.requests.post")
    def test_push_invoice_with_file(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "page-file"}
        mock_post.return_value = mock_resp

        push_invoice_to_notion(
            self._sample_draft(), "Test", "msg-1",
            file_url="http://45.55.121.238/attachments/invoice.pdf",
        )

        props = mock_post.call_args.kwargs["json"]["properties"]
        files = props["Invoice File"]["files"]
        assert len(files) == 1
        assert files[0]["name"] == "invoice.pdf"
        assert files[0]["external"]["url"] == "http://45.55.121.238/attachments/invoice.pdf"
        print("Invoice file property set correctly")

    @patch("services.notion_service.requests.post")
    def test_push_invoice_no_file(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "page-nofile"}
        mock_post.return_value = mock_resp

        push_invoice_to_notion(self._sample_draft())

        props = mock_post.call_args.kwargs["json"]["properties"]
        assert "Invoice File" not in props
        print("No file URL means no Invoice File property")

    @patch("services.notion_service.requests.post")
    def test_push_invoice_api_error(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.text = "Bad Request"
        mock_post.return_value = mock_resp

        with pytest.raises(Exception, match="Failed to create Notion page"):
            push_invoice_to_notion(self._sample_draft())
        print("Invoice API error handled correctly")


# ---------------------------------------------------------------------------
# Shipping push tests
# ---------------------------------------------------------------------------

class TestPushShipping:

    def _sample_shipping(self):
        return ShippingData(
            carrier="FedEx",
            tracking_number="794644790138",
            order_number="ORD-5678",
            shipment_date="03/01/2026",
            estimated_delivery="03/04/2026",
            delivery_status="in transit",
            origin_address="123 Warehouse St, Portland, OR",
            destination_address="456 Job Site Rd, Seattle, WA",
            items=[
                ShippingItem(description="Lumber 2x4", quantity=50, weight="200 lbs"),
            ],
            vendor_name="Home Depot",
            notes="Leave at loading dock",
        )

    @patch("services.notion_service.requests.post")
    def test_push_shipping_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "ship-123"}
        mock_post.return_value = mock_resp

        result = push_shipping_to_notion(self._sample_shipping(), "FedEx Shipment", "msg-ship-001")

        assert result["id"] == "ship-123"
        props = mock_post.call_args.kwargs["json"]["properties"]
        assert "FedEx" in props["Name"]["title"][0]["text"]["content"]
        assert props["Tracking Number"]["rich_text"][0]["text"]["content"] == "794644790138"
        assert props["Carrier"]["select"]["name"] == "FedEx"
        assert props["Status"]["select"]["name"] == "In Transit"
        assert props["Vendor"]["rich_text"][0]["text"]["content"] == "Home Depot"
        assert props["Latest Event"]["rich_text"][0]["text"]["content"] == "in transit"
        assert props["Tracking Link"]["url"] == "https://www.trackingmore.com/track?number=794644790138&express=fedex"
        assert props["Email Link"]["url"] == "https://outlook.office365.com/mail/id/msg-ship-001"
        print("Shipping pushed to Notion correctly")

    @patch("services.notion_service.requests.post")
    def test_push_shipping_dates(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "ship-456"}
        mock_post.return_value = mock_resp

        push_shipping_to_notion(self._sample_shipping())

        props = mock_post.call_args.kwargs["json"]["properties"]
        assert props["Date"]["date"]["start"] == "2026-03-01"
        assert props["Expected Delivery"]["date"]["start"] == "2026-03-04"
        print("Shipping dates formatted correctly")

    @patch("services.notion_service.requests.post")
    def test_push_shipping_order_number(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "ship-789"}
        mock_post.return_value = mock_resp

        push_shipping_to_notion(self._sample_shipping())

        props = mock_post.call_args.kwargs["json"]["properties"]
        assert props["Order Number"]["rich_text"][0]["text"]["content"] == "ORD-5678"
        print("Order number pushed correctly")

    @patch("services.notion_service.requests.post")
    def test_push_shipping_delivered_status(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "ship-abc"}
        mock_post.return_value = mock_resp

        data = ShippingData(carrier="UPS", delivery_status="delivered")
        push_shipping_to_notion(data)

        props = mock_post.call_args.kwargs["json"]["properties"]
        assert props["Status"]["select"]["name"] == "Delivered"
        print("Delivered status mapped correctly")

    @patch("services.notion_service.requests.post")
    def test_push_shipping_unknown_carrier(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "ship-def"}
        mock_post.return_value = mock_resp

        data = ShippingData(carrier="DHL Express", tracking_number="123")
        push_shipping_to_notion(data)

        props = mock_post.call_args.kwargs["json"]["properties"]
        assert props["Carrier"]["select"]["name"] == "Other"
        print("Unknown carrier mapped to Other")

    @patch("services.notion_service.requests.post")
    def test_push_shipping_api_error(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"
        mock_post.return_value = mock_resp

        with pytest.raises(Exception, match="Failed to create Notion page"):
            push_shipping_to_notion(self._sample_shipping())
        print("Shipping API error handled correctly")


# ---------------------------------------------------------------------------
# Client communication push tests
# ---------------------------------------------------------------------------

class TestPushClientComm:

    def _sample_client(self):
        return ClientData(
            client_name="John Smith",
            subject="Kitchen remodel update",
            project_name="Smith Residence",
            summary="Client wants an update on cabinet installation timeline.",
            action_items=["Send updated schedule", "Order backsplash tile"],
            key_dates=["03/10/2026 - Cabinet delivery", "03/15/2026 - Install starts"],
            response_needed=True,
            urgency="high",
            notes="Client prefers email",
        )

    @patch("services.notion_service.requests.post")
    def test_push_client_comm_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "client-123"}
        mock_post.return_value = mock_resp

        result = push_client_comm_to_notion(self._sample_client(), "Re: Kitchen remodel", "msg-client-001")

        assert result["id"] == "client-123"
        props = mock_post.call_args.kwargs["json"]["properties"]
        assert props["Subject"]["title"][0]["text"]["content"] == "Kitchen remodel update"
        assert props["Client Name"]["rich_text"][0]["text"]["content"] == "John Smith"
        assert props["Project"]["rich_text"][0]["text"]["content"] == "Smith Residence"
        assert props["Urgency"]["select"]["name"] == "High"
        assert props["Response Needed"]["checkbox"] is True
        assert props["Email Link"]["url"] == "https://outlook.office365.com/mail/id/msg-client-001"
        print("Client communication pushed to Notion correctly")

    @patch("services.notion_service.requests.post")
    def test_push_client_action_items_formatted(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "client-456"}
        mock_post.return_value = mock_resp

        push_client_comm_to_notion(self._sample_client())

        props = mock_post.call_args.kwargs["json"]["properties"]
        action_text = props["Action Items"]["rich_text"][0]["text"]["content"]
        assert "Send updated schedule" in action_text
        assert "Order backsplash tile" in action_text
        print("Action items formatted correctly")

    @patch("services.notion_service.requests.post")
    def test_push_client_key_dates_formatted(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "client-789"}
        mock_post.return_value = mock_resp

        push_client_comm_to_notion(self._sample_client())

        props = mock_post.call_args.kwargs["json"]["properties"]
        dates_text = props["Key Dates"]["rich_text"][0]["text"]["content"]
        assert "Cabinet delivery" in dates_text
        assert "Install starts" in dates_text
        print("Key dates formatted correctly")

    @patch("services.notion_service.requests.post")
    def test_push_client_falls_back_to_email_subject(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "client-abc"}
        mock_post.return_value = mock_resp

        data = ClientData(summary="General update")
        push_client_comm_to_notion(data, "Email Subject Line")

        props = mock_post.call_args.kwargs["json"]["properties"]
        assert props["Subject"]["title"][0]["text"]["content"] == "Email Subject Line"
        print("Falls back to email subject when no parsed subject")

    @patch("services.notion_service.requests.post")
    def test_push_client_low_urgency(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "client-def"}
        mock_post.return_value = mock_resp

        data = ClientData(summary="Info only", urgency="low", response_needed=False)
        push_client_comm_to_notion(data)

        props = mock_post.call_args.kwargs["json"]["properties"]
        assert props["Urgency"]["select"]["name"] == "Low"
        assert props["Response Needed"]["checkbox"] is False
        print("Low urgency mapped correctly")

    @patch("services.notion_service.requests.post")
    def test_push_client_api_error(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_post.return_value = mock_resp

        with pytest.raises(Exception, match="Failed to create Notion page"):
            push_client_comm_to_notion(self._sample_client())
        print("Client API error handled correctly")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
