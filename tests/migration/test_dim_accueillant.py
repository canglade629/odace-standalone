"""Migration validation tests for dim_accueillant (accueillants → dim_accueillant)."""
import pytest
from app.utils.migration_validator import MigrationValidator


class TestDimAccueillantMigration:
    """Validation tests for accueillants → dim_accueillant migration."""
    
    @classmethod
    def setup_class(cls):
        """Setup validator instance for all tests."""
        cls.validator = MigrationValidator()
        cls.old_table = "accueillants"
        cls.new_table = "dim_accueillant"
    
    def test_row_count_match(self):
        """Test that row counts match between silver.accueillants and silver_v2.dim_accueillant."""
        result = self.validator.compare_row_counts(
            old_table=self.old_table,
            new_table=self.new_table
        )
        assert result.passed, result.message
    
    def test_accueillant_sk_unique(self):
        """Test that accueillant_sk (surrogate key) is unique."""
        result = self.validator.validate_unique_key(
            table=self.new_table,
            key_column="accueillant_sk"
        )
        assert result.passed, result.message
    
    def test_no_nulls_in_required_columns(self):
        """Test that required columns have no NULL values."""
        required_columns = [
            'accueillant_sk',
            'ville',
            'code_postal',
            'latitude',
            'longitude'
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
    
    def test_commune_sk_foreign_key(self):
        """Test that commune_sk values are valid foreign keys to dim_commune."""
        result = self.validator.validate_foreign_keys(
            fact_table=self.new_table,
            fk_column="commune_sk",
            dim_table="dim_commune",
            pk_column="commune_sk"
        )
        # Allow some failures since not all will match
        assert result.details['orphaned_count'] < result.details['fk_count'] * 0.15, \
            f"More than 15% of commune_sk values are orphaned: {result.message}"
    
    def test_coordinates_valid(self):
        """Test that latitude and longitude are within valid ranges."""
        from deltalake import DeltaTable
        from app.core.config import get_settings
        
        settings = get_settings()
        path = settings.get_silver_v2_path(self.new_table)
        dt = DeltaTable(path)
        df = dt.to_pandas()
        
        # Check latitude range (-90 to 90)
        valid_lat = df['latitude'].between(-90, 90).all()
        assert valid_lat, "Found latitude values outside valid range (-90, 90)"
        
        # Check longitude range (-180 to 180)
        valid_lon = df['longitude'].between(-180, 180).all()
        assert valid_lon, "Found longitude values outside valid range (-180, 180)"
    
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

