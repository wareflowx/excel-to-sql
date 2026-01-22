"""
Integration tests for ConfigGenerator with real Excel files.

Tests use actual Excel fixtures to verify end-to-end configuration generation.
"""

import pytest
import pandas as pd
from pathlib import Path
import json
import tempfile
from excel_to_sql.auto_pilot.generator import ConfigGenerator
from excel_to_sql.auto_pilot.detector import PatternDetector
from excel_to_sql.auto_pilot.scorer import QualityScorer


class TestConfigGeneratorIntegration:
    """Integration tests with real Excel files."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.generator = ConfigGenerator()
        self.detector = PatternDetector()
        self.scorer = QualityScorer()
        self.fixtures_dir = Path(__file__).parent.parent / "fixtures" / "auto_pilot"

    # -------------------------------------------------------------------------
    # Integration tests with produits.xlsx
    # -------------------------------------------------------------------------

    def test_generate_config_for_produits(self) -> None:
        """Test complete configuration generation for produits.xlsx."""
        produits_file = self.fixtures_dir / "produits.xlsx"
        df = pd.read_excel(produits_file)

        # Step 1: Detect patterns
        patterns = self.detector.detect_patterns(df, "produits")

        # Step 2: Score quality
        quality = self.scorer.score_table(df, "produits", primary_key=patterns["primary_key"])

        # Step 3: Generate configuration
        config = self.generator.generate(df, "produits", patterns, quality)

        # Verify structure
        assert config["target_table"] == "produits"
        assert config["primary_key"] == ["no_produit"]
        assert "column_mappings" in config
        assert "metadata" in config

        # Verify metadata includes quality score
        assert config["metadata"]["quality_score"] >= 80
        assert config["metadata"]["primary_key_detected"] is True
        assert config["metadata"]["has_value_mappings"] is True

    def test_produits_config_has_value_mappings(self) -> None:
        """Test that produits config includes French status code mappings."""
        produits_file = self.fixtures_dir / "produits.xlsx"
        df = pd.read_excel(produits_file)

        patterns = self.detector.detect_patterns(df, "produits")
        quality = self.scorer.score_table(df, "produits", primary_key=patterns["primary_key"])
        config = self.generator.generate(df, "produits", patterns, quality)

        # Should have value mapping for 'etat' column
        assert len(config["value_mappings"]) > 0
        etat_mapping = [m for m in config["value_mappings"] if m["column"] == "etat"]
        assert len(etat_mapping) == 1
        assert "ACTIF" in etat_mapping[0]["mappings"]
        assert etat_mapping[0]["mappings"]["ACTIF"] == "active"

    def test_produits_config_column_types(self) -> None:
        """Test that produits config has correct column types."""
        produits_file = self.fixtures_dir / "produits.xlsx"
        df = pd.read_excel(produits_file)

        patterns = self.detector.detect_patterns(df, "produits")
        quality = self.scorer.score_table(df, "produits", primary_key=patterns["primary_key"])
        config = self.generator.generate(df, "produits", patterns, quality)

        # Verify column types
        assert config["column_mappings"]["no_produit"]["type"] == "integer"
        assert config["column_mappings"]["nom_produit"]["type"] == "string"
        assert config["column_mappings"]["etat"]["type"] == "string"
        assert config["column_mappings"]["prix"]["type"] == "float"

    def test_produits_config_validation_rules(self) -> None:
        """Test that produits config includes PK uniqueness validation."""
        produits_file = self.fixtures_dir / "produits.xlsx"
        df = pd.read_excel(produits_file)

        patterns = self.detector.detect_patterns(df, "produits")
        quality = self.scorer.score_table(df, "produits", primary_key=patterns["primary_key"])
        config = self.generator.generate(df, "produits", patterns, quality)

        # Should have unique validation for PK
        unique_rules = [r for r in config["validation_rules"] if r["type"] == "unique"]
        assert len(unique_rules) == 1
        assert unique_rules[0]["column"] == "no_produit"

    # -------------------------------------------------------------------------
    # Integration tests with mouvements.xlsx
    # -------------------------------------------------------------------------

    def test_generate_config_for_mouvements(self) -> None:
        """Test complete configuration generation for mouvements.xlsx."""
        mouvements_file = self.fixtures_dir / "mouvements.xlsx"
        df = pd.read_excel(mouvements_file)

        patterns = self.detector.detect_patterns(df, "mouvements")
        quality = self.scorer.score_table(df, "mouvements", primary_key=patterns["primary_key"])
        config = self.generator.generate(df, "mouvements", patterns, quality)

        # Verify structure
        assert config["target_table"] == "mouvements"
        assert config["primary_key"] == ["oid"]
        assert config["metadata"]["quality_score"] >= 90

    def test_mouvements_config_has_value_mappings(self) -> None:
        """Test that mouvements config includes French movement code mappings."""
        mouvements_file = self.fixtures_dir / "mouvements.xlsx"
        df = pd.read_excel(mouvements_file)

        patterns = self.detector.detect_patterns(df, "mouvements")
        quality = self.scorer.score_table(df, "mouvements", primary_key=patterns["primary_key"])
        config = self.generator.generate(df, "mouvements", patterns, quality)

        # Should have value mapping for 'type' column
        assert len(config["value_mappings"]) > 0
        type_mapping = [m for m in config["value_mappings"] if m["column"] == "type"]
        assert len(type_mapping) == 1
        assert "ENTRÉE" in type_mapping[0]["mappings"]
        assert type_mapping[0]["mappings"]["ENTRÉE"] == "inbound"

    def test_mouvements_config_has_reference_validation(self) -> None:
        """Test that mouvements config includes FK reference validation."""
        mouvements_file = self.fixtures_dir / "mouvements.xlsx"
        df = pd.read_excel(mouvements_file)

        patterns = self.detector.detect_patterns(df, "mouvements")
        quality = self.scorer.score_table(df, "mouvements", primary_key=patterns["primary_key"])
        config = self.generator.generate(df, "mouvements", patterns, quality)

        # Should have reference validation for no_produit FK
        assert len(config["reference_validations"]) > 0
        fk_ref = [r for r in config["reference_validations"] if r["column"] == "no_produit"]
        assert len(fk_ref) == 1
        assert fk_ref[0]["reference_table"] == "produits"

    # -------------------------------------------------------------------------
    # Integration tests with commandes.xlsx
    # -------------------------------------------------------------------------

    def test_generate_config_for_commandes(self) -> None:
        """Test complete configuration generation for commandes.xlsx."""
        commandes_file = self.fixtures_dir / "commandes.xlsx"
        df = pd.read_excel(commandes_file)

        patterns = self.detector.detect_patterns(df, "commandes")
        quality = self.scorer.score_table(df, "commandes", primary_key=patterns["primary_key"])
        config = self.generator.generate(df, "commandes", patterns, quality)

        # Verify structure
        assert config["target_table"] == "commandes"
        assert config["primary_key"] == ["commande"]
        assert config["metadata"]["quality_score"] >= 95  # Perfect quality

    def test_commandes_config_has_calculated_columns(self) -> None:
        """Test that commandes config includes calculated column for split fields."""
        commandes_file = self.fixtures_dir / "commandes.xlsx"
        df = pd.read_excel(commandes_file)

        patterns = self.detector.detect_patterns(df, "commandes")
        quality = self.scorer.score_table(df, "commandes", primary_key=patterns["primary_key"])
        config = self.generator.generate(df, "commandes", patterns, quality)

        # Should have calculated column for split status fields
        assert len(config["calculated_columns"]) > 0
        calc_col = config["calculated_columns"][0]
        assert "COALESCE" in calc_col["expression"]
        assert calc_col["type"] == "string"

    def test_commandes_config_metadata(self) -> None:
        """Test that commandes config metadata reflects perfect quality."""
        commandes_file = self.fixtures_dir / "commandes.xlsx"
        df = pd.read_excel(commandes_file)

        patterns = self.detector.detect_patterns(df, "commandes")
        quality = self.scorer.score_table(df, "commandes", primary_key=patterns["primary_key"])
        config = self.generator.generate(df, "commandes", patterns, quality)

        # Verify metadata
        assert config["metadata"]["row_count"] == 20
        assert config["metadata"]["quality_grade"] == "A+"
        assert config["metadata"]["primary_key_detected"] is True
        assert config["metadata"]["has_split_fields"] is True

    # -------------------------------------------------------------------------
    # End-to-end workflow tests
    # -------------------------------------------------------------------------

    def test_end_to_end_workflow_all_fixtures(self) -> None:
        """Test complete workflow: detect patterns -> score quality -> generate config."""
        all_configs = {}

        for fixture_name in ["produits.xlsx", "mouvements.xlsx", "commandes.xlsx"]:
            fixture_file = self.fixtures_dir / fixture_name
            df = pd.read_excel(fixture_file)
            table_name = fixture_name.replace(".xlsx", "")

            # Step 1: Detect patterns
            patterns = self.detector.detect_patterns(df, table_name)

            # Step 2: Score quality
            quality = self.scorer.score_table(df, table_name, primary_key=patterns["primary_key"])

            # Step 3: Generate configuration
            config = self.generator.generate(df, table_name, patterns, quality)

            all_configs[table_name] = config

            # Verify each config has required fields
            assert "target_table" in config
            assert "primary_key" in config
            assert "column_mappings" in config
            assert "metadata" in config

        # Verify specific expectations per table
        assert all_configs["produits"]["target_table"] == "produits"
        assert all_configs["mouvements"]["target_table"] == "mouvements"
        assert all_configs["commandes"]["target_table"] == "commandes"

        # Verify all have primary keys detected
        assert all_configs["produits"]["primary_key"] == ["no_produit"]
        assert all_configs["mouvements"]["primary_key"] == ["oid"]
        assert all_configs["commandes"]["primary_key"] == ["commande"]

    def test_save_and_load_config(self) -> None:
        """Test saving and loading configuration file."""
        produits_file = self.fixtures_dir / "produits.xlsx"
        df = pd.read_excel(produits_file)

        patterns = self.detector.detect_patterns(df, "produits")
        quality = self.scorer.score_table(df, "produits", primary_key=patterns["primary_key"])
        config = self.generator.generate(df, "produits", patterns, quality)

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / ".excel-to-sql" / "mappings.json"

            # Save config
            self.generator.save(config, filepath)

            # Verify file exists
            assert filepath.exists()

            # Load config
            loaded_config = self.generator.load(filepath)

            # Verify structure
            assert "mappings" in loaded_config
            assert "produits" in loaded_config["mappings"]

            # Verify content
            produits_config = loaded_config["mappings"]["produits"]
            assert produits_config["target_table"] == "produits"
            assert produits_config["primary_key"] == ["no_produit"]

    def test_generate_multiple_configs_to_single_file(self) -> None:
        """Test that each save operation overwrites the file (current behavior)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / ".excel-to-sql" / "mappings.json"

            configs = []
            for fixture_name in ["produits.xlsx", "mouvements.xlsx", "commandes.xlsx"]:
                fixture_file = self.fixtures_dir / fixture_name
                df = pd.read_excel(fixture_file)
                table_name = fixture_name.replace(".xlsx", "")

                patterns = self.detector.detect_patterns(df, table_name)
                quality = self.scorer.score_table(df, table_name, primary_key=patterns["primary_key"])
                config = self.generator.generate(df, table_name, patterns, quality)
                configs.append(config)

                # Save each config (last one overwrites)
                self.generator.save(config, filepath)

            # Load and verify only the last config is present
            loaded = self.generator.load(filepath)
            assert "mappings" in loaded
            # The last saved config (commandes) should be present
            assert "commandes" in loaded["mappings"]
            assert loaded["mappings"]["commandes"]["target_table"] == "commandes"

    # -------------------------------------------------------------------------
    # Compatibility tests with existing mapping models
    # -------------------------------------------------------------------------

    def test_config_compatibility_with_mapping_models(self) -> None:
        """Test that generated config is compatible with mapping models."""
        from excel_to_sql.models.mapping import TypeMapping, Mappings

        produits_file = self.fixtures_dir / "produits.xlsx"
        df = pd.read_excel(produits_file)

        patterns = self.detector.detect_patterns(df, "produits")
        quality = self.scorer.score_table(df, "produits", primary_key=patterns["primary_key"])
        config = self.generator.generate(df, "produits", patterns, quality)

        # Should be able to validate with Pydantic model
        try:
            type_mapping = TypeMapping(**config)
            assert type_mapping.target_table == "produits"
            assert type_mapping.primary_key == ["no_produit"]
        except Exception as e:
            pytest.fail(f"Config validation failed: {e}")

    def test_full_mappings_structure(self) -> None:
        """Test that saved config has correct Mappings structure."""
        from excel_to_sql.models.mapping import Mappings

        produits_file = self.fixtures_dir / "produits.xlsx"
        df = pd.read_excel(produits_file)

        patterns = self.detector.detect_patterns(df, "produits")
        quality = self.scorer.score_table(df, "produits", primary_key=patterns["primary_key"])
        config = self.generator.generate(df, "produits", patterns, quality)

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / ".excel-to-sql" / "mappings.json"
            self.generator.save(config, filepath)

            # Load and validate with Mappings model
            loaded = self.generator.load(filepath)

            try:
                mappings = Mappings(**loaded)
                assert "produits" in mappings.mappings
            except Exception as e:
                pytest.fail(f"Mappings validation failed: {e}")

    # -------------------------------------------------------------------------
    # Performance tests
    # -------------------------------------------------------------------------

    def test_generation_performance(self) -> None:
        """Test that configuration generation completes quickly."""
        import time

        mouvements_file = self.fixtures_dir / "mouvements.xlsx"
        df = pd.read_excel(mouvements_file)

        patterns = self.detector.detect_patterns(df, "mouvements")
        quality = self.scorer.score_table(df, "mouvements", primary_key=patterns["primary_key"])

        start_time = time.time()
        config = self.generator.generate(df, "mouvements", patterns, quality)
        end_time = time.time()

        elapsed = end_time - start_time

        # Should complete in less than 0.5 seconds
        assert elapsed < 0.5, f"Generation took {elapsed:.2f}s, expected < 0.5s"

        # Should still produce valid results
        assert config["target_table"] == "mouvements"
