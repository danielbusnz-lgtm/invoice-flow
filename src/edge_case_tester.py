#!/usr/bin/env python3
"""
Edge case testing for AI-Invoice extraction.
Tests various challenging scenarios and documents failures.
"""
from pathlib import Path
from typing import Optional, List, Dict, Any
import json
from openai import OpenAI
from pdf_parser import extract_text_from_pdf
from push_invoice import InvoiceDraft, InvoiceLine
from dotenv import load_dotenv
import traceback
from collections import defaultdict

# Load environment variables
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env")


class EdgeCaseResult:
    """Results from testing a single invoice"""
    def __init__(self, filename: str):
        self.filename = filename
        self.success = False
        self.invoice_data: Optional[InvoiceDraft] = None
        self.text_length = 0
        self.edge_cases_detected = []
        self.errors = []
        self.warnings = []


def build_invoice_draft(message_text: str, client: OpenAI) -> Optional[InvoiceDraft]:
    """Extract invoice data from text using OpenAI"""
    try:
        response = client.responses.parse(
            model="gpt-4o-2024-08-06",
            input=[
                {
                    "role": "system",
                    "content": (
                        "Extract structured invoice data from the provided text. "
                        "Always respond with JSON matching the schema. "
                        "If you do not find invoice information, return an empty items list. "
                        "Our company name is Cape Property Pros, and we are always the receiver of the invoice."
                    ),
                },
                {"role": "user", "content": message_text},
            ],
            text_format=InvoiceDraft,
        )
        return response.output_parsed
    except Exception as e:
        print(f"Error in build_invoice_draft: {str(e)}")
        return None


def detect_edge_cases(result: EdgeCaseResult, pdf_text: str):
    """Detect various edge cases in the invoice"""

    # Check for scanned/image-based PDFs
    if result.text_length < 50:
        result.edge_cases_detected.append("SCANNED_PDF")
        result.errors.append("Insufficient text extracted - likely scanned image")

    # Check invoice data quality if extraction succeeded
    if result.invoice_data:
        invoice = result.invoice_data

        # Missing vendor
        if not invoice.vendor_display_name or len(invoice.vendor_display_name.strip()) < 2:
            result.edge_cases_detected.append("MISSING_VENDOR")
            result.errors.append("Vendor name missing or too short")

        # No line items
        if not invoice.line_items or len(invoice.line_items) == 0:
            result.edge_cases_detected.append("NO_LINE_ITEMS")
            result.errors.append("No line items extracted")

        # Missing total
        if invoice.total_amount is None or invoice.total_amount == 0:
            result.edge_cases_detected.append("MISSING_TOTAL")
            result.warnings.append("Total amount not specified")

        # Check line items for issues
        for idx, item in enumerate(invoice.line_items):
            # Zero or negative quantity
            if item.quantity <= 0:
                result.edge_cases_detected.append("INVALID_QUANTITY")
                result.warnings.append(f"Line {idx+1}: Invalid quantity ({item.quantity})")

            # Zero or negative rate
            if item.rate <= 0:
                result.edge_cases_detected.append("INVALID_RATE")
                result.warnings.append(f"Line {idx+1}: Invalid rate ({item.rate})")

            # Missing item name
            if not item.item or len(item.item.strip()) < 2:
                result.edge_cases_detected.append("MISSING_ITEM_NAME")
                result.warnings.append(f"Line {idx+1}: Item name missing or too short")

        # Calculate total from line items and compare
        if invoice.total_amount:
            calculated_total = sum(item.amount for item in invoice.line_items)
            if invoice.tax:
                calculated_total += invoice.tax

            difference = abs(invoice.total_amount - calculated_total)
            if difference > 0.02:  # Allow 2 cent rounding difference
                result.edge_cases_detected.append("TOTAL_MISMATCH")
                result.warnings.append(
                    f"Total mismatch: Invoice=${invoice.total_amount:.2f}, "
                    f"Calculated=${calculated_total:.2f}, Diff=${difference:.2f}"
                )

        # Check for negative amounts (credits/returns)
        if invoice.total_amount and invoice.total_amount < 0:
            result.edge_cases_detected.append("CREDIT_NOTE")
            result.warnings.append("Negative total - may be a credit note")

        # Very large invoice
        if invoice.total_amount and invoice.total_amount > 10000:
            result.edge_cases_detected.append("LARGE_INVOICE")
            result.warnings.append(f"Large invoice amount: ${invoice.total_amount:,.2f}")

        # Many line items
        if len(invoice.line_items) > 20:
            result.edge_cases_detected.append("MANY_LINE_ITEMS")
            result.warnings.append(f"High number of line items: {len(invoice.line_items)}")

    # Check PDF text for potential issues
    text_lower = pdf_text.lower()

    # Multi-page indicators
    if "page " in text_lower and ("of " in text_lower or "/" in text_lower):
        result.edge_cases_detected.append("MULTI_PAGE")

    # Credit note indicators
    if any(word in text_lower for word in ["credit memo", "credit note", "refund", "return"]):
        result.edge_cases_detected.append("CREDIT_NOTE")

    # Quote vs Invoice confusion
    if "quote" in text_lower or "estimate" in text_lower:
        result.edge_cases_detected.append("QUOTE_NOT_INVOICE")
        result.warnings.append("Document may be a quote/estimate, not an invoice")

    # Statement confusion
    if "statement" in text_lower and "invoice" not in text_lower:
        result.edge_cases_detected.append("STATEMENT_NOT_INVOICE")
        result.warnings.append("Document may be a statement, not an invoice")


