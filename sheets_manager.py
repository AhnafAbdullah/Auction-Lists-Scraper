import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from logger import setup_logger  # Make sure logger.py exists in the same directory


class SheetsManager:
    def __init__(self, json_keyfile, spreadsheet_name):
        # Initialize logger first
        self.logger = setup_logger()

        self.scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        try:
            self.creds = ServiceAccountCredentials.from_json_keyfile_name(json_keyfile, self.scope)
            self.client = gspread.authorize(self.creds)
            self.sheet = self.client.open(spreadsheet_name).sheet1

            # Initialize sheet with headers and sorting
            if not self.sheet.row_values(1):
                self.sheet.append_row(["Auction Date", "County", "Address", "Link"])
                self._setup_sheet()

        except Exception as e:
            self.logger.error(f"Initialization failed: {str(e)}", exc_info=True)
            raise

    def _setup_sheet(self):
        """Configures sheet formatting and sorting"""
        try:
            self.sheet.freeze(rows=1)  # Freeze header row
            self.sheet.sort((1, 'asc'))  # Sort by Date (Column 1)
        except Exception as e:
            self.logger.error(f"Sheet setup failed: {str(e)}", exc_info=True)
            raise

    def add_auction(self, date, county, address, link):
        """Adds an auction row if it doesn't exist, then re-sorts"""
        try:
            existing = self.sheet.get_all_records()

            # Convert to datetime objects for accurate comparison
            new_date = datetime.strptime(date, "%m-%d-%Y")

            is_duplicate = any(
                datetime.strptime(row["Auction Date"], "%m-%d-%Y") == new_date
                and row["Address"].strip().lower() == address.strip().lower()
                and row["County"].strip().lower() == county.strip().lower()
                for row in existing
            )

            if not is_duplicate:
                self.sheet.append_row([date, county, address, link])
                self.sheet.sort((1, 'asc'))  # Re-sort after adding
                self.logger.info(f"Added auction: {date} | {county} | {address[:50]}...")
                return True

            self.logger.debug(f"Duplicate skipped: {date} | {county} | {address[:50]}...")
            return False

        except ValueError as e:
            self.logger.error(f"Date format error (County: {county}, Date: {date}): {str(e)}")
            return False
        except gspread.exceptions.APIError as e:
            self.logger.error(f"Google API error (County: {county}): {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error (County: {county}): {str(e)}", exc_info=True)
            return False