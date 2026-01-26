"""Test suite for expense category to account mapping"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from services.quickbooks_service import QuickbooksInvoiceService


class TestCategoryMapping:
    """Test expense category to QuickBooks account mapping"""

    @pytest.fixture
    def qb_service(self):
        """Initialize QuickBooks service"""
        return QuickbooksInvoiceService()

    def test_exact_category_match(self, qb_service):
        """Test exact category matches"""
        test_cases = {
            'materials': '63',
            'labor': '59',
            'equipment': '29',
            'fuel': '56',
            'supplies': '20'
        }
        
        for category, expected_account in test_cases.items():
            account_id = qb_service.match_category_to_account(category)
            assert account_id == expected_account
            print(f"✓ {category} → Account {account_id}")

    def test_case_insensitive_matching(self, qb_service):
        """Test that category matching is case-insensitive"""
        test_cases = ['MATERIALS', 'Materials', 'mAtErIaLs']
        
        for category in test_cases:
            account_id = qb_service.match_category_to_account(category)
            assert account_id == '63'  # Job Materials account
        
        print("✓ Case-insensitive matching works")

    def test_partial_category_match(self, qb_service):
        """Test partial string matching in categories"""
        # "plants and soil" should match "plants" → 66
        account_id = qb_service.match_category_to_account("plants and soil")
        assert account_id == '66'
        print("✓ Partial match: 'plants and soil' → Account 66")

    def test_unknown_category_default(self, qb_service):
        """Test that unknown categories return default account"""
        import os
        default_account = os.getenv('QB_EXPENSE_ACCOUNT_ID', '31')
        
        account_id = qb_service.match_category_to_account("random unknown category")
        assert account_id == default_account
        print(f"✓ Unknown category → Default Account {default_account}")

    def test_empty_category_default(self, qb_service):
        """Test that empty category returns default account"""
        import os
        default_account = os.getenv('QB_EXPENSE_ACCOUNT_ID', '31')
        
        account_id = qb_service.match_category_to_account("")
        assert account_id == default_account
        print(f"✓ Empty category → Default Account {default_account}")

    def test_none_category_default(self, qb_service):
        """Test that None category returns default account"""
        import os
        default_account = os.getenv('QB_EXPENSE_ACCOUNT_ID', '31')
        
        account_id = qb_service.match_category_to_account(None)
        assert account_id == default_account
        print(f"✓ None category → Default Account {default_account}")

    def test_whitespace_handling(self, qb_service):
        """Test that categories with whitespace are handled correctly"""
        account_id = qb_service.match_category_to_account("  materials  ")
        assert account_id == '63'
        print("✓ Whitespace trimming works")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
