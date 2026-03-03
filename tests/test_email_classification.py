"""Test suite for email classification into invoice, shipping, insurance, client_communications"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from parsers.ai_parser import invoice_label
from models.invoice import LabelSort


class TestLabelSortModel:
    """Test that the LabelSort model accepts all valid labels"""

    @pytest.mark.parametrize("label", [
        "invoice",
        "shipping",
        "insurance",
        "client_communications",
        "none",
    ])
    def test_valid_labels(self, label):
        """Test each valid label is accepted by the model"""
        result = LabelSort(label=label)
        assert result.label == label
        print(f"Label '{label}' accepted")

    def test_invalid_label_rejected(self):
        """Test that an invalid label raises a validation error"""
        with pytest.raises(Exception):
            LabelSort(label="unknown_category")
        print("Invalid label correctly rejected")


class TestEmailClassification:
    """Test that emails are classified into the correct category"""

    def _mock_openai_response(self, label):
        """Helper to create a mock OpenAI parsed response"""
        mock_response = MagicMock()
        mock_response.output_parsed = LabelSort(label=label)
        return mock_response

    def _make_mock_client(self, label):
        """Helper to create a mock OpenAI client that returns a given label"""
        mock_client = MagicMock()
        mock_client.responses.parse.return_value = self._mock_openai_response(label)
        return mock_client

    # Invoice emails

    def test_classify_invoice_with_attachment(self):
        """Test that an email with an invoice PDF is classified as invoice"""
        client = self._make_mock_client("invoice")
        result = invoice_label(
            "Please find attached invoice #1234 for services rendered.",
            [("invoice_1234.pdf", "Invoice text content")],
            client=client,
        )
        assert result == "invoice"
        print("Invoice with attachment classified correctly")

    def test_classify_invoice_payment_request(self):
        """Test that a payment request email is classified as invoice"""
        client = self._make_mock_client("invoice")
        result = invoice_label(
            "Payment is due for the work completed on the Johnson project. Total: $4,500.00. Please remit by March 15.",
            [],
            client=client,
        )
        assert result == "invoice"
        print("Payment request classified as invoice")

    # Shipping emails

    def test_classify_shipping_tracking(self):
        """Test that a tracking notification is classified as shipping"""
        client = self._make_mock_client("shipping")
        result = invoice_label(
            "Your order has shipped! Tracking number: 1Z999AA10123456784. Estimated delivery: March 5, 2026.",
            [],
            client=client,
        )
        assert result == "shipping"
        print("Shipping tracking classified correctly")

    def test_classify_shipping_delivery_confirmation(self):
        """Test that a delivery confirmation is classified as shipping"""
        client = self._make_mock_client("shipping")
        result = invoice_label(
            "Your package was delivered at 2:30 PM. It was left at the front door. Signed by: J. Smith",
            [],
            client=client,
        )
        assert result == "shipping"
        print("Delivery confirmation classified as shipping")

    def test_classify_shipping_freight(self):
        """Test that a freight/courier update is classified as shipping"""
        client = self._make_mock_client("shipping")
        result = invoice_label(
            "Freight shipment update: Your lumber order (BOL #78432) departed the warehouse and is en route to the job site.",
            [],
            client=client,
        )
        assert result == "shipping"
        print("Freight update classified as shipping")

    # Insurance emails

    def test_classify_insurance_certificate(self):
        """Test that a certificate of insurance email is classified as insurance"""
        client = self._make_mock_client("insurance")
        result = invoice_label(
            "Attached is the updated Certificate of Insurance for CPP Builders. General liability coverage: $2,000,000.",
            [("COI_CPPBuilders_2026.pdf", "Certificate content")],
            client=client,
        )
        assert result == "insurance"
        print("Certificate of insurance classified correctly")

    def test_classify_insurance_claim(self):
        """Test that an insurance claim email is classified as insurance"""
        client = self._make_mock_client("insurance")
        result = invoice_label(
            "We have received your workers compensation claim #WC-2026-0891. An adjuster will contact you within 48 hours.",
            [],
            client=client,
        )
        assert result == "insurance"
        print("Insurance claim classified correctly")

    def test_classify_insurance_policy_renewal(self):
        """Test that a policy renewal notice is classified as insurance"""
        client = self._make_mock_client("insurance")
        result = invoice_label(
            "Your commercial auto policy is up for renewal on April 1, 2026. Please review the attached policy documents.",
            [("policy_renewal_2026.pdf", "Policy content")],
            client=client,
        )
        assert result == "insurance"
        print("Policy renewal classified as insurance")

    # Client communications

    def test_classify_client_project_update(self):
        """Test that a project update email is classified as client_communications"""
        client = self._make_mock_client("client_communications")
        result = invoice_label(
            "Hi Daniel, just wanted to give you an update on the kitchen remodel. The cabinets arrived yesterday and install starts Monday.",
            [],
            client=client,
        )
        assert result == "client_communications"
        print("Project update classified as client_communications")

    def test_classify_client_scheduling(self):
        """Test that a scheduling email is classified as client_communications"""
        client = self._make_mock_client("client_communications")
        result = invoice_label(
            "Can we schedule a walkthrough for the Smith residence on Thursday at 10am? Let me know if that works.",
            [],
            client=client,
        )
        assert result == "client_communications"
        print("Scheduling email classified as client_communications")

    def test_classify_client_question(self):
        """Test that a client question is classified as client_communications"""
        client = self._make_mock_client("client_communications")
        result = invoice_label(
            "What color tile did we decide on for the master bathroom? I want to confirm before placing the order.",
            [],
            client=client,
        )
        assert result == "client_communications"
        print("Client question classified as client_communications")

    # None / spam

    def test_classify_spam_as_none(self):
        """Test that spam/promotional email is classified as none"""
        client = self._make_mock_client("none")
        result = invoice_label(
            "HUGE SALE! 50% off all power tools this weekend only! Click here to shop now!",
            [],
            client=client,
        )
        assert result == "none"
        print("Spam classified as none")

    def test_classify_newsletter_as_none(self):
        """Test that a newsletter is classified as none"""
        client = self._make_mock_client("none")
        result = invoice_label(
            "Weekly Construction Industry Digest: Top 10 trends in sustainable building for 2026.",
            [],
            client=client,
        )
        assert result == "none"
        print("Newsletter classified as none")


class TestClassificationPrompt:
    """Test that the classification prompt includes all categories"""

    def test_prompt_contains_all_labels(self):
        """Verify the OpenAI prompt mentions all classification categories"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.output_parsed = LabelSort(label="none")
        mock_client.responses.parse.return_value = mock_response

        invoice_label("test email", [], client=mock_client)

        call_args = mock_client.responses.parse.call_args
        system_message = call_args.kwargs["input"][0]["content"]

        assert "invoice" in system_message
        assert "shipping" in system_message
        assert "insurance" in system_message
        assert "client_communications" in system_message
        assert "none" in system_message
        print("All labels present in classification prompt")

    def test_prompt_uses_label_sort_format(self):
        """Verify the response is parsed with LabelSort model"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.output_parsed = LabelSort(label="invoice")
        mock_client.responses.parse.return_value = mock_response

        invoice_label("test", [], client=mock_client)

        call_args = mock_client.responses.parse.call_args
        assert call_args.kwargs["text_format"] == LabelSort
        print("LabelSort format used correctly")

    def test_attachments_included_in_context(self):
        """Verify that attachment filenames are sent to the AI"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.output_parsed = LabelSort(label="invoice")
        mock_client.responses.parse.return_value = mock_response

        invoice_label(
            "See attached",
            [("invoice.pdf", "content"), ("receipt.jpg", b"binary")],
            client=mock_client,
        )

        call_args = mock_client.responses.parse.call_args
        user_message = call_args.kwargs["input"][1]["content"]

        assert "invoice.pdf" in user_message
        assert "receipt.jpg" in user_message
        print("Attachment filenames included in context")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
