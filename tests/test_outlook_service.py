"""Test suite for Microsoft Outlook email service"""
import sys
import base64
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from services.outlook_service import (
    _get_access_token,
    fetch_messages_with_attachments,
    MS_GRAPH_BASE_URL,
)


class TestOutlookAuth:
    """Test Microsoft OAuth authentication"""

    @patch("services.outlook_service.msal.ClientApplication")
    @patch("services.outlook_service.TOKEN_PATH")
    @patch.dict("os.environ", {
        "MICROSOFT_CLIENT_ID": "test-client-id",
        "MICROSOFT_CLIENT_SECRET": "test-client-secret",
        "MICROSOFT_TENANT_ID": "test-tenant-id",
    })
    def test_auth_with_refresh_token(self, mock_token_path, mock_msal):
        """Test authentication using a stored refresh token"""
        mock_token_path.exists.return_value = True
        mock_token_path.read_text.return_value = "fake-refresh-token"

        mock_app = MagicMock()
        mock_msal.return_value = mock_app
        mock_app.acquire_token_by_refresh_token.return_value = {
            "access_token": "fake-access-token",
            "refresh_token": "new-refresh-token",
        }

        token = _get_access_token()

        assert token == "fake-access-token"
        mock_app.acquire_token_by_refresh_token.assert_called_once_with(
            "fake-refresh-token", scopes=["User.Read", "Mail.ReadWrite"]
        )
        mock_token_path.write_text.assert_called_once_with("new-refresh-token")
        print("Auth with refresh token works")

    @patch("services.outlook_service.msal.ClientApplication")
    @patch("services.outlook_service.TOKEN_PATH")
    @patch.dict("os.environ", {
        "MICROSOFT_CLIENT_ID": "test-client-id",
        "MICROSOFT_CLIENT_SECRET": "test-client-secret",
        "MICROSOFT_TENANT_ID": "test-tenant-id",
    })
    def test_auth_fails_without_token(self, mock_token_path, mock_msal):
        """Test that auth raises when no refresh token and no interactive login"""
        mock_token_path.exists.return_value = True
        mock_token_path.read_text.return_value = "expired-token"

        mock_app = MagicMock()
        mock_msal.return_value = mock_app
        mock_app.acquire_token_by_refresh_token.return_value = {
            "error": "invalid_grant",
            "error_description": "Token expired",
        }

        with pytest.raises(Exception, match="Failed to acquire access token"):
            _get_access_token()
        print("Auth failure handled correctly")

    @patch("services.outlook_service.msal.ClientApplication")
    @patch("services.outlook_service.TOKEN_PATH")
    @patch.dict("os.environ", {
        "MICROSOFT_CLIENT_ID": "test-client-id",
        "MICROSOFT_CLIENT_SECRET": "test-client-secret",
        "MICROSOFT_TENANT_ID": "test-tenant-id",
    })
    def test_auth_uses_correct_authority(self, mock_token_path, mock_msal):
        """Test that the authority URL uses the tenant ID from .env"""
        mock_token_path.exists.return_value = True
        mock_token_path.read_text.return_value = "fake-token"

        mock_app = MagicMock()
        mock_msal.return_value = mock_app
        mock_app.acquire_token_by_refresh_token.return_value = {
            "access_token": "fake-access-token",
        }

        _get_access_token()

        mock_msal.assert_called_once_with(
            client_id="test-client-id",
            authority="https://login.microsoftonline.com/test-tenant-id",
            client_credential="test-client-secret",
        )
        print("Authority URL built correctly from tenant ID")


