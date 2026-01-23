"""
Excel file entity for reading and hashing Excel files.

Encapsulates file I/O and content-based hashing for incremental imports.
"""

from pathlib import Path
from typing import Optional, List, Dict, Literal

import pandas as pd
import hashlib

from excel_to_sql.exceptions import ExcelFileError


class ExcelFile:
    """
    Represents an Excel file with reading and hashing capabilities.

    Usage:
        file = ExcelFile("path/to/file.xlsx")
        df = file.read()                    # Read as DataFrame
        hash_value = file.content_hash      # Get SHA-256 of content
        sheets = file.list_sheets()         # List all sheet names
    """

    def __init__(self, path: Path | str) -> None:
        """
        Initialize Excel file entity.

        Args:
            path: Path to Excel file
        """
        self._path = Path(path)
        self._hash_cache: Optional[Dict[str, str]] = None

    # ──────────────────────────────────────────────────────────────
    # PROPERTIES
    # ──────────────────────────────────────────────────────────────

    @property
    def path(self) -> Path:
        """File path."""
        return self._path

    @property
    def name(self) -> str:
        """Filename with extension."""
        return self._path.name

    @property
    def exists(self) -> bool:
        """Check if file exists."""
        return self._path.exists()

    @property
    def sheet_names(self) -> List[str]:
        """Get list of sheet names."""
        try:
            excel_file = pd.ExcelFile(self._path, engine="openpyxl")
            return excel_file.sheet_names
        except Exception:
            return []

    # ──────────────────────────────────────────────────────────────
    # PUBLIC METHODS
    # ──────────────────────────────────────────────────────────────

    def read(
        self,
        sheet_name: str | None = None,
        header: int | None | Literal["detect"] = 0
    ) -> pd.DataFrame:
        """
        Read Excel file as DataFrame.

        Args:
            sheet_name: Sheet to read (default: first sheet)
            header: Row to use as header (0-based). Use "detect" for automatic
                    header detection. None means no header. (default: 0)

        Returns:
            Pandas DataFrame with raw data

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is invalid/corrupted
        """
        if not self.exists:
            raise FileNotFoundError(f"Excel file not found: {self._path}")

        if self._path.suffix.lower() not in {".xlsx", ".xls"}:
            raise ValueError(f"Not an Excel file: {self._path}")

        try:
            # Use sheet_name=0 to read first sheet when None specified
            # (pd.read_excel returns dict when sheet_name=None)
            actual_sheet = 0 if sheet_name is None else sheet_name

            # Handle automatic header detection
            if header == "detect":
                from excel_to_sql.auto_pilot.header_detector import HeaderDetector
                detector = HeaderDetector()
                header_row = detector.detect_header_row(self._path, actual_sheet)
                return pd.read_excel(self._path, sheet_name=actual_sheet, header=header_row, engine="openpyxl")

            return pd.read_excel(self._path, sheet_name=actual_sheet, header=header, engine="openpyxl")
        except (FileNotFoundError, PermissionError):
            # Re-raise filesystem errors as-is
            raise
        except pd.errors.EmptyDataError as e:
            raise ExcelFileError(
                f"Excel file is empty: {self._path.name}",
                file_path=str(self._path),
                operation="read"
            ) from e
        except pd.errors.ParserError as e:
            raise ExcelFileError(
                f"Invalid Excel file format: {self._path.name}",
                file_path=str(self._path),
                operation="read"
            ) from e
        except Exception as e:
            raise ExcelFileError(
                f"Failed to read Excel file: {self._path.name}",
                file_path=str(self._path),
                operation="read"
            ) from e

    def read_all_sheets(self) -> Dict[str, pd.DataFrame]:
        """
        Read all sheets from Excel file.

        Returns:
            Dictionary mapping sheet names to DataFrames

        Example:
            file = ExcelFile("data.xlsx")
            sheets = file.read_all_sheets()
            for sheet_name, df in sheets.items():
                print(f"{sheet_name}: {len(df)} rows")
        """
        if not self.exists:
            raise FileNotFoundError(f"Excel file not found: {self._path}")

        try:
            return pd.read_excel(self._path, sheet_name=None, engine="openpyxl")
        except (FileNotFoundError, PermissionError):
            raise
        except pd.errors.EmptyDataError as e:
            raise ExcelFileError(
                f"Excel file is empty: {self._path.name}",
                file_path=str(self._path),
                operation="read_all_sheets"
            ) from e
        except pd.errors.ParserError as e:
            raise ExcelFileError(
                f"Invalid Excel file format: {self._path.name}",
                file_path=str(self._path),
                operation="read_all_sheets"
            ) from e
        except Exception as e:
            raise ExcelFileError(
                f"Failed to read Excel file: {self._path.name}",
                file_path=str(self._path),
                operation="read_all_sheets"
            ) from e

    def read_sheets(self, sheet_names: List[str]) -> Dict[str, pd.DataFrame]:
        """
        Read specific sheets from Excel file.

        Args:
            sheet_names: List of sheet names to read

        Returns:
            Dictionary mapping sheet names to DataFrames

        Example:
            file = ExcelFile("data.xlsx")
            sheets = file.read_sheets(["Products", "Categories"])
        """
        result = {}

        for sheet_name in sheet_names:
            try:
                result[sheet_name] = self.read(sheet_name)
            except ExcelFileError:
                # Re-raise ExcelFileError as-is
                raise
            except Exception as e:
                raise ExcelFileError(
                    f"Failed to read sheet: {sheet_name}",
                    file_path=str(self._path),
                    operation="read_sheets"
                ) from e

        return result

    @property
    def content_hash(self) -> str:
        """
        SHA-256 hash of DataFrame content (not file bytes).

        Lazy computation - cached after first call.
        Hash is based on first sheet content.

        Deprecated: Use get_content_hash(sheet_name) for multi-sheet support.
        """
        if self._hash_cache is None:
            df = self.read()
            self._hash_cache = {"": self._compute_hash(df)}
        return self._hash_cache.get("", "")

    def get_content_hash(self, sheet_name: Optional[str] = None) -> str:
        """
        Get SHA-256 hash of a specific sheet's content.

        Args:
            sheet_name: Sheet name (default: first sheet)

        Returns:
            Hexadecimal SHA-256 hash

        Hash is based on:
        - Column names (sorted)
        - Row values (converted to string)
        - NOT file metadata (mtime, size)
        """
        cache_key = sheet_name or ""

        if self._hash_cache is None:
            self._hash_cache = {}

        if cache_key not in self._hash_cache:
            df = self.read(sheet_name)
            self._hash_cache[cache_key] = self._compute_hash(df)

        return self._hash_cache[cache_key]

    def get_combined_hash(self) -> str:
        """
        Get combined hash of all sheets.

        Returns:
            Hexadecimal SHA-256 hash of all sheets combined

        Useful for detecting changes in multi-sheet files.
        """
        sheets = self.read_all_sheets()

        # Combine all sheets into one hash
        combined = ""
        for sheet_name in sorted(sheets.keys()):
            sheet_hash = self._compute_hash(sheets[sheet_name])
            combined += f"{sheet_name}:{sheet_hash}"

        return hashlib.sha256(combined.encode()).hexdigest()

    def validate(self) -> bool:
        """
        Quick validation that file is readable.

        Returns:
            True if file can be read

        Doesn't load full data - just checks:
        - File exists
        - Has .xlsx extension
        - Can read sheet names
        """
        if not self.exists:
            return False

        if self._path.suffix.lower() not in {".xlsx", ".xls"}:
            return False

        try:
            pd.ExcelFile(self._path, engine="openpyxl")
            return True
        except Exception:
            return False

    # ──────────────────────────────────────────────────────────────
    # PRIVATE METHODS
    # ──────────────────────────────────────────────────────────────

    def _compute_hash(self, df: pd.DataFrame) -> str:
        """
        Compute hash of DataFrame content.

        Args:
            df: DataFrame to hash

        Returns:
            Hexadecimal SHA-256 hash

        Hash computation strategy:
        - Sort columns for consistency
        - Convert to string representation
        - Hash the resulting string

        This ensures that same data produces same hash,
        regardless of original column order.
        """
        # Sort columns for consistency
        df_sorted = df[sorted(df.columns)]

        # Convert to string representation
        content_str = df_sorted.to_string(index=True)

        # Compute SHA-256
        return hashlib.sha256(content_str.encode()).hexdigest()
