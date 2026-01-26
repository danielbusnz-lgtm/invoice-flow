#!/bin/bash
# Run all test suites

echo "=================================="
echo "Running Invoice Flow Test Suite"
echo "=================================="
echo ""

cd "$(dirname "$0")/.."

echo "Running Bill Creation Tests..."
pytest tests/test_bill_creation.py -v
echo ""

echo "Running Receipt Creation Tests..."
pytest tests/test_receipt_creation.py -v
echo ""

echo "Running Customer Matching Tests..."
pytest tests/test_customer_matching.py -v
echo ""

echo "Running Vendor Management Tests..."
pytest tests/test_vendor_management.py -v
echo ""

echo "Running Category Mapping Tests..."
pytest tests/test_category_mapping.py -v
echo ""

echo "Running Duplicate Detection Tests..."
pytest tests/test_duplicate_detection.py -v
echo ""

echo "Running Attachment Tests..."
pytest tests/test_attachments.py -v
echo ""

echo "=================================="
echo "All Tests Complete"
echo "=================================="
