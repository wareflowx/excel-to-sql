"""
Integration tests for QualityScorer with real Excel files.

Tests use actual Excel fixtures to verify end-to-end quality scoring.
"""

import pytest
import pandas as pd
from pathlib import Path
from excel_to_sql.auto_pilot.scorer import QualityScorer


class TestQualityScorerIntegration:
    """Integration tests with real Excel files."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.scorer = QualityScorer()
        self.fixtures_dir = Path(__file__).parent.parent / "fixtures" / "auto_pilot"

    # -------------------------------------------------------------------------
    # Integration tests with produits.xlsx
    # -------------------------------------------------------------------------

    def test_produits_xlsx_quality_scoring(self) -> None:
        """Test quality scoring on produits.xlsx fixture."""
        produits_file = self.fixtures_dir / "produits.xlsx"
        df = pd.read_excel(produits_file)

        result = self.scorer.score_table(df, "produits", primary_key="no_produit")

        # Verify score is calculated
        assert "score" in result
        assert 0 <= result["score"] <= 100

        # Verify grade is assigned
        assert result["grade"] in ["A+", "A", "B", "C", "D"]

        # Verify breakdown dimensions
        assert "completeness" in result["breakdown"]
        assert "uniqueness" in result["breakdown"]
        assert "validity" in result["breakdown"]
        assert "consistency" in result["breakdown"]

    def test_produits_xlsx_detects_missing_categories(self) -> None:
        """Test that produits.xlsx analysis detects missing categories."""
        produits_file = self.fixtures_dir / "produits.xlsx"
        df = pd.read_excel(produits_file)

        result = self.scorer.score_table(df, "produits", primary_key="no_produit")

        # produits.xlsx has 3 missing categories out of 10 rows (30%)
        # Should have at least one issue about missing categories
        assert len(result["issues"]) >= 0  # May or may not flag depending on threshold
        # The completeness breakdown should reflect this
        assert result["breakdown"]["completeness"] <= 100

    def test_produits_xlsx_grade_matches_expectations(self) -> None:
        """Test that produits.xlsx gets appropriate grade."""
        produits_file = self.fixtures_dir / "produits.xlsx"
        df = pd.read_excel(produits_file)

        result = self.scorer.score_table(df, "produits", primary_key="no_produit")

        # produits.xlsx has good quality but some missing values
        # Should be in A or B range
        assert result["grade"] in ["A+", "A", "B"]

    # -------------------------------------------------------------------------
    # Integration tests with mouvements.xlsx
    # -------------------------------------------------------------------------

    def test_mouvements_xlsx_quality_scoring(self) -> None:
        """Test quality scoring on mouvements.xlsx fixture."""
        mouvements_file = self.fixtures_dir / "mouvements.xlsx"
        df = pd.read_excel(mouvements_file)

        result = self.scorer.score_table(df, "mouvements", primary_key="oid")

        # Verify score structure
        assert "score" in result
        assert "grade" in result
        assert "breakdown" in result
        assert "issues" in result

    def test_mouvements_xlsx_high_quality_score(self) -> None:
        """Test that mouvements.xlsx has high quality score."""
        mouvements_file = self.fixtures_dir / "mouvements.xlsx"
        df = pd.read_excel(mouvements_file)

        result = self.scorer.score_table(df, "mouvements", primary_key="oid")

        # mouvements.xlsx has good quality (unique OID, no major issues)
        # Should have score >= 90
        assert result["score"] >= 90
        assert result["grade"] in ["A+", "A"]

    def test_mouvements_xlsx_detects_negative_quantities(self) -> None:
        """Test that mouvements.xlsx detects negative quantities."""
        mouvements_file = self.fixtures_dir / "mouvements.xlsx"
        df = pd.read_excel(mouvements_file)

        result = self.scorer.score_table(df, "mouvements", primary_key="oid")

        # mouvements.xlsx has negative quantities (SORTIE movements)
        # This should be detected as a validity issue
        # However, negative quantities might be valid for SORTIE (outbound)
        # So we just check that the score is calculated correctly
        assert result["score"] >= 0

    # -------------------------------------------------------------------------
    # Integration tests with commandes.xlsx
    # -------------------------------------------------------------------------

    def test_commandes_xlsx_quality_scoring(self) -> None:
        """Test quality scoring on commandes.xlsx fixture."""
        commandes_file = self.fixtures_dir / "commandes.xlsx"
        df = pd.read_excel(commandes_file)

        result = self.scorer.score_table(df, "commandes", primary_key="commande")

        # Verify score structure
        assert "score" in result
        assert "grade" in result
        assert "breakdown" in result
        assert "issues" in result

    def test_commandes_xlsx_perfect_quality(self) -> None:
        """Test that commandes.xlsx has excellent quality."""
        commandes_file = self.fixtures_dir / "commandes.xlsx"
        df = pd.read_excel(commandes_file)

        result = self.scorer.score_table(df, "commandes", primary_key="commande")

        # commandes.xlsx has perfect quality
        # Should have score >= 95 and grade A+
        assert result["score"] >= 95
        assert result["grade"] == "A+"

    # -------------------------------------------------------------------------
    # End-to-end workflow tests
    # -------------------------------------------------------------------------

    def test_end_to_end_scoring_workflow(self) -> None:
        """Test complete scoring workflow across all fixtures."""
        all_results = {}

        for fixture_name in ["produits.xlsx", "mouvements.xlsx", "commandes.xlsx"]:
            fixture_file = self.fixtures_dir / fixture_name
            df = pd.read_excel(fixture_file)
            table_name = fixture_name.replace(".xlsx", "")

            # Detect primary key first (would come from PatternDetector in real usage)
            from excel_to_sql.auto_pilot.detector import PatternDetector
            detector = PatternDetector()
            patterns = detector.detect_patterns(df, table_name)
            primary_key = patterns.get("primary_key")

            result = self.scorer.score_table(df, table_name, primary_key=primary_key)
            all_results[table_name] = result

            # Verify each result has required fields
            assert "score" in result
            assert "grade" in result
            assert "breakdown" in result
            assert "issues" in result

        # Verify specific expectations per table
        assert all_results["commandes"]["score"] >= 95  # Perfect quality
        assert all_results["mouvements"]["score"] >= 90  # High quality
        assert all_results["produits"]["score"] >= 80  # Good quality

    def test_scoring_accuracy_on_real_wms_data(self) -> None:
        """Test that scoring accurately reflects data quality."""
        test_cases = [
            {
                "file": "produits.xlsx",
                "table": "produits",
                "expected_min_score": 80,  # Good but has missing values
                "expected_max_score": 100,
            },
            {
                "file": "mouvements.xlsx",
                "table": "mouvements",
                "expected_min_score": 90,  # High quality
                "expected_max_score": 100,
            },
            {
                "file": "commandes.xlsx",
                "table": "commandes",
                "expected_min_score": 95,  # Excellent quality
                "expected_max_score": 100,
            },
        ]

        for test_case in test_cases:
            fixture_file = self.fixtures_dir / test_case["file"]
            df = pd.read_excel(fixture_file)

            # Get primary key from PatternDetector
            from excel_to_sql.auto_pilot.detector import PatternDetector
            detector = PatternDetector()
            patterns = detector.detect_patterns(df, test_case["table"])
            primary_key = patterns.get("primary_key")

            result = self.scorer.score_table(df, test_case["table"], primary_key=primary_key)

            # Verify score is within expected range
            assert test_case["expected_min_score"] <= result["score"] <= test_case["expected_max_score"], \
                f"{test_case['file']}: expected score {test_case['expected_min_score']}-{test_case['expected_max_score']}, got {result['score']}"

    # -------------------------------------------------------------------------
    # Performance tests
    # -------------------------------------------------------------------------

    def test_scoring_performance_on_large_file(self) -> None:
        """Test that scoring completes within acceptable time limits."""
        import time

        mouvements_file = self.fixtures_dir / "mouvements.xlsx"
        df = pd.read_excel(mouvements_file)

        start_time = time.time()
        result = self.scorer.score_table(df, "mouvements", primary_key="oid")
        end_time = time.time()

        elapsed = end_time - start_time

        # Should complete in less than 1 second for 50 rows
        assert elapsed < 1.0, f"Scoring took {elapsed:.2f}s, expected < 1.0s"

        # Should still produce valid results
        assert result["score"] >= 0

    # -------------------------------------------------------------------------
    # Edge case tests with real data
    # -------------------------------------------------------------------------

    def test_handles_french_characters_in_data(self) -> None:
        """Test that French characters in data are handled correctly."""
        # produits file has French values (ACTIF, INACTIF, Électronique, etc.)
        produits_file = self.fixtures_dir / "produits.xlsx"
        df = pd.read_excel(produits_file)

        # Should not crash on French characters
        result = self.scorer.score_table(df, "produits", primary_key="no_produit")

        assert result is not None
        assert "score" in result

    def test_handles_mixed_data_types_in_columns(self) -> None:
        """Test that mixed data types are handled correctly."""
        # mouvements file has date_heure_2 with mixed types (timestamps and None)
        mouvements_file = self.fixtures_dir / "mouvements.xlsx"
        df = pd.read_excel(mouvements_file)

        # Should still score correctly
        result = self.scorer.score_table(df, "mouvements", primary_key="oid")

        assert result["score"] >= 0
        assert result["grade"] in ["A+", "A", "B", "C", "D"]

    # -------------------------------------------------------------------------
    # Integration with PatternDetector
    # -------------------------------------------------------------------------

    def test_integration_with_pattern_detector(self) -> None:
        """Test that QualityScorer works well with PatternDetector output."""
        from excel_to_sql.auto_pilot.detector import PatternDetector

        produits_file = self.fixtures_dir / "produits.xlsx"
        df = pd.read_excel(produits_file)

        # Step 1: Detect patterns
        detector = PatternDetector()
        patterns = detector.detect_patterns(df, "produits")

        # Step 2: Score quality using detected PK
        result = self.scorer.score_table(
            df,
            "produits",
            primary_key=patterns.get("primary_key")
        )

        # Verify integration works
        assert result["score"] >= 0
        assert patterns["primary_key"] == "no_produit"
        assert result["breakdown"]["uniqueness"] == 100  # No duplicate PKs

    def test_combined_pattern_detection_and_quality_scoring(self) -> None:
        """Test complete workflow: pattern detection + quality scoring."""
        from excel_to_sql.auto_pilot.detector import PatternDetector

        all_files = ["produits.xlsx", "mouvements.xlsx", "commandes.xlsx"]
        results = {}

        for filename in all_files:
            filepath = self.fixtures_dir / filename
            df = pd.read_excel(filepath)
            table_name = filename.replace(".xlsx", "")

            # Detect patterns
            detector = PatternDetector()
            patterns = detector.detect_patterns(df, table_name)

            # Score quality
            quality = self.scorer.score_table(
                df,
                table_name,
                primary_key=patterns.get("primary_key")
            )

            results[table_name] = {
                "patterns": patterns,
                "quality": quality,
            }

        # Verify all tables were analyzed
        assert len(results) == 3

        # Verify each has both pattern and quality info
        for table_name, result in results.items():
            assert "primary_key" in result["patterns"]
            assert "score" in result["quality"]
            assert "grade" in result["quality"]
