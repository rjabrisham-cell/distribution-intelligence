"""
Excel / CSV Parsing Service.

Stateless service for reading and parsing Excel/CSV files.

Contract with ImportService
----------------------------

parse() returns:

    {
        "file_name": str,
        "headers": list[str],
        "rows": list[dict[str, Any]],
        "total_rows": int,
    }

preview() returns:

    {
        "file_name": str,
        "headers": list[str],
        "sample_rows": list[dict[str, Any]],
        "total_rows": int,
    }

The service intentionally keeps raw cell values as strings where
possible so that validation remains responsible for type conversion.
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.exceptions import FileProcessingError


logger = logging.getLogger(__name__)


# ==============================================================
# Supported file extensions
# ==============================================================

SUPPORTED_EXTENSIONS = {
    ".xlsx",
    ".xls",
    ".csv",
}


# ==============================================================
# Excel engines
# ==============================================================

EXCEL_XLSX_ENGINE = "openpyxl"
EXCEL_XLS_ENGINE = "xlrd"


class ExcelService:
    """
    Stateless Excel/CSV parsing service.

    Examples
    --------

        parsed = ExcelService().parse(file_path)

        preview = ExcelService().preview(
            file_path,
            sample_size=10,
        )

    parse() and preview() return dictionaries that are directly
    compatible with ImportService.
    """

    # ==========================================================
    # Public API
    # ==========================================================

    @classmethod
    def parse(
        cls,
        file_path: str | Path,
        sheet_name: str | int = 0,
    ) -> dict[str, Any]:
        """
        Parse the complete file.

        Returns
        -------
        dict
            {
                "file_name": str,
                "headers": list[str],
                "rows": list[dict[str, Any]],
                "total_rows": int,
            }

        Notes
        -----
        Cell values are read as strings whenever possible to avoid
        silent type coercion before validation.
        """

        path = cls._validate_file_path(file_path)

        try:
            df = cls._read_file(
                path,
                sheet_name=sheet_name,
                dtype=str,
            )

            df = cls._clean_dataframe(df)

            headers = cls._extract_headers(df)
            rows = cls._dataframe_to_records(df)

            total_rows = len(rows)

            logger.info(
                "Parsed file: %s → %d rows, %d columns",
                path.name,
                total_rows,
                len(headers),
            )

            return {
                "file_name": path.name,
                "headers": headers,
                "rows": rows,
                "total_rows": total_rows,
            }

        except FileProcessingError:
            raise

        except Exception as exc:
            logger.exception(
                "Unexpected error while parsing file: %s",
                path,
            )

            raise FileProcessingError(
                f"Could not parse file '{path.name}': {exc}"
            ) from exc

    # ----------------------------------------------------------

    @classmethod
    def get_headers(
        cls,
        file_path: str | Path,
        sheet_name: str | int = 0,
    ) -> list[str]:
        """
        Return the column headers from the file.
        """

        path = cls._validate_file_path(file_path)

        try:
            df = cls._read_file(
                path,
                sheet_name=sheet_name,
                nrows=0,
            )

            return cls._extract_headers(df)

        except FileProcessingError:
            raise

        except Exception as exc:
            logger.exception(
                "Failed to read headers from file: %s",
                path,
            )

            raise FileProcessingError(
                f"Could not read headers from "
                f"'{path.name}': {exc}"
            ) from exc

    # ----------------------------------------------------------

    @classmethod
    def preview(
        cls,
        file_path: str | Path,
        nrows: int = 10,
        sample_size: int | None = None,
        sheet_name: str | int = 0,
    ) -> dict[str, Any]:
        """
        Generate a file preview.

        Parameters
        ----------
        file_path:
            Excel/CSV file path.

        nrows:
            Number of sample rows.

        sample_size:
            Backward-compatible alias for nrows.

        sheet_name:
            Excel sheet name or index.

        Returns
        -------
        dict
            {
                "file_name": str,
                "headers": list[str],
                "sample_rows": list[dict[str, Any]],
                "total_rows": int,
            }

        Important
        ---------
        The returned structure is intentionally a dictionary because
        ImportService.preview_import() consumes it using .get().
        """

        path = cls._validate_file_path(file_path)

        if sample_size is not None:
            nrows = sample_size

        if nrows < 0:
            raise FileProcessingError(
                "Preview row count cannot be negative."
            )

        try:
            # ------------------------------------------------------
            # Read sample
            # ------------------------------------------------------

            sample_df = cls._read_file(
                path,
                sheet_name=sheet_name,
                nrows=nrows,
                dtype=str,
            )

            sample_df = cls._clean_dataframe(sample_df)

            headers = cls._extract_headers(sample_df)

            sample_rows = cls._dataframe_to_records(
                sample_df,
            )

            # ------------------------------------------------------
            # Determine total row count
            # ------------------------------------------------------

            total_rows = cls.fast_row_count(
                path,
                sheet_name=sheet_name,
            )

            logger.info(
                "Generated preview: %s → %d total rows, "
                "%d sample rows",
                path.name,
                total_rows,
                len(sample_rows),
            )

            return {
                "file_name": path.name,
                "headers": headers,
                "sample_rows": sample_rows,
                "total_rows": total_rows,
            }

        except FileProcessingError:
            raise

        except Exception as exc:
            logger.exception(
                "Failed to generate preview for file: %s",
                path,
            )

            raise FileProcessingError(
                f"Could not generate preview for "
                f"'{path.name}': {exc}"
            ) from exc

    # ----------------------------------------------------------

    @classmethod
    def fast_row_count(
        cls,
        file_path: str | Path,
        sheet_name: str | int = 0,
    ) -> int:
        """
        Return the number of data rows.

        CSV
        ---
        Uses pandas-compatible CSV parsing rather than simply counting
        physical lines. This correctly handles quoted fields containing
        newlines.

        Excel
        -----
        Reads only the first column to minimize memory usage.
        """

        path = cls._validate_file_path(file_path)

        suffix = path.suffix.lower()

        try:
            # ------------------------------------------------------
            # CSV
            # ------------------------------------------------------

            if suffix == ".csv":
                return cls._count_csv_rows(path)

            # ------------------------------------------------------
            # Excel
            # ------------------------------------------------------

            df = cls._read_file(
                path,
                sheet_name=sheet_name,
                usecols=[0],
            )

            return len(df)

        except FileProcessingError:
            raise

        except Exception as exc:
            logger.exception(
                "Failed to count rows in file: %s",
                path,
            )

            raise FileProcessingError(
                f"Could not count rows in "
                f"'{path.name}': {exc}"
            ) from exc

    # ==========================================================
    # Internal file handling
    # ==========================================================

    @staticmethod
    def _validate_file_path(
        file_path: str | Path,
    ) -> Path:
        """
        Validate file path and supported extension.
        """

        path = Path(file_path)

        suffix = path.suffix.lower()

        if suffix not in SUPPORTED_EXTENSIONS:
            raise FileProcessingError(
                f"Unsupported file format: '{suffix}'. "
                f"Supported: "
                f"{', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            )

        if not path.exists():
            raise FileProcessingError(
                f"File not found: {path}"
            )

        if not path.is_file():
            raise FileProcessingError(
                f"Path is not a file: {path}"
            )

        return path

    # ----------------------------------------------------------

    @classmethod
    def _read_file(
        cls,
        file_path: str | Path,
        **kwargs: Any,
    ) -> pd.DataFrame:
        """
        Internal file reader.

        Selects the appropriate parser according to extension.
        """

        path = cls._validate_file_path(file_path)

        suffix = path.suffix.lower()

        try:
            # ------------------------------------------------------
            # CSV
            # ------------------------------------------------------

            if suffix == ".csv":
                kwargs.pop("sheet_name", None)  # Excel-only option from parse().
                return cls._read_csv(
                    path,
                    **kwargs,
                )

            # ------------------------------------------------------
            # XLSX
            # ------------------------------------------------------

            if suffix == ".xlsx":
                return pd.read_excel(
                    path,
                    engine=EXCEL_XLSX_ENGINE,
                    **kwargs,
                )

            # ------------------------------------------------------
            # XLS
            # ------------------------------------------------------

            if suffix == ".xls":
                return pd.read_excel(
                    path,
                    engine=EXCEL_XLS_ENGINE,
                    **kwargs,
                )

            raise FileProcessingError(
                f"Unsupported file format: '{suffix}'."
            )

        except FileProcessingError:
            raise

        except ImportError as exc:
            if suffix == ".xls":
                raise FileProcessingError(
                    "Reading .xls files requires the "
                    "'xlrd' package. "
                    "Install it with: pip install xlrd"
                ) from exc

            if suffix == ".xlsx":
                raise FileProcessingError(
                    "Reading .xlsx files requires the "
                    "'openpyxl' package."
                ) from exc

            raise FileProcessingError(
                f"Required package for '{suffix}' "
                f"is not installed."
            ) from exc

        except Exception as exc:
            logger.exception(
                "Failed to read file: %s",
                path,
            )

            raise FileProcessingError(
                f"Could not parse file "
                f"'{path.name}': {exc}"
            ) from exc

    # ----------------------------------------------------------

    @staticmethod
    def _read_csv(
        file_path: Path,
        **kwargs: Any,
    ) -> pd.DataFrame:
        """
        Read CSV with reasonable encoding fallback.

        The parser first attempts UTF-8 with BOM support and then
        falls back to cp1256, which is useful for Persian Windows
        CSV files.
        """

        encodings = (
            "utf-8-sig",
            "utf-8",
            "cp1256",
        )

        last_error: Exception | None = None

        for encoding in encodings:
            try:
                return pd.read_csv(
                    file_path,
                    encoding=encoding,
                    **kwargs,
                )

            except UnicodeDecodeError as exc:
                last_error = exc
                continue

        if last_error is not None:
            raise FileProcessingError(
                f"Could not decode CSV file "
                f"'{file_path.name}'. "
                f"Tried UTF-8 and cp1256."
            ) from last_error

        raise FileProcessingError(
            f"Could not read CSV file "
            f"'{file_path.name}'."
        )

    # ==========================================================
    # DataFrame normalization
    # ==========================================================

    @staticmethod
    def _clean_dataframe(
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Normalize DataFrame values.

        - Replace NaN/NaT with None.
        - Normalize column names to strings.
        """

        if df is None:
            raise FileProcessingError(
                "Excel parser returned no data."
            )

        df = df.copy()

        # ------------------------------------------------------
        # Normalize column names
        # ------------------------------------------------------

        df.columns = [
            str(column).strip()
            if column is not None
            else ""
            for column in df.columns
        ]

        # ------------------------------------------------------
        # Replace pandas missing values with None
        # ------------------------------------------------------

        df = df.astype(object)
        df = df.where(pd.notnull(df), None)

        return df

    # ----------------------------------------------------------

    @staticmethod
    def _extract_headers(
        df: pd.DataFrame,
    ) -> list[str]:
        """
        Extract normalized column headers.
        """

        return [
            str(column).strip()
            if column is not None
            else ""
            for column in df.columns
        ]

    # ----------------------------------------------------------

    @staticmethod
    def _dataframe_to_records(
        df: pd.DataFrame,
    ) -> list[dict[str, Any]]:
        """
        Convert DataFrame rows to JSON-safe dictionaries.

        All pandas/numpy scalar values are converted to native
        Python values where possible.
        """

        if df.empty:
            return []

        records = df.to_dict(
            orient="records",
        )

        normalized_records: list[dict[str, Any]] = []

        for record in records:
            normalized: dict[str, Any] = {}

            for key, value in record.items():

                # --------------------------------------------------
                # pandas / numpy scalar
                # --------------------------------------------------

                if hasattr(value, "item"):
                    try:
                        value = value.item()
                    except (ValueError, TypeError):
                        pass

                # --------------------------------------------------
                # pandas timestamp
                # --------------------------------------------------

                if isinstance(
                    value,
                    pd.Timestamp,
                ):
                    value = value.isoformat()

                # --------------------------------------------------
                # pandas NaT
                # --------------------------------------------------

                if value is pd.NaT:
                    value = None

                normalized[str(key)] = value

            normalized_records.append(normalized)

        return normalized_records

    # ==========================================================
    # CSV row counting
    # ==========================================================

    @staticmethod
    def _count_csv_rows(
        file_path: Path,
    ) -> int:
        """
        Count actual CSV data records.

        Uses csv.reader so quoted newlines inside a field are
        not incorrectly counted as multiple records.
        """

        encodings = (
            "utf-8-sig",
            "utf-8",
            "cp1256",
        )

        last_error: Exception | None = None

        for encoding in encodings:

            try:
                with file_path.open(
                    "r",
                    encoding=encoding,
                    newline="",
                ) as file:

                    reader = csv.reader(file)

                    # Skip header
                    try:
                        next(reader)
                    except StopIteration:
                        return 0

                    return sum(
                        1
                        for _ in reader
                    )

            except UnicodeDecodeError as exc:
                last_error = exc
                continue

        if last_error is not None:
            raise FileProcessingError(
                f"Could not decode CSV file "
                f"'{file_path.name}' "
                f"while counting rows."
            ) from last_error

        raise FileProcessingError(
            f"Could not count rows in "
            f"'{file_path.name}'."
        )