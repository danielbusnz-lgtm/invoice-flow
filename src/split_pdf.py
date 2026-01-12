#!/usr/bin/env python3
"""
Script to split a multi-invoice PDF into separate files.
Each invoice is assumed to be on a separate page.
"""
from pathlib import Path
import sys

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    print("pypdf not found, trying PyPDF2...")
    try:
        from PyPDF2 import PdfReader, PdfWriter
    except ImportError:
        print("Error: Neither pypdf nor PyPDF2 is installed.")
        print("Please install one with: pip install pypdf")
        sys.exit(1)


def split_pdf_by_page(input_pdf_path: Path, output_dir: Path, prefix: str = "invoice"):
    """
    Split a PDF file into separate PDFs, one per page.

    Args:
        input_pdf_path: Path to the input PDF file
        output_dir: Directory where split PDFs will be saved
        prefix: Prefix for output filenames (default: "invoice")
    """
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    # Open the input PDF
    reader = PdfReader(input_pdf_path)
    total_pages = len(reader.pages)

    print(f"Processing: {input_pdf_path.name}")
    print(f"Total pages found: {total_pages}")
    print(f"Output directory: {output_dir}")
    print("-" * 50)

    created_files = []

    # Split each page into a separate PDF
    for page_num in range(total_pages):
        # Create a new PDF writer for this page
        writer = PdfWriter()
        writer.add_page(reader.pages[page_num])

        # Generate output filename
        output_filename = f"{prefix}_{page_num + 1:03d}.pdf"
        output_path = output_dir / output_filename

        # Write the page to a new PDF file
        with open(output_path, "wb") as output_file:
            writer.write(output_file)

        created_files.append(output_path)
        print(f"✓ Created: {output_filename}")

    print("-" * 50)
    print(f"Successfully created {len(created_files)} separate PDF files")
    return created_files


def main():
    # Define paths
    input_pdf = Path("/home/dan/projects/boriss/invoices/Boris Invoices001 (005).pdf")
    output_dir = Path("/home/dan/projects/boriss/invoices/split_invoices")

    # Check if input file exists
    if not input_pdf.exists():
        print(f"Error: Input PDF not found at {input_pdf}")
        sys.exit(1)

    # Split the PDF
    split_pdf_by_page(input_pdf, output_dir, prefix="Boris_Invoice")

    print(f"\nAll invoice files saved to: {output_dir}")


if __name__ == "__main__":
    main()
