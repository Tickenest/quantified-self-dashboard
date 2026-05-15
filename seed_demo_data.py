"""
seed_demo_data.py

Loads the Quincy Everyman synthetic dataset (data/quincy_everyman.csv) into
the demo Google Sheet via the Google Sheets API.

Prerequisites:
    pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client

Authentication:
    1. Go to https://console.cloud.google.com
    2. Create a project and enable the Google Sheets API
    3. Create OAuth 2.0 credentials (Desktop app)
    4. Download the credentials JSON and save as credentials.json in this directory
    5. Run this script — it will open a browser for authentication on first run
    6. A token.json file will be created for subsequent runs

Usage:
    python seed_demo_data.py

Configuration:
    Set SPREADSHEET_ID and SHEET_NAME below to match your demo Google Sheet.
"""

import csv
import os

SPREADSHEET_ID = "1tMq20IZEma540FVa6WTqOz5JO4T8ZibfzTvemfePiM8"
SHEET_NAME = "quincy_everyman_final"
CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "quincy_everyman.csv")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def get_credentials():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return creds


def load_csv():
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        return list(reader)


def seed_sheet(rows):
    from googleapiclient.discovery import build

    creds = get_credentials()
    service = build("sheets", "v4", credentials=creds)
    sheet = service.spreadsheets()

    # Clear existing content
    print(f"Clearing {SHEET_NAME}...")
    sheet.values().clear(
        spreadsheetId=SPREADSHEET_ID,
        range=SHEET_NAME,
    ).execute()

    # Write rows
    print(f"Writing {len(rows)} rows (including header)...")
    sheet.values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!A1",
        valueInputOption="RAW",
        body={"values": rows},
    ).execute()

    print("Done.")


if __name__ == "__main__":
    rows = load_csv()
    print(f"Loaded {len(rows)} rows from {CSV_PATH}")
    seed_sheet(rows)
