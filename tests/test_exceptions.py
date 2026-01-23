"""
Tests for custom exception classes.
"""

import pytest

from excel_to_sql.exceptions import (
    ExcelToSqlError,
    ExcelFileError,
    ConfigurationError,
    ValidationError,
    DatabaseError,
)


class TestExcelToSqlError:
    """Tests for base ExcelToSqlError exception."""

    def test_base_exception_creation(self):
        """Test creating base exception."""
        error = ExcelToSqlError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.context == {}

    def test_base_exception_with_context(self):
        """Test creating base exception with context."""
        error = ExcelToSqlError("Test error", context={"key": "value"})
        assert "key=value" in str(error)
        assert error.context == {"key": "value"}

    def test_base_exception_to_dict(self):
        """Test converting exception to dictionary."""
        error = ExcelToSqlError("Test error", context={"key": "value"})
        result = error.to_dict()
        assert result["type"] == "ExcelToSqlError"
        assert result["message"] == "Test error"
        assert result["context"] == {"key": "value"}


class TestExcelFileError:
    """Tests for ExcelFileError exception."""

    def test_file_error_creation(self):
        """Test creating Excel file error."""
        error = ExcelFileError("Failed to read")
        assert "Failed to read" in str(error)

    def test_file_error_with_file_path(self):
        """Test Excel file error with file path."""
        error = ExcelFileError(
            "Read failed",
            file_path="test.xlsx",
            operation="read"
        )
        assert error.file_path == "test.xlsx"
        assert error.operation == "read"
        assert "file_path=test.xlsx" in str(error)
        assert "operation=read" in str(error)

    def test_file_error_context(self):
        """Test Excel file error includes context."""
        error = ExcelFileError("Read failed", file_path="data.xlsx")
        assert error.context == {"file_path": "data.xlsx"}

    def test_file_error_to_dict(self):
        """Test converting ExcelFileError to dictionary."""
        error = ExcelFileError(
            "Read failed",
            file_path="test.xlsx",
            operation="read"
        )
        result = error.to_dict()
        assert result["type"] == "ExcelFileError"
        assert result["message"] == "Read failed"
        assert result["context"]["file_path"] == "test.xlsx"


class TestConfigurationError:
    """Tests for ConfigurationError exception."""

    def test_config_error_creation(self):
        """Test creating configuration error."""
        error = ConfigurationError("Invalid config")
        assert "Invalid config" in str(error)

    def test_config_error_with_config_file(self):
        """Test configuration error with config file."""
        error = ConfigurationError(
            "Config not found",
            config_file="mappings.json"
        )
        assert error.config_file == "mappings.json"
        assert "config_file=mappings.json" in str(error)

    def test_config_error_with_config_key(self):
        """Test configuration error with config key."""
        error = ConfigurationError(
            "Missing field",
            config_key="primary_key"
        )
        assert error.config_key == "primary_key"
        assert "config_key=primary_key" in str(error)

    def test_config_error_full_context(self):
        """Test configuration error with both file and key."""
        error = ConfigurationError(
            "Missing field",
            config_file="mappings.json",
            config_key="primary_key"
        )
        assert error.config_file == "mappings.json"
        assert error.config_key == "primary_key"
        assert "config_file=mappings.json" in str(error)
        assert "config_key=primary_key" in str(error)


class TestValidationError:
    """Tests for ValidationError exception."""

    def test_validation_error_creation(self):
        """Test creating validation error."""
        error = ValidationError("Validation failed")
        assert "Validation failed" in str(error)

    def test_validation_error_with_field(self):
        """Test validation error with field name."""
        error = ValidationError(
            "Required field",
            field="email"
        )
        assert error.field == "email"
        assert "field=email" in str(error)

    def test_validation_error_with_value(self):
        """Test validation error with value."""
        error = ValidationError(
            "Invalid value",
            field="age",
            value="invalid"
        )
        assert error.field == "age"
        assert error.value == "invalid"
        assert "value=invalid" in str(error)

    def test_validation_error_with_rule(self):
        """Test validation error with rule."""
        error = ValidationError(
            "Rule violated",
            field="email",
            rule="required"
        )
        assert error.rule == "required"
        assert "rule=required" in str(error)

    def test_validation_error_full_context(self):
        """Test validation error with all context."""
        error = ValidationError(
            "Email is required",
            field="email",
            value=None,
            rule="required"
        )
        assert error.field == "email"
        assert error.value is None
        assert error.rule == "required"


class TestDatabaseError:
    """Tests for DatabaseError exception."""

    def test_database_error_creation(self):
        """Test creating database error."""
        error = DatabaseError("Query failed")
        assert "Query failed" in str(error)

    def test_database_error_with_table(self):
        """Test database error with table name."""
        error = DatabaseError(
            "Table not found",
            table="products"
        )
        assert error.table == "products"
        assert "table=products" in str(error)

    def test_database_error_with_operation(self):
        """Test database error with operation."""
        error = DatabaseError(
            "Insert failed",
            table="products",
            operation="insert"
        )
        assert error.table == "products"
        assert error.operation == "insert"
        assert "operation=insert" in str(error)

    def test_database_error_with_sql_error(self):
        """Test database error with SQL error."""
        error = DatabaseError(
            "Query failed",
            table="products",
            sql_error="UNIQUE constraint failed"
        )
        assert error.sql_error == "UNIQUE constraint failed"
        assert "sql_error=UNIQUE constraint failed" in str(error)

    def test_database_error_full_context(self):
        """Test database error with all context."""
        error = DatabaseError(
            "Insert failed",
            table="products",
            operation="insert",
            sql_error="UNIQUE constraint failed: products.id"
        )
        assert error.table == "products"
        assert error.operation == "insert"
        assert error.sql_error == "UNIQUE constraint failed: products.id"
        assert "table=products" in str(error)
        assert "operation=insert" in str(error)


class TestExceptionHierarchy:
    """Tests for exception inheritance."""

    def test_all_exceptions_inherit_from_base(self):
        """Test that all custom exceptions inherit from ExcelToSqlError."""
        errors = [
            ExcelFileError("test"),
            ConfigurationError("test"),
            ValidationError("test"),
            DatabaseError("test"),
        ]

        for error in errors:
            assert isinstance(error, ExcelToSqlError)
            assert isinstance(error, Exception)

    def test_catch_base_exception(self):
        """Test catching base exception catches all custom exceptions."""
        caught = []

        try:
            raise ExcelFileError("File error")
        except ExcelToSqlError as e:
            caught.append("file_error")

        try:
            raise ConfigurationError("Config error")
        except ExcelToSqlError as e:
            caught.append("config_error")

        try:
            raise ValidationError("Validation error")
        except ExcelToSqlError as e:
            caught.append("validation_error")

        try:
            raise DatabaseError("Database error")
        except ExcelToSqlError as e:
            caught.append("database_error")

        assert len(caught) == 4

    def test_specific_exception_catch(self):
        """Test catching specific exception types."""
        caught = []

        try:
            raise ExcelFileError("File error")
        except ExcelFileError:
            caught.append("file")

        try:
            raise ConfigurationError("Config error")
        except ConfigurationError:
            caught.append("config")

        assert len(caught) == 2

    def test_exception_chaining(self):
        """Test exception chaining preserves original traceback."""
        try:
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise ExcelFileError("Wrapped error") from e
        except ExcelFileError as exc:
            assert exc.__cause__ is not None
            assert str(exc.__cause__) == "Original error"
