from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from time import sleep
import time
import math
from datetime import datetime
from sheets_manager import SheetsManager
from logger import setup_logger
logger = setup_logger()
import logging
import os
os.environ['WDM_LOG_LEVEL'] = '1'  # 0=Silent, 1=Errors, 2=Warnings, 3=Info


# Configure Chrome options (unchanged from your original)
options = webdriver.ChromeOptions()
# Headless configuration
options.add_argument("--headless=new")  # Modern headless mode
options.add_argument("--no-sandbox")  # Essential for CI/CD
options.add_argument("--disable-dev-shm-usage")  # Prevents memory issues
options.add_argument("--disable-gpu")  # Recommended for headless
options.add_argument("--window-size=1920,1080")  # Virtual display size

# Anti-detection settings
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)


# Initialize WebDriver with all warnings all logged
driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)

# Initialize SheetsManager (replace your old Sheets code with this)
sheets = SheetsManager(
    json_keyfile="auction-list-scraper-466209-8e731da0fa26.json",
    spreadsheet_name="Auction Listings"
)
# 2. Remove expired auctions
sheets.remove_expired_auctions()

# 3. Before scraping, storing all the auctions to check later if any was cancelled or withdrawn
existing_auctions = sheets.get_existing_auctions()  # {key: row_num}
active_auctions = set()  # Just track active auction keys

