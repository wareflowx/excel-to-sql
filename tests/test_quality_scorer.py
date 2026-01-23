"""
Tests for QualityScorer in auto_pilot module.
"""

import pytest
import pandas as pd
import numpy as np

from excel_to_sql.auto_pilot.quality import QualityScorer


class TestQualityScorer:
    """Tests for QualityScorer class."""

    @pytest.fixture
    def scorer(self):
        """Create a QualityScorer instance."""
        return QualityScorer()

    @pytest.fixture
    def sample_df(self):
        """Create a sample DataFrame for testing."""
        return pd.DataFrame({
            "id": [1, 2, 3, 4, 5],
            "name": ["Alice", "Bob", "Charlie", "David", "Eve"],
            "age": [25, 30, 35, 40, 45],
            "email": ["alice@example.com", "bob@example.com", None, "david@example.com", "eve@example.com"],
            "salary": [50000, 60000, None, 80000, 90000],
            "department": ["Sales", "Engineering", "Engineering", "Sales", "HR"]
        })

    # ──────────────────────────────────────────────────────────────
    # Tests for generate_quality_report
    # ──────────────────────────────────────────────────────────────

    def test_generate_quality_report_basic(self, scorer, sample_df):
        """Test basic quality report generation."""
        report = scorer.generate_quality_report(sample_df, "employees")

        assert report["table_name"] == "employees"
        assert report["row_count"] == 5
        assert report["column_count"] == 6
        assert "score" in report
        assert "grade" in report
        assert "issues" in report
        assert "column_stats" in report
        assert isinstance(report["score"], int)
        assert isinstance(report["grade"], str)
        assert isinstance(report["issues"], list)
        assert isinstance(report["column_stats"], dict)

    def test_generate_quality_report_high_quality(self, scorer):
        """Test quality report for high-quality data."""
        df = pd.DataFrame({
            "id": [1, 2, 3, 4, 5],
            "name": ["A", "B", "C", "D", "E"],
            "value": [10, 20, 30, 40, 50]
        })

        report = scorer.generate_quality_report(df, "test")

        assert report["score"] >= 90
        assert report["grade"] == "A"
        assert len(report["issues"]) == 0

    def test_generate_quality_report_with_nulls(self, scorer):
        """Test quality report detects null values."""
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "name": ["A", None, "C"],
            "value": [10, 20, 30]
        })

        report = scorer.generate_quality_report(df, "test")

        assert report["score"] < 100
        assert "null values" in " ".join(report["issues"]).lower()

    def test_generate_quality_report_empty_dataframe(self, scorer):
        """Test quality report for empty DataFrame."""
        df = pd.DataFrame()

        report = scorer.generate_quality_report(df, "test")

        assert report["score"] == 0
        assert report["grade"] == "F"
        assert "empty" in " ".join(report["issues"]).lower()

    def test_generate_quality_report_with_duplicates(self, scorer):
        """Test quality report detects duplicates in potential PK."""
        df = pd.DataFrame({
            "id": [1, 2, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19],  # 19 unique out of 20 = 95%, potential PK with 1 duplicate
            "name": ["A", "B", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S"]
        })

        report = scorer.generate_quality_report(df, "test")

        assert report["score"] < 100
        assert any("duplicate" in issue.lower() for issue in report["issues"])

    def test_generate_quality_report_empty_column(self, scorer):
        """Test quality report detects empty columns."""
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "name": ["A", "B", "C"],
            "empty": [None, None, None]
        })

        report = scorer.generate_quality_report(df, "test")

        assert report["score"] < 100
        assert "empty" in " ".join(report["issues"]).lower()

    def test_generate_quality_report_outliers(self, scorer):
        """Test quality report detects outliers."""
        # Create data with outliers
        np.random.seed(42)
        data = np.random.randn(100)  # Most values between -3 and 3
        data[0] = 10  # Clear outlier
        data[1] = -15  # Clear outlier

        df = pd.DataFrame({"value": data})

        report = scorer.generate_quality_report(df, "test")

        assert report["score"] < 100
        assert any("outlier" in issue.lower() for issue in report["issues"])

    def test_grade_assignment(self, scorer):
        """Test letter grade assignment."""
        # A grade
        df_a = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        assert scorer.generate_quality_report(df_a, "test")["grade"] == "A"

        # B grade
        df_b = pd.DataFrame({"a": [1, 2, None], "b": [4, 5, 6]})
        report_b = scorer.generate_quality_report(df_b, "test")
        assert report_b["grade"] in ["A", "B"]  # Should be A or B

        # Low quality
        df_low = pd.DataFrame({"a": [None, None, None], "b": [None, None, None]})
        assert scorer.generate_quality_report(df_low, "test")["grade"] in ["D", "F"]

    # ──────────────────────────────────────────────────────────────
    # Tests for column statistics
    # ──────────────────────────────────────────────────────────────

    def test_column_stats_null_count(self, scorer, sample_df):
        """Test null count in column statistics."""
        report = scorer.generate_quality_report(sample_df, "test")

        email_stats = report["column_stats"]["email"]
        assert email_stats["null_count"] == 1
        assert email_stats["null_percentage"] == 20.0

        salary_stats = report["column_stats"]["salary"]
        assert salary_stats["null_count"] == 1

    def test_column_stats_unique_count(self, scorer, sample_df):
        """Test unique count in column statistics."""
        report = scorer.generate_quality_report(sample_df, "test")

        id_stats = report["column_stats"]["id"]
        assert id_stats["unique_count"] == 5
        assert id_stats["unique_percentage"] == 100.0

    def test_column_stats_dtype(self, scorer, sample_df):
        """Test data type in column statistics."""
        report = scorer.generate_quality_report(sample_df, "test")

        assert report["column_stats"]["id"]["dtype"] == "int64"
        assert report["column_stats"]["name"]["dtype"] == "object"

    def test_column_stats_sample_values(self, scorer, sample_df):
        """Test sample values in column statistics."""
        report = scorer.generate_quality_report(sample_df, "test")

        name_stats = report["column_stats"]["name"]
        assert "sample_values" in name_stats
        assert len(name_stats["sample_values"]) <= 5
        assert all(isinstance(v, str) for v in name_stats["sample_values"])

    def test_column_stats_potential_pk(self, scorer):
        """Test potential primary key detection."""
        df = pd.DataFrame({
            "id": [1, 2, 3, 4, 5],
            "name": ["A", "B", "A", "D", "E"],  # Not all unique (A appears twice)
            "category": ["X", "Y", "X", "Y", "X"]  # Not unique
        })

        report = scorer.generate_quality_report(df, "test")

        assert report["column_stats"]["id"]["is_potential_pk"] is True
        assert report["column_stats"]["name"]["is_potential_pk"] is False
        assert report["column_stats"]["category"]["is_potential_pk"] is False

    # ──────────────────────────────────────────────────────────────
    # Tests for quality score calculation
    #──────────────────────────────────────────────────────────────

    def test_score_calculation_perfect_data(self, scorer):
        """Test score calculation for perfect data."""
        df = pd.DataFrame({
            "id": [1, 2, 3, 4, 5],
            "name": ["A", "B", "C", "D", "E"]
        })

        report = scorer.generate_quality_report(df, "test")
        assert report["score"] == 100

    def test_score_calculation_with_nulls(self, scorer):
        """Test score deduction for null values."""
        # 20% null values = 10 points over threshold
        df = pd.DataFrame({
            "col": [1, 2, 3, 4, 5] * 5  # 20% nulls
        })
        df["col"] = df["col"].astype(float)
        df.loc[0:5, "col"] = None

        report = scorer.generate_quality_report(df, "test")
        # 20% - 10% threshold = 10% * 0.5 = 5 points deduction
        assert report["score"] <= 95
        assert report["score"] >= 90  # Should still be A grade

    def test_score_calculation_with_duplicates(self, scorer):
        """Test score deduction for duplicates in PK."""
        # 2 duplicates in PK column (18 unique out of 20 = 90%)
        df = pd.DataFrame({
            "id": [1, 2, 2, 3, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
            "value": list(range(20))
        })

        report = scorer.generate_quality_report(df, "test")
        # 2 duplicates * 2 points = 4 points deduction
        assert report["score"] == 96

    def test_score_calculation_with_empty_columns(self, scorer):
        """Test score deduction for empty columns."""
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "empty_col": [None, None, None],
            "value": [10, 20, 30]
        })

        report = scorer.generate_quality_report(df, "test")
        # 1 empty column: 5 points deduction for empty column
        # + (100% - 10%) * 0.5 = 45 points for null values
        # Total = 50 points deduction, score = 50
        assert report["score"] == 50

    def test_score_calculation_floor(self, scorer):
        """Test score never goes below 0."""
        df = pd.DataFrame({
            "a": [None, None, None],
            "b": [None, None, None],
            "c": [None, None, None]
        })

        report = scorer.generate_quality_report(df, "test")
        assert report["score"] == 0  # Floor at 0

    # ──────────────────────────────────────────────────────────────
    # Tests for configuration
    # ──────────────────────────────────────────────────────────────

    def test_default_thresholds(self, scorer):
        """Test default quality thresholds."""
        thresholds = scorer.get_quality_thresholds()

        assert thresholds["grade_a_min"] == 90
        assert thresholds["grade_b_min"] == 75
        assert thresholds["grade_c_min"] == 60
        assert thresholds["null_threshold"] == 10

    def test_custom_thresholds(self, scorer):
        """Test setting custom quality thresholds."""
        scorer.set_quality_thresholds(
            grade_a_min=85,
            grade_b_min=70,
            grade_c_min=55,
            null_threshold=15
        )

        thresholds = scorer.get_quality_thresholds()
        assert thresholds["grade_a_min"] == 85
        assert thresholds["grade_b_min"] == 70
        assert thresholds["grade_c_min"] == 55
        assert thresholds["null_threshold"] == 15

    def test_custom_thresholds_affect_grades(self, scorer):
        """Test that custom thresholds affect grade assignment."""
        scorer.set_quality_thresholds(grade_a_min=85, grade_b_min=70)

        # Perfect data should get A
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        report = scorer.generate_quality_report(df, "test")

        # With default thresholds would be A (100), verify it's still A
        assert report["grade"] == "A"

    # ──────────────────────────────────────────────────────────────
    # Tests for outlier detection
    # ──────────────────────────────────────────────────────────────

    def test_detect_outliers_3sigma(self, scorer):
        """Test outlier detection using 3-sigma rule."""
        # Create data with known outliers
        np.random.seed(42)
        data = [0] * 100
        data[0] = 50  # Clear outlier (> 3 sigma for data with mean=0, std small)
        data[1] = -30

        df = pd.DataFrame({"value": data})
        report = scorer.generate_quality_report(df, "test")

        # Should detect outliers
        assert any("outlier" in str(issue).lower() for issue in report["issues"])

    def test_detect_outliers_no_data(self, scorer):
        """Test outlier detection with insufficient data."""
        df = pd.DataFrame({"value": [1, 2]})  # Only 2 values

        report = scorer.generate_quality_report(df, "test")

        # Should not detect outliers (need at least 3 values for std)
        assert not any("outlier" in str(issue).lower() for issue in report["issues"])

    def test_detect_outliers_all_null(self, scorer):
        """Test outlier detection with all null values."""
        df = pd.DataFrame({"value": [None, None, None]})

        report = scorer.generate_quality_report(df, "test")

        # Should not detect outliers
        assert not any("outlier" in str(issue).lower() for issue in report["issues"])

    # ──────────────────────────────────────────────────────────────
    # Tests for type hints and docstrings
    # ──────────────────────────────────────────────────────────────

    def test_generate_quality_report_type_hints(self, scorer):
        """Test that generate_quality_report has proper type hints."""
        import inspect

        sig = inspect.signature(scorer.generate_quality_report)
        annotations = sig.parameters

        assert "df" in annotations
        assert "table_name" in annotations
        # With __future__ annotations, these are strings
        assert "pd.DataFrame" in str(annotations["df"].annotation)
        assert "str" in str(annotations["table_name"].annotation)
        assert "Dict" in str(sig.return_annotation)

    def test_quality_scorer_docstring(self):
        """Test that QualityScorer has proper docstrings."""
        assert QualityScorer.__doc__ is not None
        assert "QualityScorer" in QualityScorer.__name__
        assert "generate_quality_report" in dir(QualityScorer)

    def test_methods_have_docstrings(self, scorer):
        """Test that public methods have docstrings."""
        assert scorer.generate_quality_report.__doc__ is not None
        assert scorer.get_quality_thresholds.__doc__ is not None
        assert scorer.set_quality_thresholds.__doc__ is not None

    # ──────────────────────────────────────────────────────────────
    # Integration-style tests
    # ──────────────────────────────────────────────────────────────

    def test_realistic_dataframe(self, scorer):
        """Test with realistic dataset."""
        df = pd.DataFrame({
            "product_id": [101, 102, 103, 104, 105, None],  # One null
            "product_name": ["Widget A", "Widget B", "Widget C", "Widget D", "Widget E", None],
            "price": [10.99, 20.50, 15.75, None, 25.00, None],  # Two nulls
            "category": ["Electronics", "Electronics", "Home", "Home", "Garden", None],
            "in_stock": [True, False, True, True, False, None],
            "supplier": ["ACME", "ACME", "BCorp", "ACME", "BCorp", None]
        })

        report = scorer.generate_quality_report(df, "products")

        # Should detect issues
        assert len(report["issues"]) > 0

        # Score should be reasonable
        assert 0 <= report["score"] <= 100

        # Should have stats for all columns
        assert len(report["column_stats"]) == 6

    def test_dataframe_with_multiple_issues(self, scorer):
        """Test DataFrame with multiple quality issues."""
        df = pd.DataFrame({
            "id": [1, 2, 2, 3],  # Duplicates in potential PK
            "name": [None, "B", "B", "D"],  # Null value
            "empty": [None, None, None, None],  # Empty column
            "value": [1, 2, 3, 100]  # Potential outlier
        })

        report = scorer.generate_quality_report(df, "test")

        # Should detect multiple issues
        assert len(report["issues"]) >= 3

        # Score should be penalized
        assert report["score"] < 90
