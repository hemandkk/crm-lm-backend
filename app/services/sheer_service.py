import asyncio
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class GoogleSheetsService:
    """
    Appends a row to a Google Sheet when a new prospect is created.
    All operations are non-blocking — called from FastAPI BackgroundTasks.
    """

    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
    MAX_RETRIES = 3

    def __init__(
        self,
        credentials_path: str,
        spreadsheet_id: str,
        sheet_name: str = "Leads",
    ) -> None:
        self.spreadsheet_id = spreadsheet_id
        self.sheet_name = sheet_name
        self._credentials_path = credentials_path
        self._service = None

    def _build_service(self):
        """Lazy init — only imports google libs when actually needed."""
        if self._service:
            return self._service

        if not os.path.exists(self._credentials_path):
            raise FileNotFoundError(
                f"Google Sheets credentials not found at {self._credentials_path}"
            )

        from google.oauth2 import service_account  # type: ignore
        from googleapiclient.discovery import build  # type: ignore

        creds = service_account.Credentials.from_service_account_file(
            self._credentials_path, scopes=self.SCOPES
        )
        self._service = build("sheets", "v4", credentials=creds, cache_discovery=False)
        return self._service

    def _prospect_to_row(self, data: dict[str, Any]) -> list[Any]:
        return [
            data.get("created_at", ""),
            data.get("prospect_id", ""),
            data.get("name", ""),
            data.get("email", ""),
            data.get("phone", ""),
            data.get("father_name", ""),
            data.get("mother_name", ""),
            data.get("course_name", ""),
            data.get("specialization", ""),
            data.get("address", ""),
            data.get("estimated_value", ""),
            data.get("delivery_address", ""),
            data.get("delivery_date", ""),
            data.get("notes", ""),
            data.get("assigned_employee", ""),
            data.get("aadhaar_url", ""),
            data.get("photo_url", ""),
            data.get("sslc_url", ""),
            data.get("degree_url", ""),
            data.get("agreement_url", ""),
        ]

    async def append_prospect(self, prospect_data: dict[str, Any]) -> bool:
        """
        Append one row to the sheet.  Retries up to MAX_RETRIES times with
        exponential back-off.  Always returns without raising — caller logs result.
        """
        if not self.spreadsheet_id:
            logger.warning("GOOGLE_SPREADSHEET_ID not configured — skipping sync")
            return False

        values = [self._prospect_to_row(prospect_data)]

        for attempt in range(self.MAX_RETRIES):
            try:
                service = self._build_service()
                service.spreadsheets().values().append(
                    spreadsheetId=self.spreadsheet_id,
                    range=f"{self.sheet_name}!A1",
                    valueInputOption="USER_ENTERED",
                    insertDataOption="INSERT_ROWS",
                    body={"values": values},
                ).execute()
                logger.info(
                    "Sheets sync OK — prospect %s", prospect_data.get("prospect_id")
                )
                return True
            except Exception as exc:
                wait = 2**attempt
                logger.warning(
                    "Sheets sync attempt %d/%d failed: %s — retrying in %ds",
                    attempt + 1,
                    self.MAX_RETRIES,
                    exc,
                    wait,
                )
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(wait)

        logger.error(
            "Sheets sync permanently failed for prospect %s",
            prospect_data.get("prospect_id"),
        )
        return False

    async def ensure_header_row(self) -> None:
        """Write column headers if the sheet is empty."""
        headers = [
            [
                "Date", "Prospect ID", "Name", "Email", "Phone",
                "Father Name", "Mother Name", "Course", "Specialization",
                "Address", "Deal Value", "Delivery Address", "Delivery Date",
                "Notes", "Assigned Employee",
                "Aadhaar URL", "Photo URL", "SSLC URL", "Degree URL", "Agreement URL",
            ]
        ]
        try:
            service = self._build_service()
            # Check if A1 already has data
            result = service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f"{self.sheet_name}!A1",
            ).execute()
            if not result.get("values"):
                service.spreadsheets().values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range=f"{self.sheet_name}!A1",
                    valueInputOption="USER_ENTERED",
                    body={"values": headers},
                ).execute()
                logger.info("Sheets header row written")
        except Exception as exc:
            logger.warning("Could not write header row: %s", exc)


def build_sheets_service() -> GoogleSheetsService:
    from app.core.config import settings
    return GoogleSheetsService(
        credentials_path=settings.GOOGLE_SHEETS_CREDENTIALS_PATH,
        spreadsheet_id=settings.GOOGLE_SPREADSHEET_ID,
        sheet_name=settings.GOOGLE_SHEET_NAME,
    )


# Singleton — instantiated once at startup
sheets_service = build_sheets_service()