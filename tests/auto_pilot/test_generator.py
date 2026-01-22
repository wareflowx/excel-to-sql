"""
Unit tests for ConfigGenerator class.

Tests cover all generation methods with various edge cases and scenarios.
"""

import pytest
import pandas as pd
from pathlib import Path
import json
import tempfile
from excel_to_sql.auto_pilot.generator import ConfigGenerator


class TestConfigGenerator:
    """Test suite for ConfigGenerator class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.generator = ConfigGenerator()

    # -------------------------------------------------------------------------
    # Tests for generate (main orchestration method)
    # -------------------------------------------------------------------------

    def test_generate_complete_config(self) -> None:
        """Test complete configuration generation."""
        df = pd.DataFrame({
            "no_produit": [1, 2, 3],
            "nom": ["A", "B", "C"],
        })

        patterns = {
            "primary_key": "no_produit",
            "value_mappings": {},
            "foreign_keys": [],
            "split_fields": None,
            "confidence": 0.95,
        }

        quality = {
            "score": 95,
            "grade": "A+",
            "breakdown": {"completeness": 100, "uniqueness": 100, "validity": 100, "consistency": 100},
            "issues": [],
        }

        config = self.generator.generate(df, "produits", patterns, quality)

        assert config["target_table"] == "produits"
        assert config["primary_key"] == ["no_produit"]
        assert "column_mappings" in config
        assert "value_mappings" in config
        assert "calculated_columns" in config
        assert "validation_rules" in config
        assert "reference_validations" in config
        assert "metadata" in config

    def test_generate_with_value_mappings(self) -> None:
        """Test configuration generation with value mappings."""
        df = pd.DataFrame({
            "no_produit": [1, 2, 3],
            "etat": ["ACTIF", "INACTIF", "ACTIF"],
        })

        patterns = {
            "primary_key": "no_produit",
            "value_mappings": {
                "etat": {"ACTIF": "active", "INACTIF": "inactive"}
            },
            "foreign_keys": [],
            "split_fields": None,
            "confidence": 0.95,
        }

        quality = {
            "score": 95,
            "grade": "A+",
            "breakdown": {},
            "issues": [],
        }

        config = self.generator.generate(df, "produits", patterns, quality)

        assert len(config["value_mappings"]) == 1
        assert config["value_mappings"][0]["column"] == "etat"
        assert config["value_mappings"][0]["mappings"]["ACTIF"] == "active"

    def test_generate_with_split_fields(self) -> None:
        """Test configuration generation with split fields."""
        df = pd.DataFrame({
            "commande": ["C001", "C002", "C003"],
            "etat_superieur": ["A", None, None],
            "etat_inferieur": [None, "B", None],
            "etat": [None, None, "C"],
        })

        patterns = {
            "primary_key": "commande",
            "value_mappings": {},
            "foreign_keys": [],
            "split_fields": ["etat_superieur", "etat_inferieur", "etat"],
            "confidence": 0.90,
        }

        quality = {
            "score": 90,
            "grade": "A",
            "breakdown": {},
            "issues": [],
        }

        config = self.generator.generate(df, "commandes", patterns, quality)

        assert len(config["calculated_columns"]) == 1
        assert "COALESCE" in config["calculated_columns"][0]["expression"]

    def test_generate_with_foreign_keys(self) -> None:
        """Test configuration generation with foreign keys."""
        df = pd.DataFrame({
            "oid": [1, 2, 3],
            "no_produit": [101, 102, 103],
        })

        patterns = {
            "primary_key": "oid",
            "value_mappings": {},
            "foreign_keys": [
                {"column": "no_produit", "ref_table": "produits", "ref_column": "no_produit", "coverage": 100}
            ],
            "split_fields": None,
            "confidence": 0.95,
        }

        quality = {
            "score": 95,
            "grade": "A+",
            "breakdown": {},
            "issues": [],
        }

        config = self.generator.generate(df, "mouvements", patterns, quality)

        assert len(config["reference_validations"]) == 1
        assert config["reference_validations"][0]["column"] == "no_produit"
        assert config["reference_validations"][0]["reference_table"] == "produits"

    def test_generate_without_primary_key(self) -> None:
        """Test configuration generation without detected primary key."""
        df = pd.DataFrame({
            "col1": [1, 2, 3],
            "col2": ["A", "B", "C"],
        })

        patterns = {
            "primary_key": None,
            "value_mappings": {},
            "foreign_keys": [],
            "split_fields": None,
            "confidence": 0.50,
        }

        quality = {
            "score": 70,
            "grade": "C",
            "breakdown": {},
            "issues": ["No clear primary key detected"],
        }

        config = self.generator.generate(df, "test", patterns, quality)

        assert config["primary_key"] == []
        assert config["metadata"]["primary_key_detected"] is False

    # -------------------------------------------------------------------------
    # Tests for _generate_column_mappings
    # -------------------------------------------------------------------------

    def test_generate_column_mappings_basic(self) -> None:
        """Test column mapping generation with basic types."""
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
            "price": [10.5, 20.0, 30.75],
            "active": [True, False, True],
        })

        mappings = self.generator._generate_column_mappings(df)

        assert "id" in mappings
        assert "name" in mappings
        assert "price" in mappings
        assert "active" in mappings

        assert mappings["id"]["type"] == "integer"
        assert mappings["name"]["type"] == "string"
        assert mappings["price"]["type"] == "float"
        assert mappings["active"]["type"] == "boolean"

    def test_generate_column_mappings_with_datetime(self) -> None:
        """Test column mapping generation with datetime columns."""
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "created_at": pd.to_datetime(["2024-01-01", "2024-02-01", "2024-03-01"]),
        })

        mappings = self.generator._generate_column_mappings(df)

        assert mappings["created_at"]["type"] == "date"

    def test_generate_column_mappings_with_numeric_column_names(self) -> None:
        """Test column mapping generation with numeric column names."""
        df = pd.DataFrame({
            1: [10, 20, 30],
            2: ["A", "B", "C"],
        })

        mappings = self.generator._generate_column_mappings(df)

        # Numeric column names should be converted to strings
        assert "1" in mappings or 1 in mappings
        assert "2" in mappings or 2 in mappings

    # -------------------------------------------------------------------------
    # Tests for _infer_sql_type
    # -------------------------------------------------------------------------

    def test_infer_sql_type_integer(self) -> None:
        """Test SQL type inference for integers."""
        series = pd.Series([1, 2, 3, 4, 5])
        assert self.generator._infer_sql_type(series) == "integer"

    def test_infer_sql_type_float(self) -> None:
        """Test SQL type inference for floats."""
        series = pd.Series([1.5, 2.5, 3.5])
        assert self.generator._infer_sql_type(series) == "float"

    def test_infer_sql_type_boolean(self) -> None:
        """Test SQL type inference for booleans."""
        series = pd.Series([True, False, True])
        assert self.generator._infer_sql_type(series) == "boolean"

    def test_infer_sql_type_string(self) -> None:
        """Test SQL type inference for strings."""
        series = pd.Series(["A", "B", "C"])
        assert self.generator._infer_sql_type(series) == "string"

    def test_infer_sql_type_datetime(self) -> None:
        """Test SQL type inference for datetime."""
        series = pd.to_datetime(["2024-01-01", "2024-02-01", "2024-03-01"])
        assert self.generator._infer_sql_type(series) == "date"

    def test_infer_sql_type_datetime_string(self) -> None:
        """Test SQL type inference for datetime strings."""
        series = pd.Series(["2024-01-01", "2024-02-01", "2024-03-01"])
        assert self.generator._infer_sql_type(series) == "date"

    def test_infer_sql_type_numeric_string(self) -> None:
        """Test SQL type inference for numeric strings."""
        series = pd.Series(["1.5", "2.5", "3.5"])
        assert self.generator._infer_sql_type(series) == "float"

    def test_infer_sql_type_mixed_string(self) -> None:
        """Test SQL type inference for mixed content strings."""
        series = pd.Series(["ABC", "123", "XYZ"])
        assert self.generator._infer_sql_type(series) == "string"

    # -------------------------------------------------------------------------
    # Tests for _generate_value_mappings
    # -------------------------------------------------------------------------

    def test_generate_value_mappings_basic(self) -> None:
        """Test value mapping generation with French codes."""
        patterns = {
            "value_mappings": {
                "etat": {"ACTIF": "active", "INACTIF": "inactive"},
                "type": {"ENTRÉE": "inbound", "SORTIE": "outbound"}
            }
        }

        mappings = self.generator._generate_value_mappings(patterns)

        assert len(mappings) == 2
        assert mappings[0]["column"] == "etat"
        assert mappings[1]["column"] == "type"

    def test_generate_value_mappings_empty(self) -> None:
        """Test value mapping generation with no mappings."""
        patterns = {"value_mappings": {}}
        mappings = self.generator._generate_value_mappings(patterns)
        assert len(mappings) == 0

    def test_generate_value_mappings_no_key(self) -> None:
        """Test value mapping generation when key doesn't exist."""
        patterns = {}
        mappings = self.generator._generate_value_mappings(patterns)
        assert len(mappings) == 0

    # -------------------------------------------------------------------------
    # Tests for _generate_calculated_columns
    # -------------------------------------------------------------------------

    def test_generate_calculated_columns_split_fields(self) -> None:
        """Test calculated column generation for split fields."""
        patterns = {
            "split_fields": ["etat_superieur", "etat_inferieur", "etat"]
        }

        calc_cols = self.generator._generate_calculated_columns(patterns)

        assert len(calc_cols) == 1
        assert "COALESCE" in calc_cols[0]["expression"]
        assert calc_cols[0]["type"] == "string"

    def test_generate_calculated_columns_no_split_fields(self) -> None:
        """Test calculated column generation with no split fields."""
        patterns = {"split_fields": None}
        calc_cols = self.generator._generate_calculated_columns(patterns)
        assert len(calc_cols) == 0

    def test_generate_calculated_columns_single_field(self) -> None:
        """Test calculated column generation with single split field."""
        patterns = {"split_fields": ["etat"]}
        calc_cols = self.generator._generate_calculated_columns(patterns)
        # Should not create COALESCE for single field
        assert len(calc_cols) == 0

    def test_guess_combined_column_name(self) -> None:
        """Test guessing combined column name from split fields."""
        split_fields = ["etat_superieur", "etat_inferieur", "etat"]
        name = self.generator._guess_combined_column_name(split_fields)
        assert name == "etat"

    def test_guess_combined_column_name_no_prefix(self) -> None:
        """Test guessing combined name when no common prefix exists."""
        split_fields = ["status_a", "status_b", "status_c"]
        name = self.generator._guess_combined_column_name(split_fields)
        # Should return the shortest name
        assert name == "status_a"

    # -------------------------------------------------------------------------
    # Tests for _generate_validation_rules
    # -------------------------------------------------------------------------

    def test_generate_validation_rules_with_pk(self) -> None:
        """Test validation rule generation with primary key."""
        df = pd.DataFrame({
            "no_produit": [1, 2, 3],
            "nom": ["A", "B", "C"],
        })

        patterns = {"primary_key": "no_produit"}

        rules = self.generator._generate_validation_rules(df, patterns)

        assert len(rules) >= 1
        # Should have unique rule for PK
        unique_rules = [r for r in rules if r["type"] == "unique"]
        assert len(unique_rules) == 1
        assert unique_rules[0]["column"] == "no_produit"

    def test_generate_validation_rules_required_fields(self) -> None:
        """Test validation rule generation for required fields."""
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "name": ["A", "B", "C"],  # No nulls
            "optional": ["X", None, "Z"],  # Has nulls
        })

        patterns = {"primary_key": "id"}

        rules = self.generator._generate_validation_rules(df, patterns)

        # Should have required rule for 'name' (no nulls, not PK)
        required_rules = [r for r in rules if r["type"] == "required"]
        assert len(required_rules) >= 1
        assert any(r["column"] == "name" for r in required_rules)

    def test_generate_validation_rules_no_pk(self) -> None:
        """Test validation rule generation without primary key."""
        df = pd.DataFrame({
            "col1": [1, 2, 3],
            "col2": ["A", "B", "C"],
        })

        patterns = {"primary_key": None}

        rules = self.generator._generate_validation_rules(df, patterns)

        # Should not have unique rule
        unique_rules = [r for r in rules if r["type"] == "unique"]
        assert len(unique_rules) == 0

    # -------------------------------------------------------------------------
    # Tests for _generate_reference_validations
    # -------------------------------------------------------------------------

    def test_generate_reference_validations_with_fks(self) -> None:
        """Test reference validation generation with foreign keys."""
        patterns = {
            "foreign_keys": [
                {"column": "no_produit", "ref_table": "produits", "ref_column": "no_produit"},
                {"column": "no_categorie", "ref_table": "categories", "ref_column": "id"}
            ]
        }

        refs = self.generator._generate_reference_validations(patterns)

        assert len(refs) == 2
        assert refs[0]["column"] == "no_produit"
        assert refs[0]["reference_table"] == "produits"
        assert refs[1]["column"] == "no_categorie"
        assert refs[1]["reference_table"] == "categories"

    def test_generate_reference_validations_defaults_ref_column(self) -> None:
        """Test reference validation defaults ref_column to 'id'."""
        patterns = {
            "foreign_keys": [
                {"column": "category_id", "ref_table": "categories"}  # No ref_column
            ]
        }

        refs = self.generator._generate_reference_validations(patterns)

        assert refs[0]["reference_column"] == "id"

    def test_generate_reference_validations_empty(self) -> None:
        """Test reference validation generation with no foreign keys."""
        patterns = {"foreign_keys": []}
        refs = self.generator._generate_reference_validations(patterns)
        assert len(refs) == 0

    # -------------------------------------------------------------------------
    # Tests for _generate_metadata
    # -------------------------------------------------------------------------

    def test_generate_metadata_complete(self) -> None:
        """Test metadata generation with complete information."""
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "name": ["A", "B", "C"],
        })

        patterns = {
            "primary_key": "id",
            "value_mappings": {"status": {"A": "active"}},
            "foreign_keys": [],
            "split_fields": None,
            "confidence": 0.95,
        }

        quality = {
            "score": 92,
            "grade": "A",
            "breakdown": {},
            "issues": [],
        }

        metadata = self.generator._generate_metadata(df, patterns, quality)

        assert metadata["row_count"] == 3
        assert metadata["column_count"] == 2
        assert metadata["quality_score"] == 92
        assert metadata["quality_grade"] == "A"
        assert metadata["detection_confidence"] == 0.95
        assert metadata["auto_generated"] is True
        assert metadata["primary_key_detected"] is True
        assert metadata["has_value_mappings"] is True
        assert metadata["has_foreign_keys"] is False
        assert metadata["has_split_fields"] is False

    def test_generate_metadata_minimal(self) -> None:
        """Test metadata generation with minimal information."""
        df = pd.DataFrame({"col1": [1, 2]})

        patterns = {
            "primary_key": None,
            "value_mappings": {},
            "foreign_keys": [],
            "split_fields": None,
            "confidence": 0.50,
        }

        quality = {
            "score": 70,
            "grade": "C",
            "breakdown": {},
            "issues": [],
        }

        metadata = self.generator._generate_metadata(df, patterns, quality)

        assert metadata["row_count"] == 2
        assert metadata["column_count"] == 1
        assert metadata["quality_score"] == 70
        assert metadata["quality_grade"] == "C"
        assert metadata["primary_key_detected"] is False

    # -------------------------------------------------------------------------
    # Tests for save and load
    # -------------------------------------------------------------------------

    def test_save_configuration(self) -> None:
        """Test saving configuration to JSON file."""
        df = pd.DataFrame({"id": [1, 2, 3]})

        patterns = {"primary_key": "id", "value_mappings": {}, "foreign_keys": [], "split_fields": None, "confidence": 1.0}
        quality = {"score": 100, "grade": "A+", "breakdown": {}, "issues": []}

        config = self.generator.generate(df, "test", patterns, quality)

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "mappings.json"
            self.generator.save(config, filepath)

            assert filepath.exists()

            # Verify file content
            with open(filepath, "r") as f:
                content = json.load(f)
                assert "mappings" in content
                assert "test" in content["mappings"]

    def test_load_configuration(self) -> None:
        """Test loading configuration from JSON file."""
        test_config = {
            "mappings": {
                "produits": {
                    "target_table": "produits",
                    "primary_key": ["no_produit"],
                    "column_mappings": {},
                    "value_mappings": [],
                    "calculated_columns": [],
                    "validation_rules": [],
                    "reference_validations": [],
                    "hooks": [],
                    "tags": [],
                    "metadata": {}
                }
            }
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "mappings.json"
            with open(filepath, "w") as f:
                json.dump(test_config, f)

            loaded = self.generator.load(filepath)

            assert loaded == test_config

    # -------------------------------------------------------------------------
    # Edge case tests
    # -------------------------------------------------------------------------

    def test_empty_dataframe(self) -> None:
        """Test configuration generation with empty DataFrame."""
        df = pd.DataFrame()

        patterns = {"primary_key": None, "value_mappings": {}, "foreign_keys": [], "split_fields": None, "confidence": 0.0}
        quality = {"score": 0, "grade": "D", "breakdown": {}, "issues": ["Table is empty"]}

        config = self.generator.generate(df, "empty", patterns, quality)

        assert config["target_table"] == "empty"
        assert config["metadata"]["row_count"] == 0
        assert config["metadata"]["column_count"] == 0

    def test_dataframe_with_mixed_types(self) -> None:
        """Test configuration generation with mixed data types."""
        df = pd.DataFrame({
            "int_col": [1, 2, 3],
            "float_col": [1.5, 2.5, 3.5],
            "str_col": ["A", "B", "C"],
            "bool_col": [True, False, True],
            "date_col": pd.to_datetime(["2024-01-01", "2024-02-01", "2024-03-01"]),
        })

        patterns = {"primary_key": "int_col", "value_mappings": {}, "foreign_keys": [], "split_fields": None, "confidence": 1.0}
        quality = {"score": 100, "grade": "A+", "breakdown": {}, "issues": []}

        config = self.generator.generate(df, "test", patterns, quality)

        assert config["column_mappings"]["int_col"]["type"] == "integer"
        assert config["column_mappings"]["float_col"]["type"] == "float"
        assert config["column_mappings"]["str_col"]["type"] == "string"
        assert config["column_mappings"]["bool_col"]["type"] == "boolean"
        assert config["column_mappings"]["date_col"]["type"] == "date"
