"""Template for migration validation tests.

This template provides a standard structure for validating table migrations.
Copy this file and customize for each table migration.
"""
import pytest
from app.utils.migration_validator import MigrationValidator


class TestTableMigration:
    """Template for table migration validation tests."""
    
    @classmethod
    def setup_class(cls):
        """Setup validator instance for all tests."""
        cls.validator = MigrationValidator()
        cls.old_table = "OLD_TABLE_NAME"  # e.g., "geo"
        cls.new_table = "NEW_TABLE_NAME"  # e.g., "dim_commune"
        cls.primary_key = "PRIMARY_KEY_COLUMN"  # e.g., "commune_sk"
    
    def test_row_count_match(self):
        """Test that row counts match between old and new tables."""
        result = self.validator.compare_row_counts(
            old_table=self.old_table,
            new_table=self.new_table
        )
        assert result.passed, result.message
    
    def test_unique_key_values(self):
        """Test that natural key values are preserved."""
        result = self.validator.compare_unique_values(
            old_table=self.old_table,
            old_column="OLD_KEY_COLUMN",  # e.g., "CODGEO"
            new_table=self.new_table,
            new_column="NEW_KEY_COLUMN"  # e.g., "commune_code"
        )
        assert result.passed, result.message
    
    def test_primary_key_unique(self):
        """Test that primary key (surrogate key) is unique."""
        result = self.validator.validate_unique_key(
            table=self.new_table,
            key_column=self.primary_key
        )
        assert result.passed, result.message
    
    def test_no_nulls_in_required_columns(self):
        """Test that required columns have no NULL values."""
        required_columns = [
            self.primary_key,
            # Add other required columns
        ]
        result = self.validator.validate_no_nulls(
            table=self.new_table,
            columns=required_columns
        )
        assert result.passed, result.message
    
    def test_metadata_columns_present(self):
        """Test that all 4 metadata columns exist and are populated."""
        result = self.validator.validate_metadata_columns(
            table=self.new_table
        )
        assert result.passed, result.message
    
    # Add custom validations specific to the table
    # def test_custom_validation(self):
    #     """Test specific business rules for this table."""
    #     pass
    
    @classmethod
    def teardown_class(cls):
        """Print validation report after all tests."""
        print("\n" + "="*80)
        print(f"MIGRATION VALIDATION REPORT: {cls.new_table}")
        print("="*80)
        cls.validator.print_report()