def scrapeData(website_link, county):
    driver.get(website_link)
    driver.implicitly_wait(30)

    # Getting data for the current month + next 2 months (to get at least 60 days advance)
    for k in range(3):
        # Get the count of auction dates first to avoid stale references
        date_elements = driver.find_elements(By.CSS_SELECTOR, ".CALBOX[role='link'], .CALBOX.CALSELF")
        num_auctions = len(date_elements)

        # for each auction in the current month
        for i in range(num_auctions):
            try:
                # Re-find elements each iteration to avoid staleness
                current_dates = driver.find_elements(By.CSS_SELECTOR, ".CALBOX[role='link'], .CALBOX.CALSELF")
                if i >= len(current_dates):  # Safety check
                    break

                date_box = current_dates[i]
                date = date_box.get_attribute("aria-label") or date_box.get_attribute("dayid")
                this_date = (datetime.strptime(date, "%B-%d-%Y")).date()
                if this_date < datetime.today().date():
                    continue

                # Click directly on the date box in each auction closure of the current month
                date_box.click()
                print(date)

                try_again_count = 3
                current_url = driver.current_url  # Save the initial URL

                while try_again_count > 0:
                    try:
                        # Wait for max pages element
                        max_pages = WebDriverWait(driver, 30).until(
                            EC.visibility_of_element_located((By.ID, "maxWA"))
                        ).text
                        print("Total pages:", max_pages)

                        max_pages = int(max_pages)
                        for j in range(max_pages):
                            # Find the auction container
                            auction_container = driver.find_element(By.ID, "Area_W")

                            # Loop over all auction items
                            auction_elements = auction_container.find_elements(By.CSS_SELECTOR, "div.AUCTION_ITEM")
                            num_auction_items = len(auction_elements)
                            for x in range(num_auction_items):
                                auction = auction_elements[x]
                                # 1. Get the STATUS CONTAINER (always exists)
                                status_container = auction.find_element(By.CSS_SELECTOR, "div.AUCTION_STATS")

                                # 2. Get BOTH elements (label + dynamic value)
                                try:
                                    # The label element (may say "Auction Status" or "Auction Sold")
                                    status_label = status_container.find_element(By.CSS_SELECTOR, "div.ASTAT_MSGA").text

                                    # The dynamic value element (contains actual status like "07/07/2025 09:01 AM ET")
                                    status_value = status_container.find_element(By.CSS_SELECTOR, "div.ASTAT_MSGB").text

                                    print(f"Raw Label: {status_label} | Status Value: {status_value}")

                                    status_text = ""
                                    # 3. Determine true status
                                    if "Sold" in status_label:
                                        status_text = "Auction Sold"
                                    else:
                                        if "Starts" in status_value:
                                            status_text = "Auction Starts"
                                        elif "Cancelled" in status_value:
                                            status_text = "Status Cancelled"

                                except NoSuchElementException:
                                    print("Could not parse auction status")

                                if status_label == "Auction Starts":
                                    # Find the table and get all rows
                                    table = auction.find_element(By.CSS_SELECTOR, "table.ad_tab")
                                    rows = table.find_elements(By.TAG_NAME, "tr")

                                    # Get last 3 rows (Appraised Value, Opening Bid, Deposit Requirement)
                                    last_three_rows = rows[-3:] if len(rows) >= 3 else rows

                                    # Extract the data from each row's td.AD_DTA
                                    appraised_value = last_three_rows[0].find_element(By.CSS_SELECTOR,
                                                                                      "td.AD_DTA").text.strip()
                                    opening_bid = last_three_rows[1].find_element(By.CSS_SELECTOR,
                                                                                  "td.AD_DTA").text.strip()
                                    deposit_requirement = last_three_rows[2].find_element(By.CSS_SELECTOR,
                                                                                          "td.AD_DTA").text.strip()

                                    address_line0 = rows[3].find_element(By.CSS_SELECTOR,
                                                                          "td.AD_DTA").text.strip()  # 5th last row (often city/state/zip)
                                    address_line1 = rows[-4].find_element(By.CSS_SELECTOR,
                                                                          "td.AD_DTA").text.strip()  # 4th last row
                                    # Combine address lines
                                    full_address = f"{address_line0} {address_line1}".strip()

                                    # Clean and convert values
                                    clean_value = float(appraised_value.replace("$", "").replace(",", ""))
                                    opening_bid_float = float(opening_bid.replace("$", "").replace(",", ""))

                                    deposit_clean = deposit_requirement.replace("$", "").replace(",", "")

                                    # Calculate expected 2/3 value (all the different variations present in data)
                                    check_value_1 = round(2 / 3 * clean_value, 0)
                                    check_value_2 = round(2 / 3 * clean_value, 2)
                                    check_value_3 = check_value_1 + 1.0
                                    check_value_4 = check_value_2 - 0.1
                                    check_value_5 = check_value_2 + 0.1

                                    # Filter conditions
                                    is_property_tax_sale = (
                                            clean_value == 0 or
                                            (opening_bid_float != check_value_1 and opening_bid_float != check_value_2 and opening_bid_float != check_value_3 and opening_bid_float != check_value_4 and opening_bid_float != check_value_5) or
                                            deposit_clean not in ["2000.00", "5000.00", "10000.00"]
                                    )

                                    if is_property_tax_sale:
                                        # Format date exactly as MM-DD-YYYY
                                        formatted_date = this_date.strftime("%m-%d-%Y")

                                        # Generate proper link (using case number if available)
                                        try:
                                            case_num = rows[1].find_element(By.CSS_SELECTOR, "td.AD_DTA").text.strip()
                                            link = f"{website_link}&case={case_num}"
                                        except Exception:
                                            link = website_link  # Fallback to base URL

                                        # Add to Google Sheets (with duplicate protection)
                                        added = sheets.add_auction(
                                            date=formatted_date,
                                            county=county,
                                            address=full_address,
                                            link=current_url
                                        )

                                        if added:
                                            print(
                                                f"✓ Added to Sheets: {formatted_date} | {county} | {full_address[:50]}...")
                                        else:
                                            print(f"⏩ Duplicate skipped: {full_address[:50]}...")

                                        # When finding active auctions, set true in the set:
                                        unique_key = sheets._create_auction_key({
                                            "Auction Date": formatted_date,
                                            "County": county,
                                            "Address": full_address
                                        })
                                        active_auctions.add(unique_key)  # Works for both new and existing auctions

                                        time.sleep(1) # sleep a second to not exceed sheets writing quota per user

                            try:
                                next_page = driver.find_element(By.CSS_SELECTOR, "span.PageRight > img")
                                next_page.click()
                                time.sleep(2)
                            except NoSuchElementException:
                                break  # End of pagination

                        break  # Success - exit retry loop

                    except TimeoutException:
                        try_again_count -= 1
                        print(f"Loading failed. Retries remaining: {try_again_count}")

                        if try_again_count > 0:
                            try:
                                x -= 1
                            except NameError:
                                i -= 1
                            driver.get(current_url)
                        else:
                            if 'x' not in locals() and 'i' in locals():
                                logger.error(f"Auction failed | County: {county} | Date: {date} | Error: The website elements failed to load in time",exc_info=True)
                    except Exception as e:
                        print(f"Unexpected error: {str(e)}")
                        try_again_count -= 1
                        if try_again_count > 0:
                            try:
                                x -= 1
                            except NameError:
                                i -= 1
                            driver.get(current_url)
                            time.sleep(3)
                        else:
                            if 'x' not in locals() and 'i' in locals():
                                logger.error(f"Auction failed | County: {county} | Date: {date} | Error: The website elements failed to load in time", exc_info = True)
                # Go back and wait for calendar to reload
                driver.back()
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".CALDAYBOX")))
                print("\n")

            except Exception as e:
                print(f"Couldn't parse auction {i + 1}/{num_auctions}: {str(e)}")
                if "stale" in str(e).lower():
                    driver.refresh()
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".CALDAYBOX")))
                else:
                    driver.back()

        try:
            next_month = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div.CALNAV a[aria-label^='Next Month']"))
            )
            next_month.click()

        except (TimeoutException, NoSuchElementException):
            print("No more months available")
            break  # Exit if no next month button



