"""Integration tests for Silver V2 migration - cross-table validations."""
import pytest
from app.utils.migration_validator import MigrationValidator
from deltalake import DeltaTable
from app.core.config import get_settings
import logging

logger = logging.getLogger(__name__)


class TestSilverV2Integration:
    """Integration tests validating referential integrity across all V2 tables."""
    
    @classmethod
    def setup_class(cls):
        """Setup validator and settings."""
        cls.validator = MigrationValidator()
        cls.settings = get_settings()
    
    def test_all_fact_tables_reference_dim_commune(self):
        """Test that all fact tables with commune_sk have valid foreign keys."""
        fact_tables_with_commune = [
            ('fact_logement', 'commune_sk'),
            ('fact_zone_attraction', 'commune_sk'),
        ]
        
        for table, fk_column in fact_tables_with_commune:
            result = self.validator.validate_foreign_keys(
                fact_table=table,
                fk_column=fk_column,
                dim_table="dim_commune",
                pk_column="commune_sk"
            )
            assert result.passed, f"{table}.{fk_column} has orphaned foreign keys: {result.message}"
    
    def test_fact_zone_attraction_both_fks_valid(self):
        """Test that fact_zone_attraction has valid FKs for both commune and pole."""
        # Test commune_sk
        result1 = self.validator.validate_foreign_keys(
            fact_table="fact_zone_attraction",
            fk_column="commune_sk",
            dim_table="dim_commune",
            pk_column="commune_sk"
        )
        assert result1.passed, f"commune_sk has orphaned FKs: {result1.message}"
        
        # Test commune_pole_sk
        result2 = self.validator.validate_foreign_keys(
            fact_table="fact_zone_attraction",
            fk_column="commune_pole_sk",
            dim_table="dim_commune",
            pk_column="commune_sk"
        )
        assert result2.passed, f"commune_pole_sk has orphaned FKs: {result2.message}"
    
    def test_fact_siae_poste_references_dim_siae_structure(self):
        """Test that fact_siae_poste has valid FK to dim_siae_structure."""
        result = self.validator.validate_foreign_keys(
            fact_table="fact_siae_poste",
            fk_column="siae_structure_sk",
            dim_table="dim_siae_structure",
            pk_column="siae_structure_sk"
        )
        assert result.passed, f"siae_structure_sk has orphaned FKs: {result.message}"
    
    def test_all_tables_have_metadata_columns(self):
        """Test that all V2 tables have the 4 required metadata columns."""
        all_tables = [
            'dim_commune',
            'dim_accueillant',
            'dim_gare',
            'dim_ligne',
            'dim_siae_structure',
            'fact_logement',
            'fact_zone_attraction',
            'fact_siae_poste'
        ]
        
        for table in all_tables:
            result = self.validator.validate_metadata_columns(table)
            assert result.passed, f"{table} missing metadata columns: {result.message}"
    
    def test_all_surrogate_keys_unique(self):
        """Test that all surrogate keys (_sk) are unique in their tables."""
        tables_and_keys = [
            ('dim_commune', 'commune_sk'),
            ('dim_accueillant', 'accueillant_sk'),
            ('dim_gare', 'gare_sk'),
            ('dim_ligne', 'ligne_sk'),
            ('dim_siae_structure', 'siae_structure_sk'),
            ('fact_logement', 'logement_sk'),
            ('fact_zone_attraction', 'zone_attraction_sk'),
            ('fact_siae_poste', 'siae_poste_sk')
        ]
        
        for table, sk_column in tables_and_keys:
            result = self.validator.validate_unique_key(table, sk_column)
            assert result.passed, f"{table}.{sk_column} is not unique: {result.message}"
    
    def test_no_unexpected_nulls_in_primary_keys(self):
        """Test that no primary keys (SK columns) contain NULLs."""
        tables_and_keys = [
            ('dim_commune', ['commune_sk', 'commune_code']),
            ('dim_accueillant', ['accueillant_sk']),
            ('dim_gare', ['gare_sk', 'code_uic']),
            ('dim_ligne', ['ligne_sk', 'ligne_code']),
            ('dim_siae_structure', ['siae_structure_sk', 'siret']),
            ('fact_logement', ['logement_sk', 'commune_sk']),
            ('fact_zone_attraction', ['zone_attraction_sk', 'commune_sk', 'commune_pole_sk']),
            ('fact_siae_poste', ['siae_poste_sk', 'siae_structure_sk'])
        ]
        
        for table, columns in tables_and_keys:
            result = self.validator.validate_no_nulls(table, columns)
            assert result.passed, f"{table} has NULLs in required columns: {result.message}"
    
    def test_total_row_counts_preserved(self):
        """Test that total row counts are preserved across migration."""
        table_pairs = [
            ('geo', 'dim_commune'),
            ('accueillants', 'dim_accueillant'),
            ('gares', 'dim_gare'),
            ('lignes', 'dim_ligne'),
            ('siae_structures', 'dim_siae_structure'),
            ('logement', 'fact_logement'),
            ('zones_attraction', 'fact_zone_attraction'),
            ('siae_postes', 'fact_siae_poste')
        ]
        
        for old_table, new_table in table_pairs:
            result = self.validator.compare_row_counts(old_table, new_table)
            # Allow some minor differences due to filtering
            if not result.passed:
                diff_ratio = abs(result.details['diff']) / result.details['old_count']
                assert diff_ratio < 0.05, \
                    f"{old_table} → {new_table}: Row count difference too large: {result.message}"
    
    @classmethod
    def teardown_class(cls):
        """Print comprehensive validation report."""
        print("\n" + "="*80)
        print("INTEGRATION TEST VALIDATION REPORT")
        print("="*80)
        cls.validator.print_report()
        
        # Generate and save report
        report = cls.validator.generate_migration_report()
        print(f"\n\nSummary: {report['summary']}")
        
        if report['failed_validations']:
            print(f"\n⚠️  Found {len(report['failed_validations'])} failed validations")
        else:
            print("\n✅ ALL INTEGRATION TESTS PASSED!")


if __name__ == "__main__":
    """Run tests manually and print report."""
    pytest.main([__file__, "-v", "-s"])

