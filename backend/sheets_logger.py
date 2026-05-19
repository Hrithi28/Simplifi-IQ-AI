"""
sheets_logger.py — BONUS: Append lead data to Google Sheets.
Also handles Google Drive PDF archiving.
"""

import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def _get_credentials():
    """Load Google service account credentials from env or file."""
    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    creds_file = os.environ.get("GOOGLE_CREDENTIALS_FILE", "credentials.json")
    
    if creds_json:
        import tempfile
        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        tmp.write(creds_json)
        tmp.close()
        return tmp.name
    elif os.path.exists(creds_file):
        return creds_file
    return None


def log_to_sheets(lead: dict, status: str) -> bool:
    """Append lead entry to Google Sheets (if configured)."""
    sheet_id = os.environ.get("GOOGLE_SHEET_ID", "")
    creds_path = _get_credentials()
    
    if not (sheet_id and creds_path):
        logger.info("Sheets logging skipped — GOOGLE_SHEET_ID or credentials not configured")
        return False

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        creds = service_account.Credentials.from_service_account_file(creds_path, scopes=SCOPES)
        service = build('sheets', 'v4', credentials=creds)

        row = [[
            lead.get("name", ""),
            lead.get("email", ""),
            lead.get("company", ""),
            lead.get("industry", ""),
            lead.get("role", ""),
            lead.get("company_size", ""),
            lead.get("website", ""),
            lead.get("pain_points", ""),
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            status,
        ]]

        # Ensure header row exists
        try:
            result = service.spreadsheets().values().get(
                spreadsheetId=sheet_id, range="Leads!A1:J1"
            ).execute()
            if not result.get("values"):
                header = [["Name", "Email", "Company", "Industry", "Role",
                           "Size", "Website", "Pain Points", "Submitted At", "Report Status"]]
                service.spreadsheets().values().update(
                    spreadsheetId=sheet_id, range="Leads!A1",
                    valueInputOption="RAW", body={"values": header}
                ).execute()
        except Exception:
            pass

        service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range="Leads!A:J",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": row},
        ).execute()

        logger.info(f"Lead logged to Google Sheets: {lead.get('email')}")
        return True

    except ImportError:
        logger.warning("google-api-python-client not installed — Sheets logging unavailable")
    except Exception as e:
        logger.error(f"Sheets logging failed: {e}")
    return False


def archive_to_drive(pdf_path: str, folder_id: str = None) -> str | None:
    """Upload PDF to Google Drive. Returns the file URL."""
    folder_id = folder_id or os.environ.get("GOOGLE_DRIVE_FOLDER_ID", "")
    creds_path = _get_credentials()

    if not folder_id:
        logger.warning("Drive archiving skipped — GOOGLE_DRIVE_FOLDER_ID not set in .env")
        return None
    if not creds_path:
        logger.warning("Drive archiving skipped — credentials.json not found")
        return None

    logger.info(f"Uploading to Drive folder: {folder_id}")

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        import os as _os

        # NOTE: scope must be drive (not drive.file) to upload into a shared folder
        SCOPES = ['https://www.googleapis.com/auth/drive']
        creds = service_account.Credentials.from_service_account_file(creds_path, scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)

        fname = _os.path.basename(pdf_path)
        meta = {"name": fname, "parents": [folder_id]}
        media = MediaFileUpload(pdf_path, mimetype="application/pdf", resumable=False)
        result = service.files().create(
            body=meta, media_body=media, fields="id,webViewLink"
        ).execute()
        url = result.get("webViewLink", "")
        file_id = result.get("id", "")
        logger.info(f"PDF archived to Drive — id: {file_id}  url: {url}")
        return url

    except Exception as e:
        logger.error(f"Drive archiving failed: {e}", exc_info=True)
    return None
