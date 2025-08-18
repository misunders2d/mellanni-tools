from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import gspread, time

import streamlit as st

from data import get_user_email

CREDS_FILE = st.secrets["gsheets-access"]
SPREADSHEET_ID = "1SpFOarsVGLiVIYhslAYCVZwAGBHqn55j0LJMAn_Wwv0"


def read_write_google_sheet(records: list) -> None:  # Optional[types.Content]:
    """
    Write data to a Google Spreadsheet.
    A function used at the end of the conversation to record all the session state keys

    Parameters:
    - reecords - a list of records to be written to the spreadsheet.

    Returns:
    - None.
    """

    date = time.strftime("%Y-%m-%d %H:%M:%S")
    full_records = [get_user_email(), date] + records

    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_info(CREDS_FILE, scopes=scope)
        client = gspread.authorize(creds)

        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        worksheet = spreadsheet.worksheet("Sheet1")
        read_data = worksheet.get("A:E")
        update_range = f"A{len(read_data)+1}:Z{len(read_data)+1}"

        worksheet.update([full_records], update_range)

        print({"status": "success"})
        return None

    except gspread.exceptions.SpreadsheetNotFound:
        print({"status": "Error: Spreadsheet not found. Check the spreadsheet ID."})
        return None
    except gspread.exceptions.WorksheetNotFound:
        print({"status": "Error: Worksheet not found. Check the sheet name."})
        return None
    except Exception as e:
        print({"status": f"Error: {str(e)}"})
        return None
