"""
Custom exception hierarchy for excel-to-sql.

This module defines a structured exception hierarchy for better error handling
and user-friendly error messages throughout the excel-to-sql application.

Exception Hierarchy:
    ExcelToSqlError (base)
    ├── ExcelFileError (Excel file operations)
    ├── ConfigurationError (Configuration issues)
    ├── ValidationError (Data validation failures)
    └── DatabaseError (Database operation failures)
"""

from __future__ import annotations


class ExcelToSqlError(Exception):
    """
    Base exception for all excel-to-sql errors.

    All custom exceptions inherit from this class, allowing for easy
    catching of any excel-to-sql specific error.

    Example:
        >>> try:
        ...     # some excel-to-sql operation
        ... except ExcelToSqlError as e:
        ...     print(f"excel-to-sql error: {e}")
    """

    def __init__(self, message: str, *, context: dict[str, str] | None = None) -> None:
        """
        Initialize an excel-to-sql error.

        Args:
            message: Human-readable error message
            context: Optional dictionary with additional context (file_name, operation, etc.)
        """
        super().__init__(message)
        self.context = context or {}
        self.message = message

    def __str__(self) -> str:
        """Return string representation with context if available."""
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.message} ({context_str})"
        return self.message

    def to_dict(self) -> dict[str, str]:
        """Convert exception to dictionary for serialization."""
        return {
            "type": self.__class__.__name__,
            "message": self.message,
            "context": self.context,
        }


class ExcelFileError(ExcelToSqlError):
    """
    Raised when Excel file operations fail.

    This exception is used for errors related to reading, writing, or
    processing Excel files.

    Attributes:
        file_path: Path to the Excel file that caused the error
        operation: The operation being performed (read, write, validate, etc.)

    Example:
        >>> raise ExcelFileError("Failed to read Excel file", file_path="data.xlsx", operation="read")
    """

    def __init__(
        self,
        message: str,
        *,
        file_path: str | None = None,
        operation: str | None = None,
        **kwargs
    ) -> None:
        """
        Initialize an Excel file error.

        Args:
            message: Human-readable error message
            file_path: Path to the Excel file
            operation: The operation being performed
            **kwargs: Additional context
        """
        context = {"file_path": str(file_path)} if file_path else {}
        if operation:
            context["operation"] = operation
        context.update(kwargs)

        super().__init__(message, context=context)
        self.file_path = file_path
        self.operation = operation


class ConfigurationError(ExcelToSqlError):
    """
    Raised when configuration is invalid, missing, or malformed.

    This exception covers errors related to project configuration, mapping files,
    and other configuration-related issues.

    Attributes:
        config_file: Path to the configuration file (if applicable)
        config_key: The configuration key that caused the error (if applicable)

    Example:
        >>> raise ConfigurationError("Missing required field: primary_key", config_key="primary_key")
    """

    def __init__(
        self,
        message: str,
        *,
        config_file: str | None = None,
        config_key: str | None = None,
        **kwargs
    ) -> None:
        """
        Initialize a configuration error.

        Args:
            message: Human-readable error message
            config_file: Path to the configuration file
            config_key: The configuration key that caused the error
            **kwargs: Additional context
        """
        context = {}
        if config_file:
            context["config_file"] = config_file
        if config_key:
            context["config_key"] = config_key
        context.update(kwargs)

        super().__init__(message, context=context)
        self.config_file = config_file
        self.config_key = config_key


class ValidationError(ExcelToSqlError):
    """
    Raised when data validation fails.

    This exception is used when data fails validation checks, such as
    required field validation, type validation, or custom validation rules.

    Attributes:
        field: The field that failed validation
        value: The value that failed validation
        rule: The validation rule that was violated

    Example:
        >>> raise ValidationError(
        ...     "Email is required",
        ...     field="email",
        ...     value=None,
        ...     rule="required"
        ... )
    """

    def __init__(
        self,
        message: str,
        *,
        field: str | None = None,
        value: str | None = None,
        rule: str | None = None,
        **kwargs
    ) -> None:
        """
        Initialize a validation error.

        Args:
            message: Human-readable error message
            field: The field that failed validation
            value: The value that failed validation
            rule: The validation rule that was violated
            **kwargs: Additional context
        """
        context = {}
        if field:
            context["field"] = field
        if value is not None:
            context["value"] = str(value)
        if rule:
            context["rule"] = rule
        context.update(kwargs)

        super().__init__(message, context=context)
        self.field = field
        self.value = value
        self.rule = rule


class DatabaseError(ExcelToSqlError):
    """
    Raised when database operations fail.

    This exception covers errors related to database connections, queries,
    transactions, and other database-related issues.

    Attributes:
        table: The database table involved (if applicable)
        operation: The database operation being performed
        sql_error: The underlying database error message

    Example:
        >>> raise DatabaseError(
        ...     "Failed to insert row",
        ...     table="products",
        ...     operation="insert",
        ...     sql_error="UNIQUE constraint failed"
        ... )
    """

    def __init__(
        self,
        message: str,
        *,
        table: str | None = None,
        operation: str | None = None,
        sql_error: str | None = None,
        **kwargs
    ) -> None:
        """
        Initialize a database error.

        Args:
            message: Human-readable error message
            table: The database table involved
            operation: The database operation being performed
            sql_error: The underlying database error message
            **kwargs: Additional context
        """
        context = {}
        if table:
            context["table"] = table
        if operation:
            context["operation"] = operation
        if sql_error:
            context["sql_error"] = sql_error
        context.update(kwargs)

        super().__init__(message, context=context)
        self.table = table
        self.operation = operation
        self.sql_error = sql_error
