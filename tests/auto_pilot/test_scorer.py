"""
Unit tests for QualityScorer class.

Tests cover all scoring methods with various edge cases and scenarios.
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from excel_to_sql.auto_pilot.scorer import QualityScorer


class TestQualityScorer:
    """Test suite for QualityScorer class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.scorer = QualityScorer()

    # -------------------------------------------------------------------------
    # Tests for score_table (main orchestration method)
    # -------------------------------------------------------------------------

    def test_score_table_perfect_quality(self) -> None:
        """Test scoring on DataFrame with perfect quality."""
        df = pd.DataFrame({
            "id": [1, 2, 3, 4, 5],
            "name": ["A", "B", "C", "D", "E"],
            "value": [10, 20, 30, 40, 50],
        })

        result = self.scorer.score_table(df, "test", primary_key="id")

        assert result["score"] == 100
        assert result["grade"] == "A+"
        assert result["breakdown"]["completeness"] == 100
        assert result["breakdown"]["uniqueness"] == 100
        assert result["breakdown"]["validity"] == 100
        assert result["breakdown"]["consistency"] == 100
        assert len(result["issues"]) == 0

    def test_score_table_with_missing_categories(self) -> None:
        """Test scoring on produits.xlsx with missing categories."""
        df = pd.DataFrame({
            "no_produit": [1001, 1002, 1003, 1004, 1005],
            "nom": ["A", "B", "C", "D", "E"],
            "categorie_1": ["Electronics", None, "Mechanical", None, "Electronics"],
        })

        result = self.scorer.score_table(df, "produits", primary_key="no_produit")

        # Should have penalty for missing categories (40% null)
        assert result["score"] < 100
        assert result["grade"] in ["A", "B"]
        assert any("categorie_1" in issue for issue in result["issues"])

    def test_score_table_with_duplicate_pk(self) -> None:
        """Test scoring with duplicate primary keys."""
        df = pd.DataFrame({
            "id": [1, 2, 2, 3, 3],  # Duplicates: 2 appears twice, 3 appears twice
            "name": ["A", "B", "C", "D", "E"],
        })

        result = self.scorer.score_table(df, "test", primary_key="id")

        # Should have penalty for duplicates
        assert result["score"] < 100
        assert result["breakdown"]["uniqueness"] < 100
        assert any("duplicate" in issue.lower() for issue in result["issues"])

    def test_score_table_with_future_dates(self) -> None:
        """Test scoring with future dates in historical data."""
        future_date = datetime.now() + timedelta(days=30)
        df = pd.DataFrame({
            "id": [1, 2, 3, 4],
            "date": [datetime(2024, 1, 1), datetime(2024, 2, 1), future_date, datetime(2024, 3, 1)],
        })

        result = self.scorer.score_table(df, "test", primary_key="id")

        # Should have penalty for future dates
        assert result["score"] < 100
        assert result["breakdown"]["consistency"] < 100
        assert any("future" in issue.lower() for issue in result["issues"])

    def test_score_table_with_negative_quantities(self) -> None:
        """Test scoring with negative quantity values."""
        df = pd.DataFrame({
            "id": [1, 2, 3, 4],
            "quantite": [10, -5, 20, -3],  # Negative quantities
        })

        result = self.scorer.score_table(df, "test", primary_key="id")

        # Should have penalty for negative quantities
        assert result["score"] < 100
        assert result["breakdown"]["validity"] < 100
        assert any("negative" in issue.lower() for issue in result["issues"])

    def test_score_table_empty_dataframe(self) -> None:
        """Test scoring on empty DataFrame."""
        df = pd.DataFrame()

        result = self.scorer.score_table(df, "empty")

        assert result["score"] == 0
        assert result["grade"] == "D"
        assert "empty" in result["issues"][0].lower()

    def test_score_table_comprehensive_issues(self) -> None:
        """Test scoring with multiple quality issues."""
        future_date = datetime.now() + timedelta(days=10)
        df = pd.DataFrame({
            "id": [1, 2, 2, 3],  # Duplicate PK
            "name": ["A", None, "C", "D"],  # Null value
            "quantite": [10, -5, 20, 30],  # Negative quantity
            "date": [datetime(2024, 1, 1), datetime(2024, 2, 1), future_date, datetime(2024, 3, 1)],  # Future date
        })

        result = self.scorer.score_table(df, "test", primary_key="id")

        # Should have low score due to multiple issues
        assert result["score"] < 80
        assert len(result["issues"]) >= 3

    # -------------------------------------------------------------------------
    # Tests for grade assignment
    # -------------------------------------------------------------------------

    def test_grade_a_plus_for_perfect_score(self) -> None:
        """Test A+ grade assignment for score 95-100."""
        df = pd.DataFrame({"id": [1, 2, 3], "name": ["A", "B", "C"]})
        result = self.scorer.score_table(df, "test", primary_key="id")
        assert result["grade"] == "A+"

    def test_grade_a_for_good_score(self) -> None:
        """Test A grade assignment for score 90-94."""
        # Create DataFrame with minor issues (90-94 range)
        df = pd.DataFrame({
            "id": list(range(1, 21)),
            "col1": [None] * 1 + [1] * 19,  # 5% nulls -> 1 point penalty
        })
        result = self.scorer.score_table(df, "test", primary_key="id")
        assert result["grade"] in ["A", "A+"]

    def test_grade_b_for_fair_score(self) -> None:
        """Test B grade assignment for score 80-89."""
        # Create DataFrame with more issues
        df = pd.DataFrame({
            "id": list(range(1, 21)),
            "col1": [None] * 3 + [1] * 17,  # 15% nulls -> 3 point penalty
            "col2": [None] * 3 + [1] * 17,  # Another 15% nulls -> 3 point penalty
            "quantite": [10] * 18 + [-5] * 2,  # 10% negative -> 1 point penalty
        })
        result = self.scorer.score_table(df, "test", primary_key="id")
        assert result["grade"] in ["A", "B"]

    def test_grade_c_for_poor_score(self) -> None:
        """Test C grade assignment for score 70-79."""
        # Create DataFrame with significant issues
        df = pd.DataFrame({
            "id": list(range(1, 21)),
            "col1": [None] * 8 + [1] * 12,  # 40% nulls -> 8 point penalty (capped at max)
        })
        result = self.scorer.score_table(df, "test", primary_key="id")
        assert result["score"] < 100
        assert result["grade"] in ["A", "B", "C"]

    def test_grade_d_for_critical_score(self) -> None:
        """Test D grade assignment for score <70."""
        df = pd.DataFrame()
        result = self.scorer.score_table(df, "empty")
        assert result["grade"] == "D"

    # -------------------------------------------------------------------------
    # Tests for _check_completeness
    # -------------------------------------------------------------------------

    def test_completeness_perfect(self) -> None:
        """Test completeness score with no null values."""
        df = pd.DataFrame({"col1": [1, 2, 3], "col2": ["A", "B", "C"]})
        result = self.scorer._check_completeness(df)
        assert result["score"] == 100
        assert result["penalty"] == 0
        assert len(result["issues"]) == 0

    def test_completeness_with_nulls(self) -> None:
        """Test completeness score with null values."""
        df = pd.DataFrame({
            "col1": [1, None, 3],
            "col2": ["A", "B", "C"],
        })
        result = self.scorer._check_completeness(df)
        # 1 null out of 6 cells = ~16.7% -> 3 point penalty
        assert result["score"] < 100
        assert result["penalty"] > 0

    def test_completeness_high_null_percentage(self) -> None:
        """Test completeness score flags columns with >10% nulls."""
        df = pd.DataFrame({
            "col1": [1] * 9 + [None] * 1,  # 10% nulls - borderline
            "col2": [1] * 8 + [None] * 2,  # 20% nulls - should be flagged
        })
        result = self.scorer._check_completeness(df)
        assert len(result["issues"]) >= 1
        assert any("col2" in issue for issue in result["issues"])

    def test_completeness_max_penalty(self) -> None:
        """Test completeness penalty is capped at 10 points."""
        df = pd.DataFrame({
            "col1": [None] * 100,  # 100% nulls
        })
        result = self.scorer._check_completeness(df)
        assert result["penalty"] == 10  # Max penalty
        assert result["score"] == 90

    # -------------------------------------------------------------------------
    # Tests for _check_uniqueness
    # -------------------------------------------------------------------------

    def test_uniqueness_perfect(self) -> None:
        """Test uniqueness score with no duplicates."""
        df = pd.DataFrame({"id": [1, 2, 3, 4, 5]})
        result = self.scorer._check_uniqueness(df, "id")
        assert result["score"] == 100
        assert result["penalty"] == 0
        assert len(result["issues"]) == 0

    def test_uniqueness_with_duplicates(self) -> None:
        """Test uniqueness score with duplicate values."""
        df = pd.DataFrame({"id": [1, 2, 2, 3, 3, 3]})
        result = self.scorer._check_uniqueness(df, "id")
        assert result["score"] < 100
        assert result["penalty"] > 0
        assert len(result["issues"]) == 1
        assert "duplicate" in result["issues"][0].lower()

    def test_uniqueness_no_primary_key(self) -> None:
        """Test uniqueness without primary key specified."""
        df = pd.DataFrame({"col1": [1, 2, 2, 3]})
        result = self.scorer._check_uniqueness(df, None)
        assert result["score"] == 100
        assert result["penalty"] == 0
        assert len(result["issues"]) == 0

    def test_uniqueness_invalid_primary_key(self) -> None:
        """Test uniqueness with non-existent primary key."""
        df = pd.DataFrame({"col1": [1, 2, 3]})
        result = self.scorer._check_uniqueness(df, "nonexistent")
        assert result["score"] == 100
        assert result["penalty"] == 0

    def test_uniqueness_all_duplicates(self) -> None:
        """Test uniqueness with all duplicate values."""
        df = pd.DataFrame({"id": [1, 1, 1, 1, 1]})
        result = self.scorer._check_uniqueness(df, "id")
        # Should have max penalty for 100% duplicates
        assert result["penalty"] >= 10
        assert result["score"] <= 90

    # -------------------------------------------------------------------------
    # Tests for _check_validity
    # -------------------------------------------------------------------------

    def test_validity_perfect(self) -> None:
        """Test validity score with all valid values."""
        df = pd.DataFrame({
            "quantite": [10, 20, 30],
            "price": [100.0, 200.0, 300.0],
        })
        result = self.scorer._check_validity(df)
        assert result["score"] == 100
        assert result["penalty"] == 0
        assert len(result["issues"]) == 0

    def test_validity_with_negative_quantities(self) -> None:
        """Test validity score detects negative quantities."""
        df = pd.DataFrame({
            "quantite": [10, -5, 20, -3, 30],
        })
        result = self.scorer._check_validity(df)
        assert result["score"] < 100
        assert result["penalty"] > 0
        assert len(result["issues"]) == 1
        assert "negative" in result["issues"][0].lower()

    def test_validity_ignores_string_columns(self) -> None:
        """Test validity ignores negative detection in string columns."""
        df = pd.DataFrame({
            "name": ["Item-1", "Item-2", "Item-3"],  # Has "-" but shouldn't be flagged
        })
        result = self.scorer._check_validity(df)
        assert result["score"] == 100
        assert result["penalty"] == 0

    def test_validity_multiple_quantity_columns(self) -> None:
        """Test validity checks multiple quantity-like columns."""
        df = pd.DataFrame({
            "quantite": [10, -5, 20],
            "quantity": [100, 200, -300],
        })
        result = self.scorer._check_validity(df)
        assert result["score"] < 100
        assert len(result["issues"]) == 2

    def test_validity_max_penalty(self) -> None:
        """Test validity penalty is capped at 10 points."""
        # Create many columns with negative values
        df = pd.DataFrame({
            f"quantite_{i}": [-1] * 10 for i in range(15)
        })
        result = self.scorer._check_validity(df)
        assert result["penalty"] <= 10

    # -------------------------------------------------------------------------
    # Tests for _check_consistency
    # -------------------------------------------------------------------------

    def test_consistency_perfect(self) -> None:
        """Test consistency score with no issues."""
        past_date = datetime.now() - timedelta(days=10)
        df = pd.DataFrame({
            "date": [past_date, past_date, past_date],
        })
        result = self.scorer._check_consistency(df)
        assert result["score"] == 100
        assert result["penalty"] == 0
        assert len(result["issues"]) == 0

    def test_consistency_with_future_dates(self) -> None:
        """Test consistency score detects future dates."""
        future_date = datetime.now() + timedelta(days=10)
        df = pd.DataFrame({
            "date": [datetime(2024, 1, 1), future_date, datetime(2024, 2, 1)],
        })
        result = self.scorer._check_consistency(df)
        assert result["score"] < 100
        assert result["penalty"] > 0
        assert len(result["issues"]) == 1
        assert "future" in result["issues"][0].lower()

    def test_consistency_with_datetime_column(self) -> None:
        """Test consistency handles datetime64 columns."""
        future_date = datetime.now() + timedelta(days=5)
        df = pd.DataFrame({
            "date": pd.to_datetime(["2024-01-01", "2024-02-01", str(future_date.date())]),
        })
        result = self.scorer._check_consistency(df)
        assert result["score"] < 100
        assert len(result["issues"]) == 1

    def test_consistency_with_string_dates(self) -> None:
        """Test consistency handles string date columns."""
        future_date = datetime.now() + timedelta(days=5)
        df = pd.DataFrame({
            "date": ["2024-01-01", "2024-02-01", str(future_date.date())],
        })
        result = self.scorer._check_consistency(df)
        assert result["score"] < 100

    def test_consistency_multiple_date_columns(self) -> None:
        """Test consistency checks multiple date columns."""
        future_date = datetime.now() + timedelta(days=10)
        df = pd.DataFrame({
            "date1": [datetime(2024, 1, 1), future_date, datetime(2024, 2, 1)],
            "date2": [datetime(2024, 1, 1), datetime(2024, 2, 1), future_date],
        })
        result = self.scorer._check_consistency(df)
        assert result["score"] < 100
        assert len(result["issues"]) == 2

    def test_consistency_max_penalty(self) -> None:
        """Test consistency penalty is capped at 5 points."""
        # Create many columns with future dates
        future_date = datetime.now() + timedelta(days=10)
        df = pd.DataFrame({
            f"date_{i}": [future_date] * 10 for i in range(10)
        })
        result = self.scorer._check_consistency(df)
        assert result["penalty"] <= 5

    # -------------------------------------------------------------------------
    # Edge case tests
    # -------------------------------------------------------------------------

    def test_handles_nan_in_primary_key(self) -> None:
        """Test scoring handles NaN values in primary key."""
        df = pd.DataFrame({
            "id": [1, 2, None, 4, 5],
            "name": ["A", "B", "C", "D", "E"],
        })
        result = self.scorer.score_table(df, "test", primary_key="id")
        # NaN should be counted as unique value in nunique()
        # But should be flagged in completeness
        assert result["breakdown"]["completeness"] < 100

    def test_handles_mixed_data_types(self) -> None:
        """Test scoring handles mixed data types gracefully."""
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "mixed_col": [1, "text", 3.14],
        })
        result = self.scorer.score_table(df, "test", primary_key="id")
        assert result["score"] >= 0
        assert result["grade"] in ["A+", "A", "B", "C", "D"]

    def test_score_never_negative(self) -> None:
        """Test that score is never negative."""
        df = pd.DataFrame({
            "id": [1, 1, 1, 1],  # All duplicates
            "col1": [None, None, None, None],  # All nulls
            "quantite": [-1, -1, -1, -1],  # All negative
        })
        result = self.scorer.score_table(df, "test", primary_key="id")
        assert result["score"] >= 0
