"""Migration validation tests for dim_commune (geo → dim_commune)."""
import pytest
from app.utils.migration_validator import MigrationValidator


class TestDimCommuneMigration:
    """Validation tests for geo → dim_commune migration."""
    
    @classmethod
    def setup_class(cls):
        """Setup validator instance for all tests."""
        cls.validator = MigrationValidator()
        cls.old_table = "geo"
        cls.new_table = "dim_commune"
    
    def test_row_count_match(self):
        """Test that row counts match between silver.geo and silver_v2.dim_commune."""
        result = self.validator.compare_row_counts(
            old_table=self.old_table,
            new_table=self.new_table
        )
        assert result.passed, result.message
    
    def test_insee_codes_preserved(self):
        """Test that all INSEE codes (CODGEO) are preserved as commune_code."""
        result = self.validator.compare_unique_values(
            old_table=self.old_table,
            old_column="CODGEO",
            new_table=self.new_table,
            new_column="commune_code"
        )
        assert result.passed, result.message
    
    def test_commune_labels_preserved(self):
        """Test that all commune names (LIBGEO) are preserved as commune_label."""
        result = self.validator.compare_unique_values(
            old_table=self.old_table,
            old_column="LIBGEO",
            new_table=self.new_table,
            new_column="commune_label"
        )
        assert result.passed, result.message
    
    def test_commune_sk_unique(self):
        """Test that commune_sk (surrogate key) is unique."""
        result = self.validator.validate_unique_key(
            table=self.new_table,
            key_column="commune_sk"
        )
        assert result.passed, result.message
    
    def test_commune_code_unique(self):
        """Test that commune_code (INSEE code) is unique."""
        result = self.validator.validate_unique_key(
            table=self.new_table,
            key_column="commune_code"
        )
        assert result.passed, result.message
    
    def test_no_nulls_in_required_columns(self):
        """Test that required columns have no NULL values."""
        required_columns = [
            'commune_sk',
            'commune_code',
            'commune_label',
            'departement_code'
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
    
    def test_departement_code_format(self):
        """Test that departement_code is properly extracted (2 or 3 chars)."""
        from app.utils.migration_validator import MigrationValidator
        from deltalake import DeltaTable
        from app.core.config import get_settings
        
        settings = get_settings()
        path = settings.get_silver_v2_path(self.new_table)
        dt = DeltaTable(path)
        df = dt.to_pandas()
        
        # Check department code length
        dept_lengths = df['departement_code'].str.len()
        valid_lengths = dept_lengths.isin([2, 3])
        
        assert valid_lengths.all(), f"Found invalid department code lengths: {dept_lengths[~valid_lengths].unique()}"
    
    def test_region_code_populated(self):
        """Test that region_code is populated for most communes."""
        from deltalake import DeltaTable
        from app.core.config import get_settings
        
        settings = get_settings()
        path = settings.get_silver_v2_path(self.new_table)
        dt = DeltaTable(path)
        df = dt.to_pandas()
        
        # At least 95% of communes should have a region code
        non_null_ratio = df['region_code'].notna().sum() / len(df)
        
        assert non_null_ratio >= 0.95, f"Only {non_null_ratio*100:.1f}% of communes have region_code (expected ≥95%)"
    
    @classmethod
    def teardown_class(cls):
        """Print validation report after all tests."""
        print("\n" + "="*80)
        print(f"MIGRATION VALIDATION REPORT: {cls.new_table}")
        print("="*80)
        cls.validator.print_report()


if __name__ == "__main__":
    """Run tests manually and print report."""
    pytest.main([__file__, "-v", "-s"])

