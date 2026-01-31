"""
Quality Scoring Module for Auto-Pilot Mode.

This module provides automatic quality assessment of pandas DataFrames,
typically Excel imports, to help users identify data quality issues early.

The QualityScorer analyzes DataFrames and generates comprehensive reports
including:
- Overall quality score (0-100)
- Letter grade (A-D)
- Detected issues with actionable recommendations
- Per-column statistics
"""

from __future__ import annotations

from typing import Any, Dict, List
import numpy as np

import pandas as pd


class QualityScorer:
    """
    Automatically assesses data quality of pandas DataFrames.

    This class analyzes DataFrames and generates quality reports that help
    identify common data issues such as missing values, duplicates, type
    inconsistencies, and outliers.

    The quality score is calculated based on multiple factors:
    - Null value percentage
    - Duplicate values
    - Type mismatches
    - Empty columns
    - Statistical outliers

    Example:
        >>> scorer = QualityScorer()
        >>> df = pd.DataFrame({"a": [1, 2, None], "b": ["x", "y", "z"]})
        >>> report = scorer.generate_quality_report(df, "products")
        >>> print(report["score"])
        85
        >>> print(report["grade"])
        'B'
        >>> print(report["issues"])
        ['Column "a" has 33.3% null values']
    """

    # Quality score thresholds
    GRADE_A_MIN = 90
    GRADE_B_MIN = 75
    GRADE_C_MIN = 60
    PERFECT_SCORE = 100

    # Deduction weights
    NULL_THRESHOLD = 10  # percentage
    NULL_DEDUCTION_PER_POINT = 0.5  # per percentage point over threshold
    DUPLICATE_DEDUCTION = 2  # per duplicate in potential PK
    TYPE_MISMATCH_DEDUCTION = 1  # per column
    EMPTY_COLUMN_DEDUCTION = 5  # per empty column
    OUTLIER_DEDUCTION = 0.1  # per outlier

    def __init__(
        self,
        null_threshold: int = 10,
        grade_a_min: int = 90,
        grade_b_min: int = 75,
        grade_c_min: int = 60
    ) -> None:
        """
        Initialize the QualityScorer.

        Args:
            null_threshold: Percentage of nulls that triggers deduction (default: 10%)
            grade_a_min: Minimum score for A grade (default: 90)
            grade_b_min: Minimum score for B grade (default: 75)
            grade_c_min: Minimum score for C grade (default: 60)
        """
        self.null_threshold = null_threshold
        self.grade_a_min = grade_a_min
        self.grade_b_min = grade_b_min
        self.grade_c_min = grade_c_min

    def generate_quality_report(
        self,
        df: pd.DataFrame,
        table_name: str
    ) -> Dict[str, Any]:
        """
        Generate comprehensive quality report for a DataFrame.

        Analyzes the DataFrame and returns a detailed quality report with
        score, grade, detected issues, and per-column statistics.

        Args:
            df: Input DataFrame to analyze
            table_name: Name of the table (for reference in report)

        Returns:
            Dictionary with the following structure:
            {
                "score": int,  # Quality score 0-100
                "grade": str,  # Letter grade: "A", "B", "C", "D", or "F"
                "issues": List[str],  # List of detected issue descriptions
                "column_stats": Dict[str, Dict[str, Any]],  # Per-column statistics
                "table_name": str,  # Table name
                "row_count": int,  # Number of rows
                "column_count": int,  # Number of columns
                "timestamp": str,  # ISO timestamp
            }

        Example:
            >>> scorer = QualityScorer()
            >>> df = pd.DataFrame({"a": [1, 2, None], "b": ["x", "y", "z"]})
            >>> report = scorer.generate_quality_report(df, "test")
            >>> report["score"]
            96
            >>> report["grade"]
            'A'
        """
        # Initialize report
        report: Dict[str, Any] = {
            "table_name": table_name,
            "row_count": len(df),
            "column_count": len(df.columns),
            "score": self.PERFECT_SCORE,
            "grade": "A",
            "issues": [],
            "column_stats": {},
        }

        if len(df) == 0:
            report["score"] = 0
            report["grade"] = "F"
            report["issues"].append("DataFrame is empty")
            return report

        # Analyze each column
        column_stats = self._analyze_columns(df)
        report["column_stats"] = column_stats

        # Detect quality issues
        issues = self._detect_issues(df, column_stats)
        report["issues"] = issues

        # Calculate quality score
        score = self._calculate_score(df, column_stats, issues)
        report["score"] = score

        # Assign grade
        grade = self._assign_grade(score)
        report["grade"] = grade

        return report

    def _analyze_columns(self, df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """
        Analyze each column and collect statistics.

        Args:
            df: Input DataFrame

        Returns:
            Dictionary mapping column names to their statistics
        """
        column_stats: Dict[str, Dict[str, Any]] = {}

        for col in df.columns:
            stats: Dict[str, Any] = {}

            # Basic info
            stats["dtype"] = str(df[col].dtype)
            stats["null_count"] = df[col].isna().sum()
            stats["null_percentage"] = (stats["null_count"] / len(df)) * 100
            stats["unique_count"] = df[col].nunique()
            stats["unique_percentage"] = (stats["unique_count"] / len(df)) * 100

            # Sample values (top 5)
            non_null_values = df[col].dropna()
            if len(non_null_values) > 0:
                sample_size = min(5, len(non_null_values))
                stats["sample_values"] = non_null_values.head(sample_size).tolist()
            else:
                stats["sample_values"] = []

            # Check if column is empty
            stats["is_empty"] = len(non_null_values) == 0

            # Detect potential primary key (high uniqueness)
            stats["is_potential_pk"] = stats["unique_percentage"] >= 95

            column_stats[col] = stats

        return column_stats

    def _detect_issues(
        self,
        df: pd.DataFrame,
        column_stats: Dict[str, Dict[str, Any]]
    ) -> List[str]:
        """
        Detect quality issues in the DataFrame.

        Args:
            df: Input DataFrame
            column_stats: Pre-computed column statistics

        Returns:
            List of detected issue descriptions
        """
        issues: List[str] = []

        # Check for null values
        for col, stats in column_stats.items():
            if stats["null_percentage"] > self.null_threshold:
                null_pct = stats["null_percentage"]
                issues.append(
                    f'Column "{col}" has {null_pct:.1f}% null values '
                    f'(threshold: {self.null_threshold}%)'
                )

        # Check for empty columns
        empty_cols = [
            col for col, stats in column_stats.items()
            if stats["is_empty"]
        ]
        if empty_cols:
            issues.append(f'Empty columns: {", ".join(empty_cols)}')

        # Check for duplicates in potential primary key columns
        potential_pk_cols = [
            col for col, stats in column_stats.items()
            if stats["is_potential_pk"]
        ]

        for col in potential_pk_cols:
            duplicate_count = len(df) - column_stats[col]["unique_count"]
            if duplicate_count > 0:
                issues.append(
                    f'Column "{col}" has {duplicate_count} duplicate values '
                    f'(potential primary key)'
                )

        # Check for type mismatches (object dtype with numeric-looking data)
        for col, stats in column_stats.items():
            if stats["dtype"] == "object" and not stats["is_empty"]:
                # Check if values look numeric
                sample_values = stats.get("sample_values", [])
                if sample_values:
                    numeric_looks = sum(
                        1 for val in sample_values
                        if isinstance(val, (int, float)) or str(val).replace(".", "").replace("-", "").isdigit()
                    )
                    if numeric_looks / len(sample_values) > 0.8:
                        issues.append(
                            f'Column "{col}" contains numeric-like values but is typed as object'
                        )

        # Check for outliers (3 sigma rule)
        for col, stats in column_stats.items():
            if stats["dtype"] in ["int64", "float64"] and not stats["is_empty"]:
                outliers = self._detect_outliers(df[col])
                if len(outliers) > 0:
                    outlier_pct = (len(outliers) / len(df)) * 100
                    issues.append(
                        f'Column "{col}" has {len(outliers)} outliers ({outlier_pct:.1f}%)'
                    )

        return issues

    def _detect_outliers(self, series: pd.Series) -> pd.Series:
        """
        Detect outliers using the 3-sigma rule.

        Values outside 3 standard deviations from the mean are considered outliers.
        Requires at least 10 data points for meaningful outlier detection.

        Args:
            series: pandas Series to analyze

        Returns:
            Boolean Series where True indicates an outlier
        """
        if len(series) == 0 or series.isna().all():
            return pd.Series([], dtype=bool)

        clean_series = series.dropna()
        if len(clean_series) < 10:  # Require at least 10 values
            return pd.Series([], dtype=bool)

        mean = clean_series.mean()
        std = clean_series.std()

        if std == 0:
            return pd.Series([False] * len(series))

        # 3-sigma rule
        lower_bound = mean - 3 * std
        upper_bound = mean + 3 * std

        outliers = (series < lower_bound) | (series > upper_bound)
        return outliers

    def _calculate_score(
        self,
        df: pd.DataFrame,
        column_stats: Dict[str, Dict[str, Any]],
        issues: List[str]
    ) -> int:
        """
        Calculate overall quality score (0-100).

        Score starts at 100 and deductions are applied for each issue.

        Args:
            df: Input DataFrame
            column_stats: Pre-computed column statistics
            issues: List of detected issues

        Returns:
            Quality score from 0 to 100
        """
        score = self.PERFECT_SCORE

        # Deduction for null values
        for stats in column_stats.values():
            null_pct = stats["null_percentage"]
            if null_pct > self.null_threshold:
                deduction = (null_pct - self.null_threshold) * self.NULL_DEDUCTION_PER_POINT
                score = max(0, score - deduction)

        # Deduction for duplicates in potential PK columns
        for col, stats in column_stats.items():
            if stats["is_potential_pk"]:
                duplicate_count = len(df) - stats["unique_count"]
                if duplicate_count > 0:
                    score = max(0, score - (duplicate_count * self.DUPLICATE_DEDUCTION))

        # Deduction for empty columns
        empty_count = sum(1 for stats in column_stats.values() if stats["is_empty"])
        score = max(0, score - (empty_count * self.EMPTY_COLUMN_DEDUCTION))

        # Deduction for outliers (capped)
        outlier_issues = [issue for issue in issues if "outliers" in issue.lower()]
        for issue in outlier_issues:
            # Extract outlier count from issue string
            import re
            match = re.search(r'(\d+) outliers', issue)
            if match:
                outlier_count = int(match.group(1))
                # Cap deduction at 10 points total for outliers
                deduction = min(outlier_count * self.OUTLIER_DEDUCTION, 10)
                score = max(0, score - deduction)

        return int(score)

    def _assign_grade(self, score: int) -> str:
        """
        Assign letter grade based on quality score.

        Args:
            score: Quality score (0-100)

        Returns:
            Letter grade: "A", "B", "C", "D", or "F"
        """
        if score >= self.grade_a_min:
            return "A"
        elif score >= self.grade_b_min:
            return "B"
        elif score >= self.grade_c_min:
            return "C"
        elif score > 0:
            return "D"
        else:
            return "F"

    def get_quality_thresholds(self) -> Dict[str, int]:
        """
        Get current quality score thresholds.

        Returns:
            Dictionary with threshold values
        """
        return {
            "grade_a_min": self.grade_a_min,
            "grade_b_min": self.grade_b_min,
            "grade_c_min": self.grade_c_min,
            "null_threshold": self.null_threshold,
        }

    def set_quality_thresholds(
        self,
        *,
        grade_a_min: int | None = None,
        grade_b_min: int | None = None,
        grade_c_min: int | None = None,
        null_threshold: int | None = None
    ) -> None:
        """
        Configure quality score thresholds.

        Args:
            grade_a_min: Minimum score for A grade (default: 90)
            grade_b_min: Minimum score for B grade (default: 75)
            grade_c_min: Minimum score for C grade (default: 60)
            null_threshold: Null percentage threshold (default: 10)
        """
        if grade_a_min is not None:
            self.grade_a_min = grade_a_min
        if grade_b_min is not None:
            self.grade_b_min = grade_b_min
        if grade_c_min is not None:
            self.grade_c_min = grade_c_min
        if null_threshold is not None:
            self.null_threshold = null_threshold