def test_invoice_edge_cases(pdf_path: Path, client: OpenAI, verbose: bool = False) -> EdgeCaseResult:
    """Test a single invoice PDF for edge cases"""
    result = EdgeCaseResult(pdf_path.name)

    try:
        # Extract text from PDF
        pdf_text = extract_text_from_pdf(pdf_path)
        result.text_length = len(pdf_text)

        if verbose:
            print(f"\n{'='*70}")
            print(f"Testing: {pdf_path.name}")
            print(f"Text extracted: {result.text_length} characters")

        # Skip if insufficient text
        if result.text_length < 50:
            detect_edge_cases(result, pdf_text)
            return result

        # Build invoice draft
        invoice = build_invoice_draft(pdf_text, client)

        if invoice:
            result.success = True
            result.invoice_data = invoice

            if verbose:
                print(f"✓ Extraction successful")
                print(f"  Vendor: {invoice.vendor_display_name}")
                print(f"  Line items: {len(invoice.line_items)}")
                print(f"  Total: ${invoice.total_amount:.2f}" if invoice.total_amount else "  Total: Not specified")
        else:
            result.errors.append("Invoice extraction returned None")
            if verbose:
                print(f"✗ Extraction failed")

        # Detect edge cases
        detect_edge_cases(result, pdf_text)

        if verbose and (result.edge_cases_detected or result.warnings or result.errors):
            if result.edge_cases_detected:
                print(f"\nEdge cases detected: {', '.join(result.edge_cases_detected)}")
            if result.warnings:
                print(f"Warnings:")
                for warning in result.warnings:
                    print(f"  ⚠ {warning}")
            if result.errors:
                print(f"Errors:")
                for error in result.errors:
                    print(f"  ✗ {error}")

    except Exception as e:
        result.errors.append(f"Exception: {type(e).__name__}: {str(e)}")
        if verbose:
            print(f"\n✗ Exception occurred: {e}")
            traceback.print_exc()

    return result


