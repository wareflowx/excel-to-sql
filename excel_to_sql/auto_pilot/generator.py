"""
Configuration Generation Module for Auto-Pilot Mode.

This module provides automatic generation of Excel-to-SQL mapping configurations
based on detected patterns and quality scores.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


class ConfigGenerator:
    """
    Automatically generates mapping configuration from detected patterns.

    This class analyzes detected patterns from PatternDetector and quality
    scores from QualityScorer to generate a complete mappings.json file
    ready for Excel-to-SQL imports.

    The generated configuration includes:
    - Column mappings with inferred types
    - Value mappings for French code translations
    - Calculated columns for split fields
    - Validation rules (PK uniqueness, required fields)
    - Reference validations for foreign keys
    - Metadata with quality scores

    Example:
        >>> generator = ConfigGenerator()
        >>> patterns = detector.detect_patterns(df, "produits")
        >>> quality = scorer.score_table(df, "produits", primary_key=patterns["primary_key"])
        >>> config = generator.generate(df, "produits", patterns, quality)
        >>> generator.save(config, ".excel-to-sql/mappings.json")
    """

    def __init__(self) -> None:
        """Initialize the ConfigGenerator."""
        pass

    def generate(
        self,
        df: pd.DataFrame,
        table_name: str,
        patterns: dict[str, Any],
        quality: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Generate complete mapping configuration from patterns and quality score.

        Args:
            df: Input DataFrame
            table_name: Name of the table
            patterns: Detected patterns from PatternDetector
            quality: Quality score from QualityScorer

        Returns:
            Dictionary containing the complete mapping configuration
            compatible with the mapping models

        Example:
            >>> detector = PatternDetector()
            >>> scorer = QualityScorer()
            >>> generator = ConfigGenerator()
            >>>
            >>> df = pd.read_excel("produits.xlsx")
            >>> patterns = detector.detect_patterns(df, "produits")
            >>> quality = scorer.score_table(df, "produits", primary_key=patterns["primary_key"])
            >>> config = generator.generate(df, "produits", patterns, quality)
        """
        # Infer column mappings with types
        column_mappings = self._generate_column_mappings(df)

        # Generate value mappings from detected patterns
        value_mappings = self._generate_value_mappings(patterns)

        # Generate calculated columns for split fields
        calculated_columns = self._generate_calculated_columns(patterns)

        # Generate validation rules
        validation_rules = self._generate_validation_rules(df, patterns)

        # Generate reference validations for foreign keys
        reference_validations = self._generate_reference_validations(patterns)

        # Generate metadata including quality score
        metadata = self._generate_metadata(df, patterns, quality)

        # Determine primary key
        primary_key = patterns.get("primary_key")
        if primary_key:
            primary_key_list = [primary_key]
        else:
            primary_key_list = []

        # Build the complete type mapping
        type_mapping = {
            "target_table": table_name,
            "primary_key": primary_key_list,
            "column_mappings": column_mappings,
            "value_mappings": value_mappings,
            "calculated_columns": calculated_columns,
            "validation_rules": validation_rules,
            "reference_validations": reference_validations,
            "hooks": [],
            "tags": ["auto-generated"],
            "metadata": metadata,
        }

        return type_mapping

    def _generate_column_mappings(self, df: pd.DataFrame) -> dict[str, dict[str, Any]]:
        """
        Generate column mappings with inferred SQL types.

        Args:
            df: Input DataFrame

        Returns:
            Dictionary mapping column names to their configuration

        Example:
            >>> df = pd.DataFrame({"id": [1, 2], "name": ["A", "B"]})
            >>> generator = ConfigGenerator()
            >>> mappings = generator._generate_column_mappings(df)
            >>> mappings["id"]["type"]  # "integer"
            >>> mappings["name"]["type"]  # "string"
        """
        column_mappings: dict[str, dict[str, Any]] = {}

        for col in df.columns:
            col_type = self._infer_sql_type(df[col])
            col_mapping = {
                "target": str(col),
                "type": col_type,
                "required": False,  # Will be updated by validation rules if needed
                "default": None,
            }
            column_mappings[str(col)] = col_mapping

        return column_mappings

    def _infer_sql_type(self, series: pd.Series) -> str:
        """
        Infer SQL type from pandas Series dtype.

        Args:
            series: pandas Series to analyze

        Returns:
            SQL type string: "string", "integer", "float", "boolean", or "date"
        """
        dtype = series.dtype

        # Handle datetime types
        if pd.api.types.is_datetime64_any_dtype(dtype):
            return "date"

        # Handle numeric types
        if pd.api.types.is_integer_dtype(dtype):
            return "integer"
        elif pd.api.types.is_float_dtype(dtype):
            return "float"
        elif pd.api.types.is_bool_dtype(dtype):
            return "boolean"

        # Handle object/string types
        if dtype == "object":
            # Check if it's actually a date string
            try:
                pd.to_datetime(series, errors="raise")
                return "date"
            except (ValueError, TypeError):
                pass

            # Check for numeric-like strings
            try:
                pd.to_numeric(series, errors="raise")
                return "float"
            except (ValueError, TypeError):
                pass

        return "string"

    def _generate_value_mappings(self, patterns: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Generate value mapping configurations from detected patterns.

        Args:
            patterns: Detected patterns from PatternDetector

        Returns:
            List of value mapping configurations

        Example:
            >>> patterns = {"value_mappings": {"etat": {"ACTIF": "active"}}}
            >>> generator = ConfigGenerator()
            >>> mappings = generator._generate_value_mappings(patterns)
            >>> mappings[0]["column"]  # "etat"
        """
        value_mappings: list[dict[str, Any]] = []

        detected_mappings = patterns.get("value_mappings", {})

        for col, mappings in detected_mappings.items():
            value_mapping = {
                "column": col,
                "mappings": mappings,
            }
            value_mappings.append(value_mapping)

        return value_mappings

    def _generate_calculated_columns(self, patterns: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Generate calculated column configurations for split fields.

        When mutually exclusive status fields are detected, creates a COALESCE
        expression to combine them into a single column.

        Args:
            patterns: Detected patterns from PatternDetector

        Returns:
            List of calculated column configurations

        Example:
            >>> patterns = {"split_fields": ["etat_superieur", "etat_inferieur", "etat"]}
            >>> generator = ConfigGenerator()
            >>> calc_cols = generator._generate_calculated_columns(patterns)
            >>> calc_cols[0]["expression"]  # "COALESCE(etat_superieur, etat_inferieur, etat)"
        """
        calculated_columns: list[dict[str, Any]] = []

        split_fields = patterns.get("split_fields")

        if split_fields and len(split_fields) > 1:
            # Create a COALESCE expression to combine split fields
            col_list = ", ".join(split_fields)
            combined_name = self._guess_combined_column_name(split_fields)

            calculated_col = {
                "name": combined_name,
                "expression": f"COALESCE({col_list})",
                "type": "string",
            }
            calculated_columns.append(calculated_col)

        return calculated_columns

    def _guess_combined_column_name(self, split_fields: list[str]) -> str:
        """
        Guess the combined column name from split field names.

        Args:
            split_fields: List of split field column names

        Returns:
            Guessed combined column name

        Example:
            >>> generator = ConfigGenerator()
            >>> generator._guess_combined_column_name(["etat_superieur", "etat"])
            'etat'
        """
        # Find the shortest name that's a prefix of others
        sorted_fields = sorted(split_fields, key=len)
        shortest = sorted_fields[0]

        # Check if shortest is a prefix of others
        if all(shortest in field for field in split_fields[1:]):
            return shortest

        # Otherwise, use the shortest name
        return shortest

    def _generate_validation_rules(
        self,
        df: pd.DataFrame,
        patterns: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Generate validation rules from detected patterns.

        Creates:
        - Unique validation for primary key
        - Required validation for columns with no nulls

        Args:
            df: Input DataFrame
            patterns: Detected patterns from PatternDetector

        Returns:
            List of validation rule configurations

        Example:
            >>> patterns = {"primary_key": "no_produit"}
            >>> generator = ConfigGenerator()
            >>> rules = generator._generate_validation_rules(df, patterns)
            >>> rules[0]["type"]  # "unique"
        """
        validation_rules: list[dict[str, Any]] = []

        # Add unique validation for primary key
        primary_key = patterns.get("primary_key")
        if primary_key:
            unique_rule = {
                "column": primary_key,
                "type": "unique",
                "params": {},
                "message": f"{primary_key} must be unique",
                "severity": "error",
            }
            validation_rules.append(unique_rule)

        # Add required validation for columns with no nulls
        for col in df.columns:
            if df[col].notna().all() and col != primary_key:
                required_rule = {
                    "column": str(col),
                    "type": "required",
                    "params": {},
                    "message": f"{col} is required",
                    "severity": "warning",
                }
                validation_rules.append(required_rule)

        return validation_rules

    def _generate_reference_validations(self, patterns: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Generate reference validations for detected foreign keys.

        Args:
            patterns: Detected patterns from PatternDetector

        Returns:
            List of reference validation configurations

        Example:
            >>> patterns = {"foreign_keys": [{"column": "no_produit", "ref_table": "produits"}]}
            >>> generator = ConfigGenerator()
            >>> refs = generator._generate_reference_validations(patterns)
            >>> refs[0]["reference_table"]  # "produits"
        """
        reference_validations: list[dict[str, Any]] = []

        foreign_keys = patterns.get("foreign_keys", [])

        for fk in foreign_keys:
            ref_validation = {
                "column": fk["column"],
                "reference_table": fk["ref_table"],
                "reference_column": fk.get("ref_column", "id"),
            }
            reference_validations.append(ref_validation)

        return reference_validations

    def _generate_metadata(
        self,
        df: pd.DataFrame,
        patterns: dict[str, Any],
        quality: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Generate metadata including quality score and detection confidence.

        Args:
            df: Input DataFrame
            patterns: Detected patterns from PatternDetector
            quality: Quality score from QualityScorer

        Returns:
            Metadata dictionary

        Example:
            >>> quality = {"score": 92, "grade": "A"}
            >>> patterns = {"confidence": 0.95}
            >>> generator = ConfigGenerator()
            >>> metadata = generator._generate_metadata(df, patterns, quality)
            >>> metadata["quality_score"]  # 92
        """
        metadata = {
            "row_count": len(df),
            "column_count": len(df.columns),
            "quality_score": quality.get("score", 0),
            "quality_grade": quality.get("grade", "D"),
            "detection_confidence": patterns.get("confidence", 0.0),
            "auto_generated": True,
            "primary_key_detected": patterns.get("primary_key") is not None,
            "has_value_mappings": len(patterns.get("value_mappings", {})) > 0,
            "has_foreign_keys": len(patterns.get("foreign_keys", [])) > 0,
            "has_split_fields": patterns.get("split_fields") is not None,
        }

        return metadata

    def save(self, config: dict[str, Any], filepath: str | Path) -> None:
        """
        Save configuration to a JSON file.

        Args:
            config: Configuration dictionary from generate()
            filepath: Path to save the configuration file

        Example:
            >>> generator = ConfigGenerator()
            >>> config = generator.generate(df, "produits", patterns, quality)
            >>> generator.save(config, ".excel-to-sql/mappings.json")
        """
        filepath = Path(filepath)

        # Create parent directory if it doesn't exist
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # Wrap in mappings container for full compatibility
        full_config = {
            "mappings": {
                config["target_table"]: config
            }
        }

        # Write to file
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(full_config, f, indent=2, ensure_ascii=False)

    def load(self, filepath: str | Path) -> dict[str, Any]:
        """
        Load configuration from a JSON file.

        Args:
            filepath: Path to the configuration file

        Returns:
            Configuration dictionary

        Example:
            >>> generator = ConfigGenerator()
            >>> config = generator.load(".excel-to-sql/mappings.json")
        """
        filepath = Path(filepath)

        with open(filepath, "r", encoding="utf-8") as f:
            config = json.load(f)

        return config
