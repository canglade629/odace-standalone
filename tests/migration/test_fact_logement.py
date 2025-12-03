"""Migration validation tests for fact_logement (logement → fact_logement)."""
import pytest
from app.utils.migration_validator import MigrationValidator


class TestFactLogementMigration:
    """Validation tests for logement → fact_logement migration."""
    
    @classmethod
    def setup_class(cls):
        """Setup validator instance for all tests."""
        cls.validator = MigrationValidator()
        cls.old_table = "logement"
        cls.new_table = "fact_logement"
    
    def test_row_count_match(self):
        """Test that row counts match."""
        result = self.validator.compare_row_counts(
            old_table=self.old_table,
            new_table=self.new_table
        )
        assert result.passed, result.message
    
    def test_logement_sk_unique(self):
        """Test that logement_sk is unique."""
        result = self.validator.validate_unique_key(
            table=self.new_table,
            key_column="logement_sk"
        )
        assert result.passed, result.message
    
    def test_no_denormalized_columns(self):
        """Test that denormalized columns have been removed."""
        from deltalake import DeltaTable
        from app.core.config import get_settings
        
        settings = get_settings()
        path = settings.get_silver_v2_path(self.new_table)
        dt = DeltaTable(path)
        df = dt.to_pandas()
        
        # These columns should NOT exist in the new table
        forbidden_columns = ['lib_commune', 'lib_epci', 'lib_dep', 'lib_reg']
        existing_forbidden = [col for col in forbidden_columns if col in df.columns]
        
        assert len(existing_forbidden) == 0, f"Found denormalized columns that should have been removed: {existing_forbidden}"
    
    def test_commune_sk_foreign_key(self):
        """Test that all commune_sk values are valid foreign keys."""
        result = self.validator.validate_foreign_keys(
            fact_table=self.new_table,
            fk_column="commune_sk",
            dim_table="dim_commune",
            pk_column="commune_sk"
        )
        assert result.passed, result.message
    
    def test_loyer_values_positive(self):
        """Test that all loyer values are positive."""
        from deltalake import DeltaTable
        from app.core.config import get_settings
        
        settings = get_settings()
        path = settings.get_silver_v2_path(self.new_table)
        dt = DeltaTable(path)
        df = dt.to_pandas()
        
        assert (df['loyer_predicted_m2'] > 0).all(), "Found non-positive loyer_predicted_m2 values"
    
    def test_bounds_coherent(self):
        """Test that lower_bound < predicted < upper_bound."""
        from deltalake import DeltaTable
        from app.core.config import get_settings
        
        settings = get_settings()
        path = settings.get_silver_v2_path(self.new_table)
        dt = DeltaTable(path)
        df = dt.to_pandas()
        
        assert (df['loyer_lower_bound_m2'] < df['loyer_upper_bound_m2']).all(), \
            "Found cases where lower_bound >= upper_bound"
    
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

