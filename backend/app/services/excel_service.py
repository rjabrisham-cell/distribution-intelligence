"""
Excel Parsing Service.

Stateless service for reading and parsing Excel/CSV files.
Uses pandas for robust type detection and data extraction.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.exceptions import FileProcessingError

logger = logging.getLogger(__name__)

# Supported file extensions
SUPPORTED_EXTENSIONS = {".xlsx", ".xls", ".csv"}


class ExcelService:
    """
    Stateless Excel/CSV parsing service.

    Usage:
        raw = ExcelService.parse(file_path)
        headers = ExcelService.get_headers(file_path)
        preview = ExcelService.preview(file_path, nrows=10)
    """

    @staticmethod
    def _read_file(file_path: str | Path, **kwargs: Any) -> pd.DataFrame:
        """Internal: read a file into a DataFrame with appropriate engine."""
        file_path = Path(file_path)
        suffix = file_path.suffix.lower()

        if suffix not in SUPPORTED_EXTENSIONS:
            raise FileProcessingError(
                f"Unsupported file format: '{suffix}'. "
                f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            )

        if not file_path.exists():
            raise FileProcessingError(f"File not found: {file_path}")

        try:
            if suffix == ".csv":
                return pd.read_csv(file_path, **kwargs)
            else:
                return pd.read_excel(file_path, engine="openpyxl", **kwargs)
        except Exception as exc:
            logger.exception("Failed to read file: %s", file_path)
            raise FileProcessingError(
                f"Could not parse file '{file_path.name}': {exc}"
            ) from exc

    @classmethod
    def parse(
        cls,
        file_path: str | Path,
        sheet_name: str | int = 0,
    ) -> pd.DataFrame:
        """
        Parse entire file and return a DataFrame.

        Args:
            file_path: Path to Excel/CSV file.
            sheet_name: Sheet name or index (Excel only).

        Returns:
            DataFrame with raw data; all columns are strings to avoid
            silent type coercion before validation.
        """
        df = cls._read_file(file_path, sheet_name=sheet_name, dtype=str)
        # Replace NaN with None for cleaner downstream handling
        df = df.where(pd.notnull(df), None)
        logger.info("Parsed file: %s → %d rows, %d columns",
                     Path(file_path).name, len(df), len(df.columns))
        return df

    @classmethod
    def get_headers(cls, file_path: str | Path, sheet_name: str | int = 0) -> list[str]:
        """Return list of column headers from the file."""
        df = cls._read_file(file_path, sheet_name=sheet_name, nrows=0)
        return list(df.columns)

    @classmethod
    def preview(
        cls,
        file_path: str | Path,
        nrows: int = 10,
        sheet_name: str | int = 0,
    ) -> tuple[list[str], list[dict[str, Any]]]:
        """
        Return headers and a sample of rows for preview.

        Returns:
            Tuple of (headers, sample_rows) where sample_rows
            is a list of dicts (each dict = one row).
        """
        df = cls._read_file(file_path, sheet_name=sheet_name, nrows=nrows, dtype=str)
        df = df.where(pd.notnull(df), None)
        headers = list(df.columns)
        sample = df.head(nrows).to_dict(orient="records")
        # Convert numpy types to native Python for JSON-safety
        sample = [
            {k: (v.item() if hasattr(v, "item") else v) for k, v in row.items()}
            for row in sample
        ]
        return headers, sample

    @classmethod
    def fast_row_count(cls, file_path: str | Path) -> int:
        """
        Get total row count without loading full file into memory.
        For CSV: count lines; for Excel: read only one column.
        """
        file_path = Path(file_path)
        suffix = file_path.suffix.lower()

        if suffix == ".csv":
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                # Subtract 1 for header
                return max(0, sum(1 for _ in f) - 1)
        else:
            # Excel: read only first column to minimise memory
            df = pd.read_excel(file_path, engine="openpyxl", usecols=[0])
            return len(df)