counties = [
    "adams", "allen", "ashland", "ashtabula", "athens", "auglaize", "belmont",
    "brown", "butler", "carroll", "champaign", "clark", "clermont", "clinton",
    "columbiana", "coshocton", "crawford", "cuyahoga", "darke", "defiance",
    "delaware", "erie", "fairfield", "fayette", "franklin", "fulton", "gallia",
    "geauga", "greene", "guernsey", "hamilton", "hancock", "hardin", "harrison",
    "henry", "highland", "hocking", "holmes", "huron", "jackson", "jefferson",
    "knox", "lake", "lawrence", "licking", "logan", "lorain", "lucas", "madison",
    "mahoning", "marion", "medina", "meigs", "mercer", "miami", "monroe",
    "montgomery", "morgan", "morrow", "muskingum", "noble", "ottawa", "paulding",
    "perry", "pickaway", "pike", "portage", "preble", "putnam", "richland",
    "ross", "sandusky", "scioto", "seneca", "shelby", "stark", "summit",
    "trumbull", "tuscarawas", "union", "vanwert", "vinton", "warren", "washington",
    "wayne", "williams", "wood", "wyandot"
]

if __name__ == "__main__":
    try:
        for county in counties:
            website_link = f"https://{county}.sheriffsaleauction.ohio.gov/index.cfm?zaction=USER&zmethod=CALENDAR"
            logger.info(f"Starting scrape for {county.upper()} county")
            try:
                scrapeData(website_link, county)
            except Exception as e:
                logger.error(f"COUNTY-WIDE FAILURE: {county} | URL: {website_link} | Error: {str(e)}", exc_info=True)
                continue
            finally:
                time.sleep(2)
        logger.info(f"Scraping completed: {new_rows_count} new rows added, {updated_rows_count} rows updated")

        # Find auctions to remove (exist in sheet but not in active_auctions)
        rows_to_delete = [
            row_num for key, row_num in existing_auctions.items()
            if key not in active_auctions
        ]
        # Delete from bottom to avoid index shifting
        for row_num in sorted(rows_to_delete, reverse=True):
            sheets.sheet.delete_rows(row_num)
            time.sleep(1)  # to not exceed writing quota per user

        driver.quit()
        exit(0)
    except Exception as e:
        logger.critical(f"Fatal error in main execution: {str(e)}", exc_info=True)
        driver.quit()
        exit(1)
