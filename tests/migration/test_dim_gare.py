"""Migration validation tests for dim_gare (gares → dim_gare)."""
import pytest
from app.utils.migration_validator import MigrationValidator


class TestDimGareMigration:
    """Validation tests for gares → dim_gare migration."""
    
    @classmethod
    def setup_class(cls):
        """Setup validator instance for all tests."""
        cls.validator = MigrationValidator()
        cls.old_table = "gares"
        cls.new_table = "dim_gare"
    
    def test_row_count_match(self):
        """Test that row counts match."""
        result = self.validator.compare_row_counts(
            old_table=self.old_table,
            new_table=self.new_table
        )
        assert result.passed, result.message
    
    def test_gare_sk_unique(self):
        """Test that gare_sk is unique."""
        result = self.validator.validate_unique_key(
            table=self.new_table,
            key_column="gare_sk"
        )
        assert result.passed, result.message
    
    def test_metadata_columns_present(self):
        """Test that all 4 metadata columns exist."""
        result = self.validator.validate_metadata_columns(
            table=self.new_table
        )
        assert result.passed, result.message
    
    @classmethod
    def teardown_class(cls):
        """Print validation report."""
        cls.validator.print_report()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

