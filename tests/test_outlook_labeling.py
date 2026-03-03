"""Test suite for applying category labels to Outlook emails"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from services.outlook_service import label_message, LABEL_TO_CATEGORY, MS_GRAPH_BASE_URL


class TestLabelMapping:
    """Test that internal labels map to the correct Outlook category names"""

    def test_invoice_maps_to_invoice(self):
        assert LABEL_TO_CATEGORY["invoice"] == "Invoice"
        print("invoice -> Invoice")

    def test_shipping_maps_to_shipping(self):
        assert LABEL_TO_CATEGORY["shipping"] == "Shipping"
        print("shipping -> Shipping")

    def test_insurance_maps_to_insurance(self):
        assert LABEL_TO_CATEGORY["insurance"] == "Insurance"
        print("insurance -> Insurance")

    def test_client_communications_maps(self):
        assert LABEL_TO_CATEGORY["client_communications"] == "Client Communications"
        print("client_communications -> Client Communications")

    def test_none_maps_to_uncategorized(self):
        assert LABEL_TO_CATEGORY["none"] == "Uncategorized"
        print("none -> Uncategorized")

    def test_all_labels_have_mapping(self):
        """Ensure every classification label has an Outlook category mapping"""
        expected_labels = ["invoice", "shipping", "insurance", "client_communications", "none"]
        for label in expected_labels:
            assert label in LABEL_TO_CATEGORY, f"Missing mapping for '{label}'"
        print("All labels have mappings")


class TestLabelMessage:
    """Test the label_message() function"""

    @patch("services.outlook_service._get_access_token", return_value="fake-token")
    @patch("services.outlook_service.httpx.patch")
    def test_label_invoice(self, mock_patch, mock_auth):
        """Test labeling a message as Invoice"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "msg-001", "categories": ["Invoice"]}
        mock_patch.return_value = mock_resp

        result = label_message("msg-001", "invoice")

        mock_patch.assert_called_once_with(
            f"{MS_GRAPH_BASE_URL}/me/messages/msg-001",
            headers={
                "Authorization": "Bearer fake-token",
                "Content-Type": "application/json",
            },
            json={"categories": ["Invoice"]},
            timeout=30.0,
        )
        assert result["categories"] == ["Invoice"]
        print("Invoice label applied correctly")

    @patch("services.outlook_service._get_access_token", return_value="fake-token")
    @patch("services.outlook_service.httpx.patch")
    def test_label_shipping(self, mock_patch, mock_auth):
        """Test labeling a message as Shipping"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "msg-002", "categories": ["Shipping"]}
        mock_patch.return_value = mock_resp

        result = label_message("msg-002", "shipping")

        call_kwargs = mock_patch.call_args
        assert call_kwargs.kwargs["json"] == {"categories": ["Shipping"]}
        print("Shipping label applied correctly")

    @patch("services.outlook_service._get_access_token", return_value="fake-token")
    @patch("services.outlook_service.httpx.patch")
    def test_label_insurance(self, mock_patch, mock_auth):
        """Test labeling a message as Insurance"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "msg-003", "categories": ["Insurance"]}
        mock_patch.return_value = mock_resp

        result = label_message("msg-003", "insurance")

        call_kwargs = mock_patch.call_args
        assert call_kwargs.kwargs["json"] == {"categories": ["Insurance"]}
        print("Insurance label applied correctly")

    @patch("services.outlook_service._get_access_token", return_value="fake-token")
    @patch("services.outlook_service.httpx.patch")
    def test_label_client_communications(self, mock_patch, mock_auth):
        """Test labeling a message as Client Communications"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "msg-004", "categories": ["Client Communications"]}
        mock_patch.return_value = mock_resp

        result = label_message("msg-004", "client_communications")

        call_kwargs = mock_patch.call_args
        assert call_kwargs.kwargs["json"] == {"categories": ["Client Communications"]}
        print("Client Communications label applied correctly")

    @patch("services.outlook_service._get_access_token", return_value="fake-token")
    @patch("services.outlook_service.httpx.patch")
    def test_label_none(self, mock_patch, mock_auth):
        """Test labeling a message as Uncategorized"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "msg-005", "categories": ["Uncategorized"]}
        mock_patch.return_value = mock_resp

        result = label_message("msg-005", "none")

        call_kwargs = mock_patch.call_args
        assert call_kwargs.kwargs["json"] == {"categories": ["Uncategorized"]}
        print("Uncategorized label applied correctly")

    @patch("services.outlook_service._get_access_token", return_value="fake-token")
    @patch("services.outlook_service.httpx.patch")
    def test_label_unknown_falls_back_to_raw(self, mock_patch, mock_auth):
        """Test that an unknown label is passed through as-is"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "msg-006", "categories": ["custom_label"]}
        mock_patch.return_value = mock_resp

        result = label_message("msg-006", "custom_label")

        call_kwargs = mock_patch.call_args
        assert call_kwargs.kwargs["json"] == {"categories": ["custom_label"]}
        print("Unknown label passed through as-is")


class TestLabelMessageErrors:
    """Test error handling for label_message()"""

    @patch("services.outlook_service._get_access_token", return_value="fake-token")
    @patch("services.outlook_service.httpx.patch")
    def test_401_raises_exception(self, mock_patch, mock_auth):
        """Test that a 401 response raises an exception"""
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"
        mock_patch.return_value = mock_resp

        with pytest.raises(Exception, match="Failed to label message"):
            label_message("msg-001", "invoice")
        print("401 error handled correctly")

    @patch("services.outlook_service._get_access_token", return_value="fake-token")
    @patch("services.outlook_service.httpx.patch")
    def test_404_raises_exception(self, mock_patch, mock_auth):
        """Test that a 404 (message not found) raises an exception"""
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.text = "Message not found"
        mock_patch.return_value = mock_resp

        with pytest.raises(Exception, match="Failed to label message"):
            label_message("nonexistent-id", "invoice")
        print("404 error handled correctly")

    @patch("services.outlook_service._get_access_token", return_value="fake-token")
    @patch("services.outlook_service.httpx.patch")
    def test_error_includes_message_id(self, mock_patch, mock_auth):
        """Test that the error message includes the message ID for debugging"""
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_patch.return_value = mock_resp

        with pytest.raises(Exception, match="msg-999"):
            label_message("msg-999", "invoice")
        print("Error message includes message ID")

    @patch("services.outlook_service._get_access_token", return_value="fake-token")
    @patch("services.outlook_service.httpx.patch")
    def test_correct_endpoint_used(self, mock_patch, mock_auth):
        """Test that the PATCH request hits the correct Graph API endpoint"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {}
        mock_patch.return_value = mock_resp

        label_message("abc-123", "invoice")

        call_args = mock_patch.call_args
        assert call_args.args[0] == f"{MS_GRAPH_BASE_URL}/me/messages/abc-123"
        print("Correct API endpoint used")

    @patch("services.outlook_service._get_access_token", return_value="fake-token")
    @patch("services.outlook_service.httpx.patch")
    def test_auth_token_in_header(self, mock_patch, mock_auth):
        """Test that the access token is included in the request header"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {}
        mock_patch.return_value = mock_resp

        label_message("msg-001", "invoice")

        call_kwargs = mock_patch.call_args
        assert call_kwargs.kwargs["headers"]["Authorization"] == "Bearer fake-token"
        print("Auth token included in header")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