def run_edge_case_tests(
    invoice_dir: Path,
    max_invoices: Optional[int] = None,
    output_file: Optional[Path] = None,
    verbose: bool = False
) -> List[EdgeCaseResult]:
    """
    Run edge case tests on multiple invoices
    """
    # Get all PDF files
    pdf_files = sorted(invoice_dir.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in {invoice_dir}")
        return []

    if max_invoices:
        pdf_files = pdf_files[:max_invoices]

    print(f"\n{'='*70}")
    print(f"EDGE CASE TESTING - AI INVOICE EXTRACTOR")
    print(f"{'='*70}")
    print(f"Testing {len(pdf_files)} invoice(s)")
    print(f"{'='*70}\n")

    # Initialize OpenAI client
    client = OpenAI()

    # Process each invoice
    results = []
    for idx, pdf_path in enumerate(pdf_files, 1):
        if not verbose:
            print(f"[{idx}/{len(pdf_files)}] Testing {pdf_path.name}...", end=" ")

        result = test_invoice_edge_cases(pdf_path, client, verbose=verbose)
        results.append(result)

        if not verbose:
            status = "✓" if result.success else "✗"
            edge_info = f" ({len(result.edge_cases_detected)} edge cases)" if result.edge_cases_detected else ""
            print(f"{status}{edge_info}")

    # Generate summary report
    print(f"\n{'='*70}")
    print("EDGE CASE TEST SUMMARY")
    print(f"{'='*70}\n")

    total = len(results)
    successful = sum(1 for r in results if r.success)
    failed = total - successful

    print(f"Total invoices tested: {total}")
    print(f"Successful extractions: {successful} ({successful/total*100:.1f}%)")
    print(f"Failed extractions: {failed} ({failed/total*100:.1f}%)")

    # Edge case statistics
    edge_case_counts = defaultdict(int)
    for result in results:
        for edge_case in result.edge_cases_detected:
            edge_case_counts[edge_case] += 1

    if edge_case_counts:
        print(f"\nEdge Cases Detected:")
        for edge_case, count in sorted(edge_case_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total) * 100
            print(f"  {edge_case}: {count} ({percentage:.1f}%)")

    # Show problematic invoices
    problematic = [r for r in results if r.errors or len(r.edge_cases_detected) >= 2]
    if problematic:
        print(f"\nProblematic Invoices ({len(problematic)}):")
        for result in problematic[:10]:  # Show first 10
            print(f"\n  {result.filename}:")
            if result.errors:
                for error in result.errors:
                    print(f"    ✗ {error}")
            if result.edge_cases_detected:
                print(f"    Edge cases: {', '.join(result.edge_cases_detected)}")

    # Save detailed results to JSON
    if output_file:
        output_data = {
            "summary": {
                "total": total,
                "successful": successful,
                "failed": failed,
                "success_rate": f"{successful/total*100:.1f}%"
            },
            "edge_case_statistics": dict(edge_case_counts),
            "results": [
                {
                    "filename": r.filename,
                    "success": r.success,
                    "text_length": r.text_length,
                    "edge_cases": r.edge_cases_detected,
                    "errors": r.errors,
                    "warnings": r.warnings,
                    "vendor": r.invoice_data.vendor_display_name if r.invoice_data else None,
                    "total": r.invoice_data.total_amount if r.invoice_data else None,
                    "line_items_count": len(r.invoice_data.line_items) if r.invoice_data else 0
                }
                for r in results
            ]
        }

        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        print(f"\nDetailed results saved to: {output_file}")

    return results


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Test AI invoice extraction with edge cases")
    parser.add_argument(
        "--dir",
        type=Path,
        default=Path("/home/dan/projects/boriss/invoices/split_invoices"),
        help="Directory containing invoice PDFs"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/home/dan/projects/boriss/Ai-Invoice/edge_case_results.json"),
        help="Output JSON file for results"
    )
    parser.add_argument(
        "--max",
        type=int,
        help="Maximum number of invoices to test"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output for each invoice"
    )

    args = parser.parse_args()

    # Run edge case tests
    results = run_edge_case_tests(
        invoice_dir=args.dir,
        max_invoices=args.max,
        output_file=args.output,
        verbose=args.verbose
    )

    # Exit with appropriate code
    failed = sum(1 for r in results if not r.success)
    if failed == 0:
        exit(0)
    elif failed < len(results):
        exit(1)  # Partial failure
    else:
        exit(2)  # Complete failure


if __name__ == "__main__":
    main()
