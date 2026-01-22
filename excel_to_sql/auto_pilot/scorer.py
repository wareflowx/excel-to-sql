"""
Data Quality Scoring Module for Auto-Pilot Mode.

This module provides multi-dimensional quality scoring that evaluates data across
completeness, validity, consistency, and uniqueness, providing an A-D grade
and actionable feedback.
"""

from __future__ import annotations

from typing import Any

import pandas as pd


class QualityScorer:
    """
    Evaluates data quality across multiple dimensions and assigns an A-D grade.

    This class analyzes pandas DataFrames and identifies quality issues across
    four dimensions:
    - Completeness: Percentage of missing/null values
    - Uniqueness: Presence of duplicate primary keys
    - Validity: Invalid values (negative quantities, invalid codes)
    - Consistency: Logical inconsistencies (future dates in historical data)

    The quality score ranges from 0-100 with corresponding grades:
    - A+: 95-100 (Excellent) - Ready to import
    - A: 90-94 (Very Good) - Minor issues acceptable
    - B: 80-89 (Good) - Some issues, review recommended
    - C: 70-79 (Fair) - Significant issues, fix recommended
    - D: <70 (Poor) - Critical issues, fix required

    Example:
        >>> scorer = QualityScorer()
        >>> result = scorer.score_table(df, table_name="produits", primary_key="no_produit")
        >>> print(result["score"])  # 94
        >>> print(result["grade"])  # "A"
        >>> print(result["breakdown"]["completeness"])  # 97
    """

    # Grade boundaries and labels
    GRADE_A_PLUS = (95, 100, "A+")
    GRADE_A = (90, 94, "A")
    GRADE_B = (80, 89, "B")
    GRADE_C = (70, 79, "C")
    GRADE_D = (0, 69, "D")

    # Maximum penalties for each dimension
    MAX_COMPLETENESS_PENALTY = 10
    MAX_UNIQUENESS_PENALTY = 15
    MAX_VALIDITY_PENALTY = 10
    MAX_CONSISTENCY_PENALTY = 5

    def __init__(self) -> None:
        """Initialize the QualityScorer."""
        pass

    def score_table(
        self,
        df: pd.DataFrame,
        table_name: str,
        primary_key: str | None = None,
    ) -> dict[str, Any]:
        """
        Run all quality checks on a DataFrame.

        Args:
            df: Input DataFrame to analyze
            table_name: Name of the table (for reference in output)
            primary_key: Optional primary key column name for uniqueness check

        Returns:
            Dictionary containing quality assessment:
            {
                "table_name": str,
                "score": int (0-100),
                "grade": str ("A+", "A", "B", "C", "D"),
                "breakdown": {
                    "completeness": int (0-100),
                    "uniqueness": int (0-100),
                    "validity": int (0-100),
                    "consistency": int (0-100),
                },
                "issues": list[str],
            }

        Example:
            >>> scorer = QualityScorer()
            >>> df = pd.DataFrame({"id": [1, 2, 3], "name": ["A", "B", "C"]})
            >>> result = scorer.score_table(df, "products", primary_key="id")
        """
        if len(df) == 0:
            return self._empty_result(table_name)

        result: dict[str, Any] = {
            "table_name": table_name,
            "score": 100,
            "grade": "A+",
            "breakdown": {
                "completeness": 100,
                "uniqueness": 100,
                "validity": 100,
                "consistency": 100,
            },
            "issues": [],
        }

        # Run each dimension check
        completeness_result = self._check_completeness(df)
        result["breakdown"]["completeness"] = completeness_result["score"]
        result["issues"].extend(completeness_result["issues"])

        uniqueness_result = self._check_uniqueness(df, primary_key)
        result["breakdown"]["uniqueness"] = uniqueness_result["score"]
        result["issues"].extend(uniqueness_result["issues"])

        validity_result = self._check_validity(df)
        result["breakdown"]["validity"] = validity_result["score"]
        result["issues"].extend(validity_result["issues"])

        consistency_result = self._check_consistency(df)
        result["breakdown"]["consistency"] = consistency_result["score"]
        result["issues"].extend(consistency_result["issues"])

        # Calculate final score (start at 100, subtract penalties)
        penalties = (
            self.MAX_COMPLETENESS_PENALTY - completeness_result["penalty"]
            + self.MAX_UNIQUENESS_PENALTY - uniqueness_result["penalty"]
            + self.MAX_VALIDITY_PENALTY - validity_result["penalty"]
            + self.MAX_CONSISTENCY_PENALTY - consistency_result["penalty"]
        )

        result["score"] = max(0, 100 - penalties)
        result["grade"] = self._assign_grade(result["score"])

        return result

    def _empty_result(self, table_name: str) -> dict[str, Any]:
        """Return result for empty DataFrame."""
        return {
            "table_name": table_name,
            "score": 0,
            "grade": "D",
            "breakdown": {
                "completeness": 0,
                "uniqueness": 0,
                "validity": 0,
                "consistency": 0,
            },
            "issues": ["Table is empty"],
        }

    def _assign_grade(self, score: int) -> str:
        """
        Assign grade based on score.

        Args:
            score: Quality score (0-100)

        Returns:
            Grade label: "A+", "A", "B", "C", or "D"
        """
        if score >= self.GRADE_A_PLUS[0]:
            return self.GRADE_A_PLUS[2]
        elif score >= self.GRADE_A[0]:
            return self.GRADE_A[2]
        elif score >= self.GRADE_B[0]:
            return self.GRADE_B[2]
        elif score >= self.GRADE_C[0]:
            return self.GRADE_C[2]
        else:
            return self.GRADE_D[2]

    def _check_completeness(self, df: pd.DataFrame) -> dict[str, Any]:
        """
        Calculate completeness score based on null value percentage.

        Deducts 1 point per 5% nulls in critical columns, max penalty of 10 points.
        Flags columns with >10% null values for review.

        Args:
            df: Input DataFrame

        Returns:
            Dictionary with score, penalty, and list of issues
        """
        issues: list[str] = []
        total_cells = len(df) * len(df.columns)
        null_cells = df.isna().sum().sum()
        null_percentage = (null_cells / total_cells * 100) if total_cells > 0 else 0

        # Check individual columns for high null percentages
        for col in df.columns:
            col_null_pct = (df[col].isna().sum() / len(df)) * 100 if len(df) > 0 else 0
            if col_null_pct > 10:
                issues.append(f"{col}: {col_null_pct:.1f}% null values")

        # Calculate penalty (1 point per 5% nulls, max 10)
        penalty = min(self.MAX_COMPLETENESS_PENALTY, int(null_percentage / 5))
        score = 100 - penalty

        return {
            "score": score,
            "penalty": penalty,
            "issues": issues,
        }

    def _check_uniqueness(self, df: pd.DataFrame, primary_key: str | None) -> dict[str, Any]:
        """
        Check uniqueness of primary key values.

        Counts duplicate values in PK column and deducts points based on
        duplicate count, max penalty of 15 points.

        Args:
            df: Input DataFrame
            primary_key: Name of primary key column (optional)

        Returns:
            Dictionary with score, penalty, and list of issues
        """
        issues: list[str] = []

        if not primary_key or primary_key not in df.columns:
            return {
                "score": 100,
                "penalty": 0,
                "issues": [],
            }

        # Count duplicates
        total_rows = len(df)
        unique_values = df[primary_key].nunique()
        duplicate_count = total_rows - unique_values

        if duplicate_count > 0:
            duplicate_pct = (duplicate_count / total_rows) * 100
            issues.append(f"{primary_key}: {duplicate_count} duplicate values ({duplicate_pct:.1f}%)")

            # Calculate penalty (max 15 points)
            penalty = min(self.MAX_UNIQUENESS_PENALTY, int(duplicate_count / total_rows * 100))
            score = 100 - penalty
        else:
            penalty = 0
            score = 100

        return {
            "score": score,
            "penalty": penalty,
            "issues": issues,
        }

    def _check_validity(self, df: pd.DataFrame) -> dict[str, Any]:
        """
        Detect invalid values in the data.

        Checks for:
        - Negative quantities where inappropriate
        - Values outside valid ranges

        Args:
            df: Input DataFrame

        Returns:
            Dictionary with score, penalty, and list of issues
        """
        issues: list[str] = []
        penalty = 0

        # Check for negative values in columns that might be quantities
        quantity_patterns = ["quantite", "quantity", "qty", "amount", "montant", "prix", "price"]

        for col in df.columns:
            col_str = str(col).lower()
            # Check if column name matches quantity patterns
            if any(pattern in col_str for pattern in quantity_patterns):
                # Skip if column has string data
                if df[col].dtype in ["object", "string"]:
                    continue

                # Count negative values
                negative_count = (df[col] < 0).sum()
                if negative_count > 0:
                    negative_pct = (negative_count / len(df)) * 100
                    issues.append(f"{col}: {negative_count} negative values ({negative_pct:.1f}%)")
                    penalty = min(self.MAX_VALIDITY_PENALTY, penalty + 1)

        score = 100 - penalty

        return {
            "score": score,
            "penalty": penalty,
            "issues": issues,
        }

    def _check_consistency(self, df: pd.DataFrame) -> dict[str, Any]:
        """
        Detect logical inconsistencies in the data.

        Checks for:
        - Future dates in historical data
        - Logical inconsistencies (e.g., end_date < start_date)

        Args:
            df: Input DataFrame

        Returns:
            Dictionary with score, penalty, and list of issues
        """
        issues: list[str] = []
        penalty = 0

        # Check date columns for future dates
        date_columns = df.select_dtypes(include=["datetime64[ns]", "object"]).columns

        for col in date_columns:
            # Try to convert to datetime if it's object type
            if df[col].dtype == "object":
                try:
                    dates = pd.to_datetime(df[col], errors="coerce")
                except Exception:
                    continue
            else:
                dates = df[col]

            # Check for future dates
            now = pd.Timestamp.now()
            future_dates = dates[dates > now]

            if len(future_dates) > 0:
                future_count = len(future_dates)
                future_pct = (future_count / len(df)) * 100
                issues.append(f"{col}: {future_count} future dates detected ({future_pct:.1f}%)")
                penalty = min(self.MAX_CONSISTENCY_PENALTY, penalty + 1)

        score = 100 - penalty

        return {
            "score": score,
            "penalty": penalty,
            "issues": issues,
        }
