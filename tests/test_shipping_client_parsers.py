"""Test suite for shipping and client communication parsers"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from parsers.ai_parser import parse_shipping, parse_client_communication
from models.invoice import ShippingData, ShippingItem, ClientData


# ---------------------------------------------------------------------------
# Model validation tests
# ---------------------------------------------------------------------------

class TestShippingDataModel:
    """Test ShippingData Pydantic model validation"""

    def test_minimal_shipping_data(self):
        data = ShippingData(carrier="FedEx")
        assert data.carrier == "FedEx"
        assert data.items == []
        print("Minimal ShippingData accepted")

    def test_full_shipping_data(self):
        data = ShippingData(
            carrier="UPS",
            tracking_number="1Z999AA10123456784",
            order_number="ORD-5678",
            shipment_date="03/01/2026",
            estimated_delivery="03/05/2026",
            delivery_status="in transit",
            origin_address="123 Warehouse St, Portland, OR",
            destination_address="456 Job Site Rd, Seattle, WA",
            items=[
                ShippingItem(description="Lumber 2x4", quantity=50, weight="200 lbs"),
                ShippingItem(description="Nails box", quantity=5),
            ],
            vendor_name="Home Depot",
            notes="Leave at loading dock",
        )
        assert data.tracking_number == "1Z999AA10123456784"
        assert len(data.items) == 2
        assert data.items[0].description == "Lumber 2x4"
        print("Full ShippingData accepted")

    def test_shipping_item_minimal(self):
        item = ShippingItem(description="Concrete bags")
        assert item.quantity is None
        assert item.weight is None
        print("Minimal ShippingItem accepted")


class TestClientDataModel:
    """Test ClientData Pydantic model validation"""

    def test_minimal_client_data(self):
        data = ClientData(summary="Client asked about project timeline.")
        assert data.summary == "Client asked about project timeline."
        assert data.action_items == []
        assert data.key_dates == []
        assert data.response_needed is False
        print("Minimal ClientData accepted")

    def test_full_client_data(self):
        data = ClientData(
            client_name="John Smith",
            subject="Kitchen remodel update",
            project_name="Smith Residence",
            summary="Client wants an update on cabinet installation timeline.",
            action_items=["Send updated schedule", "Order backsplash tile"],
            key_dates=["03/10/2026 - Cabinet delivery", "03/15/2026 - Install starts"],
            response_needed=True,
            urgency="high",
            notes="Client prefers email over phone",
        )
        assert data.client_name == "John Smith"
        assert len(data.action_items) == 2
        assert len(data.key_dates) == 2
        assert data.urgency == "high"
        assert data.response_needed is True
        print("Full ClientData accepted")

    def test_urgency_values(self):
        for level in ("low", "medium", "high"):
            data = ClientData(summary="test", urgency=level)
            assert data.urgency == level
        print("All urgency levels accepted")

    def test_invalid_urgency_rejected(self):
        with pytest.raises(Exception):
            ClientData(summary="test", urgency="critical")
        print("Invalid urgency rejected")


# ---------------------------------------------------------------------------
# Shipping parser tests
# ---------------------------------------------------------------------------

class TestParseShipping:
    """Test the parse_shipping() function"""

    def _make_mock_client(self, shipping_data: ShippingData):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.output_parsed = shipping_data
        mock_client.responses.parse.return_value = mock_response
        return mock_client

    def test_parse_tracking_email(self):
        """Test parsing a typical shipping tracking email"""
        expected = ShippingData(
            carrier="FedEx",
            tracking_number="794644790138",
            shipment_date="03/01/2026",
            estimated_delivery="03/04/2026",
            delivery_status="shipped",
            destination_address="456 Main St, Portland, OR 97201",
        )
        client = self._make_mock_client(expected)

        result = parse_shipping(
            "Your FedEx shipment 794644790138 has shipped. Estimated delivery March 4.",
            [],
            client=client,
        )

        assert result.carrier == "FedEx"
        assert result.tracking_number == "794644790138"
        assert result.delivery_status == "shipped"
        print("Tracking email parsed correctly")

    def test_parse_delivery_confirmation(self):
        """Test parsing a delivery confirmation email"""
        expected = ShippingData(
            carrier="UPS",
            tracking_number="1Z999AA10123456784",
            delivery_status="delivered",
            destination_address="789 Job Site Ave, Seattle, WA",
        )
        client = self._make_mock_client(expected)

        result = parse_shipping(
            "Your UPS package has been delivered. Tracking: 1Z999AA10123456784",
            [],
            client=client,
        )

        assert result.delivery_status == "delivered"
        print("Delivery confirmation parsed correctly")

    def test_parse_freight_with_items(self):
        """Test parsing a freight shipment with line items"""
        expected = ShippingData(
            carrier="ABC Freight",
            order_number="BOL-78432",
            items=[
                ShippingItem(description="Lumber 2x4x8", quantity=100, weight="800 lbs"),
                ShippingItem(description="Plywood sheets", quantity=20, weight="600 lbs"),
            ],
            vendor_name="Lumber Supply Co",
            delivery_status="in transit",
        )
        client = self._make_mock_client(expected)

        result = parse_shipping(
            "Freight update: Your lumber order BOL-78432 is in transit.",
            [],
            client=client,
        )

        assert len(result.items) == 2
        assert result.items[0].description == "Lumber 2x4x8"
        assert result.items[0].quantity == 100
        assert result.vendor_name == "Lumber Supply Co"
        print("Freight with items parsed correctly")

    def test_parse_shipping_with_attachment(self):
        """Test that attachment content is included in context"""
        expected = ShippingData(carrier="USPS", tracking_number="9400111899223100")
        client = self._make_mock_client(expected)

        result = parse_shipping(
            "See attached shipping label.",
            [("shipping_label.pdf", "USPS tracking 9400111899223100")],
            client=client,
        )

        call_args = client.responses.parse.call_args
        user_content = call_args.kwargs["input"][1]["content"]
        assert "shipping_label.pdf" in user_content
        assert "USPS tracking 9400111899223100" in user_content
        print("Attachment content included in shipping context")

    def test_parse_shipping_with_binary_attachment(self):
        """Test that binary attachments are noted but not included as text"""
        expected = ShippingData(carrier="FedEx")
        client = self._make_mock_client(expected)

        parse_shipping(
            "Shipping label attached.",
            [("label.png", b"\x89PNG binary data")],
            client=client,
        )

        call_args = client.responses.parse.call_args
        user_content = call_args.kwargs["input"][1]["content"]
        assert "label.png (binary file)" in user_content
        print("Binary attachment handled correctly")

    def test_parse_shipping_prompt_content(self):
        """Test that the system prompt contains key extraction instructions"""
        expected = ShippingData(carrier="test")
        client = self._make_mock_client(expected)

        parse_shipping("test", [], client=client)

        call_args = client.responses.parse.call_args
        system_content = call_args.kwargs["input"][0]["content"]
        assert "Carrier" in system_content
        assert "Tracking" in system_content
        assert "delivery" in system_content.lower()
        assert call_args.kwargs["text_format"] == ShippingData
        print("Shipping prompt contains correct instructions")

    def test_parse_shipping_auth_failure_returns_none(self):
        """Test that auth failure returns None"""
        from openai import AuthenticationError
        client = MagicMock()
        client.responses.parse.side_effect = AuthenticationError(
            message="Invalid API key",
            response=MagicMock(status_code=401),
            body=None,
        )

        result = parse_shipping("test", [], client=client)
        assert result is None
        print("Auth failure returns None")


# ---------------------------------------------------------------------------
# Client communication parser tests
# ---------------------------------------------------------------------------

class TestParseClientCommunication:
    """Test the parse_client_communication() function"""

    def _make_mock_client(self, client_data: ClientData):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.output_parsed = client_data
        mock_client.responses.parse.return_value = mock_response
        return mock_client

    def test_parse_project_update(self):
        """Test parsing a project update email"""
        expected = ClientData(
            client_name="Sarah Johnson",
            project_name="Johnson Residence",
            summary="Client provided update on kitchen remodel. Cabinets arrived, install starts Monday.",
            action_items=["Confirm install crew for Monday"],
            response_needed=False,
            urgency="low",
        )
        client = self._make_mock_client(expected)

        result = parse_client_communication(
            "Hi Daniel, cabinets arrived yesterday. Install starts Monday. Thanks, Sarah",
            [],
            client=client,
        )

        assert result.client_name == "Sarah Johnson"
        assert result.project_name == "Johnson Residence"
        assert len(result.action_items) == 1
        assert result.urgency == "low"
        print("Project update parsed correctly")

    def test_parse_scheduling_request(self):
        """Test parsing a scheduling request"""
        expected = ClientData(
            client_name="Mike Davis",
            subject="Walkthrough scheduling",
            summary="Client requesting a walkthrough at the Smith residence on Thursday at 10am.",
            action_items=["Schedule walkthrough", "Confirm with client"],
            key_dates=["03/06/2026 - Proposed walkthrough"],
            response_needed=True,
            urgency="medium",
        )
        client = self._make_mock_client(expected)

        result = parse_client_communication(
            "Can we schedule a walkthrough Thursday at 10am? - Mike",
            [],
            client=client,
        )

        assert result.response_needed is True
        assert result.urgency == "medium"
        assert len(result.key_dates) == 1
        print("Scheduling request parsed correctly")

    def test_parse_urgent_communication(self):
        """Test parsing an urgent client email"""
        expected = ClientData(
            client_name="Tom Wilson",
            project_name="Wilson Commercial Build",
            summary="Urgent: water leak found at job site. Needs immediate attention.",
            action_items=["Send plumber to site ASAP", "Document damage for insurance"],
            response_needed=True,
            urgency="high",
        )
        client = self._make_mock_client(expected)

        result = parse_client_communication(
            "URGENT: There's a water leak at the job site. Please send someone immediately.",
            [],
            client=client,
        )

        assert result.urgency == "high"
        assert result.response_needed is True
        assert len(result.action_items) == 2
        print("Urgent communication parsed correctly")

    def test_parse_client_with_attachment(self):
        """Test that attachment content is included in context"""
        expected = ClientData(summary="Client sent updated floor plans.")
        client = self._make_mock_client(expected)

        parse_client_communication(
            "Please see the updated floor plans attached.",
            [("floor_plans_v2.pdf", "Updated layout for master bedroom...")],
            client=client,
        )

        call_args = client.responses.parse.call_args
        user_content = call_args.kwargs["input"][1]["content"]
        assert "floor_plans_v2.pdf" in user_content
        assert "Updated layout for master bedroom" in user_content
        print("Attachment content included in client context")

    def test_parse_client_prompt_content(self):
        """Test that the system prompt contains key extraction instructions"""
        expected = ClientData(summary="test")
        client = self._make_mock_client(expected)

        parse_client_communication("test", [], client=client)

        call_args = client.responses.parse.call_args
        system_content = call_args.kwargs["input"][0]["content"]
        assert "Client name" in system_content
        assert "Action items" in system_content
        assert "urgency" in system_content.lower()
        assert "summary" in system_content.lower()
        assert call_args.kwargs["text_format"] == ClientData
        print("Client prompt contains correct instructions")

    def test_parse_client_auth_failure_returns_none(self):
        """Test that auth failure returns None"""
        from openai import AuthenticationError
        client = MagicMock()
        client.responses.parse.side_effect = AuthenticationError(
            message="Invalid API key",
            response=MagicMock(status_code=401),
            body=None,
        )

        result = parse_client_communication("test", [], client=client)
        assert result is None
        print("Auth failure returns None")

    def test_parse_client_multiple_action_items(self):
        """Test parsing email with multiple action items and dates"""
        expected = ClientData(
            client_name="Lisa Chen",
            summary="Client outlined next steps for bathroom renovation.",
            action_items=[
                "Order tile samples",
                "Get plumber quote",
                "Schedule permit inspection",
                "Send updated timeline",
            ],
            key_dates=[
                "03/10/2026 - Tile samples due",
                "03/15/2026 - Permit inspection",
                "04/01/2026 - Project deadline",
            ],
            response_needed=True,
            urgency="medium",
        )
        client = self._make_mock_client(expected)

        result = parse_client_communication(
            "Here are the next steps we discussed...",
            [],
            client=client,
        )

        assert len(result.action_items) == 4
        assert len(result.key_dates) == 3
        print("Multiple action items and dates parsed correctly")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