class TestFetchMessages:
    """Test fetching emails and attachments from Outlook"""

    def _mock_messages_response(self, messages):
        """Helper to create a mock httpx response for messages"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"value": messages}
        return mock_resp

    def _mock_attachments_response(self, attachments):
        """Helper to create a mock httpx response for attachments"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"value": attachments}
        return mock_resp

    @patch("services.outlook_service._get_access_token", return_value="fake-token")
    @patch("services.outlook_service.httpx.get")
    def test_fetch_empty_inbox(self, mock_get, mock_auth):
        """Test fetching from an inbox with no messages"""
        mock_get.return_value = self._mock_messages_response([])

        results = list(fetch_messages_with_attachments())

        assert len(results) == 0
        print("Empty inbox handled correctly")

    @patch("services.outlook_service._get_access_token", return_value="fake-token")
    @patch("services.outlook_service.httpx.get")
    def test_fetch_message_with_html_body(self, mock_get, mock_auth):
        """Test that HTML email bodies are converted to plain text"""
        messages = [
            {
                "id": "msg-001",
                "subject": "Test Invoice",
                "body": {
                    "contentType": "html",
                    "content": "<html><body><p>Please see attached invoice.</p></body></html>",
                },
                "hasAttachments": False,
            }
        ]

        mock_get.return_value = self._mock_messages_response(messages)

        results = list(fetch_messages_with_attachments())

        assert len(results) == 1
        msg_id, subject, body_text, attachments = results[0]
        assert msg_id == "msg-001"
        assert subject == "Test Invoice"
        assert "Please see attached invoice." in body_text
        assert len(attachments) == 0
        print("HTML body parsed correctly")

    @patch("services.outlook_service._get_access_token", return_value="fake-token")
    @patch("services.outlook_service.httpx.get")
    def test_fetch_message_with_plain_text_body(self, mock_get, mock_auth):
        """Test that plain text email bodies are returned as-is"""
        messages = [
            {
                "id": "msg-002",
                "subject": "Plain Text Invoice",
                "body": {
                    "contentType": "text",
                    "content": "Here is your invoice for March.",
                },
                "hasAttachments": False,
            }
        ]

        mock_get.return_value = self._mock_messages_response(messages)

        results = list(fetch_messages_with_attachments())

        msg_id, subject, body_text, attachments = results[0]
        assert body_text == "Here is your invoice for March."
        print("Plain text body returned correctly")

    @patch("services.outlook_service.extract_text_from_pdf")
    @patch("services.outlook_service._get_access_token", return_value="fake-token")
    @patch("services.outlook_service.httpx.get")
    def test_fetch_message_with_pdf_attachment(self, mock_get, mock_auth, mock_pdf_extract):
        """Test downloading and processing a PDF attachment"""
        pdf_bytes = b"%PDF-1.4 fake pdf content"
        pdf_b64 = base64.b64encode(pdf_bytes).decode()

        messages = [
            {
                "id": "msg-003",
                "subject": "Invoice Attached",
                "body": {"contentType": "text", "content": "See attached."},
                "hasAttachments": True,
            }
        ]

        attachments_data = [
            {
                "name": "invoice_march.pdf",
                "contentBytes": pdf_b64,
                "isInline": False,
            }
        ]

        mock_pdf_extract.return_value = "Extracted PDF text here"

        def side_effect(url, **kwargs):
            if "/attachments" in url:
                return self._mock_attachments_response(attachments_data)
            return self._mock_messages_response(messages)

        mock_get.side_effect = side_effect

        results = list(fetch_messages_with_attachments())

        assert len(results) == 1
        msg_id, subject, body_text, attachments = results[0]
        assert len(attachments) == 1
        filename, content = attachments[0]
        assert filename == "invoice_march.pdf"
        assert content == "Extracted PDF text here"
        print("PDF attachment downloaded and processed")

    @patch("services.outlook_service._get_access_token", return_value="fake-token")
    @patch("services.outlook_service.httpx.get")
    def test_fetch_message_with_image_attachment(self, mock_get, mock_auth):
        """Test downloading an image attachment (JPEG)"""
        image_bytes = b"\xff\xd8\xff\xe0 fake jpeg data"
        image_b64 = base64.b64encode(image_bytes).decode()

        messages = [
            {
                "id": "msg-004",
                "subject": "Receipt Photo",
                "body": {"contentType": "text", "content": "Photo receipt."},
                "hasAttachments": True,
            }
        ]

        attachments_data = [
            {
                "name": "receipt.jpg",
                "contentBytes": image_b64,
                "isInline": False,
            }
        ]

        def side_effect(url, **kwargs):
            if "/attachments" in url:
                return self._mock_attachments_response(attachments_data)
            return self._mock_messages_response(messages)

        mock_get.side_effect = side_effect

        results = list(fetch_messages_with_attachments())

        msg_id, subject, body_text, attachments = results[0]
        assert len(attachments) == 1
        filename, content = attachments[0]
        assert filename == "receipt.jpg"
        assert content == image_bytes
        print("Image attachment downloaded as binary")

    @patch("services.outlook_service._get_access_token", return_value="fake-token")
    @patch("services.outlook_service.httpx.get")
    def test_inline_attachments_are_skipped(self, mock_get, mock_auth):
        """Test that inline images (signatures, etc.) are skipped"""
        image_b64 = base64.b64encode(b"inline image data").decode()

        messages = [
            {
                "id": "msg-005",
                "subject": "Email with Signature",
                "body": {"contentType": "text", "content": "Hello."},
                "hasAttachments": True,
            }
        ]

        attachments_data = [
            {
                "name": "signature_logo.png",
                "contentBytes": image_b64,
                "isInline": True,
            }
        ]

        def side_effect(url, **kwargs):
            if "/attachments" in url:
                return self._mock_attachments_response(attachments_data)
            return self._mock_messages_response(messages)

        mock_get.side_effect = side_effect

        results = list(fetch_messages_with_attachments())

        msg_id, subject, body_text, attachments = results[0]
        assert len(attachments) == 0
        print("Inline attachments correctly skipped")

    @patch("services.outlook_service._get_access_token", return_value="fake-token")
    @patch("services.outlook_service.httpx.get")
    def test_api_error_raises_exception(self, mock_get, mock_auth):
        """Test that a non-200 response raises an exception"""
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"
        mock_get.return_value = mock_resp

        with pytest.raises(Exception, match="Failed to retrieve emails"):
            list(fetch_messages_with_attachments())
        print("API error handled correctly")

    @patch("services.outlook_service._get_access_token", return_value="fake-token")
    @patch("services.outlook_service.httpx.get")
    def test_max_results_parameter(self, mock_get, mock_auth):
        """Test that max_results is passed to the API"""
        mock_get.return_value = self._mock_messages_response([])

        list(fetch_messages_with_attachments(max_results=5))

        call_kwargs = mock_get.call_args
        assert call_kwargs.kwargs["params"]["$top"] == 5
        print("max_results parameter passed correctly")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
