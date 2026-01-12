#!/usr/bin/env python3
"""
Test script to process multiple invoice PDFs and extract invoice data.
"""
from pathlib import Path
from typing import Optional, List, Dict, Any
import json
from openai import OpenAI
from pdf_parser import extract_text_from_pdf
from push_invoice import InvoiceDraft, InvoiceLine
from pydantic import BaseModel
from typing import Literal
import sys
import traceback


class TestResult(BaseModel):
    """Results from processing a single invoice"""
    filename: str
    success: bool
    invoice_data: Optional[InvoiceDraft] = None
    error: Optional[str] = None
    page_count: Optional[int] = None


def build_invoice_draft(message_text: str, client: Optional[OpenAI] = None) -> Optional[InvoiceDraft]:
    """Extract invoice data from text using OpenAI"""
    if client is None:
        client = OpenAI()

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
        payload = response.output_parsed

        if not payload or not payload.line_items:
            return None

        line_items = [
            InvoiceLine(
                item=item.item,
                rate=item.rate,
                quantity=item.quantity,
                description=item.description,
            )
            for item in payload.line_items
            if item.item and item.rate is not None
        ]

        if not line_items or not payload.vendor_display_name:
            return None

        return InvoiceDraft(
            vendor_display_name=payload.vendor_display_name,
            memo=payload.memo,
            line_items=line_items,
            tax=payload.tax,
            total_amount=payload.total_amount,
        )
    except Exception as e:
        print(f"Error in build_invoice_draft: {str(e)}")
        return None


def process_invoice_pdf(pdf_path: Path, client: OpenAI, verbose: bool = False) -> TestResult:
    """Process a single invoice PDF and extract data"""
    try:
        if verbose:
            print(f"\nProcessing: {pdf_path.name}")

        # Extract text from PDF
        pdf_text = extract_text_from_pdf(pdf_path)

        if not pdf_text or len(pdf_text.strip()) < 50:
            return TestResult(
                filename=pdf_path.name,
                success=False,
                error="Insufficient text extracted from PDF"
            )

        if verbose:
            print(f"  Extracted {len(pdf_text)} characters of text")

        # Build invoice draft
        invoice = build_invoice_draft(pdf_text, client=client)

        if invoice:
            if verbose:
                print(f"  ✓ Vendor: {invoice.vendor_display_name}")
                print(f"  ✓ Line items: {len(invoice.line_items)}")
                print(f"  ✓ Total: ${invoice.total_amount:.2f}" if invoice.total_amount else "  ✓ Total: Not specified")

            return TestResult(
                filename=pdf_path.name,
                success=True,
                invoice_data=invoice
            )
        else:
            return TestResult(
                filename=pdf_path.name,
                success=False,
                error="No valid invoice data extracted"
            )

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        if verbose:
            print(f"  ✗ Error: {error_msg}")
            traceback.print_exc()

        return TestResult(
            filename=pdf_path.name,
            success=False,
            error=error_msg
        )


def test_invoices(
    invoice_dir: Path,
    output_file: Optional[Path] = None,
    max_invoices: Optional[int] = None,
    verbose: bool = True
) -> List[TestResult]:
    """
    Test invoice extraction on multiple PDF files.

    Args:
        invoice_dir: Directory containing invoice PDFs
        output_file: Optional path to save JSON results
        max_invoices: Optional limit on number of invoices to process
        verbose: Print detailed progress

    Returns:
        List of TestResult objects
    """
    # Get all PDF files
    pdf_files = sorted(invoice_dir.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in {invoice_dir}")
        return []

    if max_invoices:
        pdf_files = pdf_files[:max_invoices]

    print(f"Found {len(pdf_files)} invoice PDF files")
    print("=" * 70)

    # Initialize OpenAI client
    client = OpenAI()

    # Process each invoice
    results = []
    for idx, pdf_path in enumerate(pdf_files, 1):
        if verbose:
            print(f"\n[{idx}/{len(pdf_files)}] {pdf_path.name}")

        result = process_invoice_pdf(pdf_path, client, verbose=verbose)
        results.append(result)

        if not verbose:
            # Show progress without details
            status = "✓" if result.success else "✗"
            print(f"[{idx}/{len(pdf_files)}] {status} {pdf_path.name}")

    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    successful = sum(1 for r in results if r.success)
    failed = len(results) - successful

    print(f"Total processed: {len(results)}")
    print(f"Successful: {successful} ({successful/len(results)*100:.1f}%)")
    print(f"Failed: {failed} ({failed/len(results)*100:.1f}%)")

    # Show failures
    if failed > 0:
        print("\nFailed invoices:")
        for result in results:
            if not result.success:
                print(f"  - {result.filename}: {result.error}")

    # Show successful extractions summary
    if successful > 0:
        print("\nSuccessful extractions:")
        vendors = {}
        total_amount = 0
        for result in results:
            if result.success and result.invoice_data:
                vendor = result.invoice_data.vendor_display_name
                vendors[vendor] = vendors.get(vendor, 0) + 1
                if result.invoice_data.total_amount:
                    total_amount += result.invoice_data.total_amount

        print(f"\nUnique vendors found: {len(vendors)}")
        for vendor, count in sorted(vendors.items(), key=lambda x: x[1], reverse=True):
            print(f"  - {vendor}: {count} invoice(s)")

        if total_amount > 0:
            print(f"\nTotal invoice amount: ${total_amount:,.2f}")

    # Save results to JSON if requested
    if output_file:
        output_data = {
            "summary": {
                "total": len(results),
                "successful": successful,
                "failed": failed,
                "success_rate": f"{successful/len(results)*100:.1f}%"
            },
            "results": [
                {
                    "filename": r.filename,
                    "success": r.success,
                    "error": r.error,
                    "vendor": r.invoice_data.vendor_display_name if r.invoice_data else None,
                    "total": r.invoice_data.total_amount if r.invoice_data else None,
                    "line_items_count": len(r.invoice_data.line_items) if r.invoice_data else 0
                }
                for r in results
            ]
        }

        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        print(f"\nResults saved to: {output_file}")

    return results


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Test AI invoice extraction on multiple PDFs")
    parser.add_argument(
        "--dir",
        type=Path,
        default=Path("/home/dan/projects/boriss/invoices/split_invoices"),
        help="Directory containing invoice PDFs"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output JSON file for results"
    )
    parser.add_argument(
        "--max",
        type=int,
        help="Maximum number of invoices to process (for testing)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce output verbosity"
    )

    args = parser.parse_args()

    # Run tests
    results = test_invoices(
        invoice_dir=args.dir,
        output_file=args.output,
        max_invoices=args.max,
        verbose=not args.quiet
    )

    # Exit with appropriate code
    successful = sum(1 for r in results if r.success)
    if successful == len(results):
        sys.exit(0)
    elif successful > 0:
        sys.exit(1)  # Partial success
    else:
        sys.exit(2)  # Complete failure


if __name__ == "__main__":
    main()
