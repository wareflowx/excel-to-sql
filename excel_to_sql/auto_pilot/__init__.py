"""
Auto-Pilot Mode for Zero-Configuration Excel Import.

This module provides intelligent detection and configuration capabilities
for automatically importing Excel files into SQLite databases.
"""

from excel_to_sql.auto_pilot.detector import PatternDetector
from excel_to_sql.auto_pilot.scorer import QualityScorer
from excel_to_sql.auto_pilot.generator import ConfigGenerator

__all__ = ["PatternDetector", "QualityScorer", "ConfigGenerator"]
