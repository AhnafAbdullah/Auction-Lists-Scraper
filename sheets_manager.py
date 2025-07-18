import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from logger import setup_logger
from gspread_formatting import *


class SheetsManager:
    def __init__(self, json_keyfile, spreadsheet_name):
        self.logger = setup_logger()
        self.scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        try:
            self.creds = ServiceAccountCredentials.from_json_keyfile_name(json_keyfile, self.scope)
            self.client = gspread.authorize(self.creds)
            self.sheet = self.client.open(spreadsheet_name).sheet1

            if not self.sheet.row_values(1):
                self.sheet.append_row(["Auction Date", "County", "Address", "Link"])
                self._setup_sheet()

            self.clear_all_highlights()

        except Exception as e:
            self.logger.error(f"Initialization failed: {str(e)}", exc_info=True)
            raise

    def _setup_sheet(self):
        """Configures sheet formatting and sorting"""
        try:
            header_fmt = CellFormat(
                backgroundColor=Color(0.2, 0.6, 0.8),
                textFormat=TextFormat(bold=True, foregroundColor=Color(1, 1, 1))  # Added missing parenthesis
            )
            format_cell_range(self.sheet, "A1:D1", header_fmt)

            self.sheet.freeze(rows=1)
            self.sheet.sort((1, 'asc'))
        except Exception as e:
            self.logger.error(f"Sheet setup failed: {str(e)}", exc_info=True)
            raise

    def clear_all_highlights(self):
        """Resets all cell formatting to default"""
        try:
            default_fmt = CellFormat(
                backgroundColor=Color(1, 1, 1),
                textFormat=TextFormat(bold=False))

            if len(self.sheet.get_all_values()) > 1:
                format_cell_range(
                    self.sheet,
                    f"A2:D{len(self.sheet.get_all_values())}",
                    default_fmt)
        except Exception as e:
            self.logger.error(f"Failed to clear highlights: {str(e)}")

    def _highlight_new_row(self, row_number):
        """Applies highlight formatting to new rows"""
        try:
            new_row_fmt = CellFormat(
                backgroundColor=Color(1, 1, 0.7),
                textFormat=TextFormat(bold=True),
                borders=Borders(
                    top=Border("SOLID_THICK", Color(0, 0, 0))))
            format_cell_range(self.sheet, f"A{row_number}:D{row_number}", new_row_fmt)
        except Exception as e:
            self.logger.error(f"Failed to highlight row {row_number}: {str(e)}")

    def add_auction(self, date, county, address, link):
        """Adds and highlights new auctions"""
        try:
            existing = self.sheet.get_all_records()
            new_date = datetime.strptime(date, "%m-%d-%Y")

            is_duplicate = any(
                datetime.strptime(row["Auction Date"], "%m-%d-%Y") == new_date
                and row["Address"].strip().lower() == address.strip().lower()
                for row in existing
            )

            if not is_duplicate:
                self.sheet.append_row([date, county, address, link])
                new_row_num = len(self.sheet.get_all_values())
                self._highlight_new_row(new_row_num)
                self.sheet.sort((1, 'asc'))
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error adding auction: {str(e)}")
            return False