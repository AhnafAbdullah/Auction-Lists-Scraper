# 🏠 Auction Listings Scraper → Google Sheet

This Python project automatically scrapes **property tax foreclosure auction listings** from 88 public auction websites (excluding mortgage foreclosure listings), filters them based on specific criteria, and updates a private **Google Sheet** every 48 hours.

---

## 🚀 Features

- ✅ **Scrapes 88 public auction websites** using [Selenium](https://www.selenium.dev/)
- 📑 **Includes only relevant listings** (non-mortgage, property-tax-related)
- ⚙️ **Filtering Logic**:
  - Skips listings with:
    - Appraised Value shown
    - Opening Bid = ⅔ Appraised Value
    - Deposit = $2,000 / $5,000 / $10,000
  - Includes listings if *any* of the above rules are not met
- 📝 **Outputs to Google Sheet** with columns:
  - `Auction Date` (MM-DD-YYYY)
  - `County`
  - `Address`
  - `Link`
- 🔁 **Automated Updates Every 48 Hours**
  - New listings inserted
  - Existing rows updated if changed
  - Duplicate prevention
- 🧾 **Logging**
  - Tracks new rows added each run
  - Logs failed sites with parsing errors
- ☁️ **Automated via GitHub Actions / Cloud Scheduler**

---

## 🛠 Tech Stack

- 🐍 Python
- 🌐 Selenium WebDriver
- 📊 Google Sheets API
- ☁️ GitHub Actions (CI/CD)
- 🪵 Built-in Logging Module

---

## 📂 Source & Links

- Master site: [Cuyahoga Auction Calendar](https://cuyahoga.sheriffsaleauction.ohio.gov/index.cfm?zaction=USER&zmethod=CALENDAR)  
- List of 88 auction websites: [Google Sheet Link](https://docs.google.com/spreadsheets/d/1YLSoD0bAJ-KULgoxq14SBZ6z0oNk6RF40gD0ol0-ca4/edit?usp=sharing)

---

## ✅ Success Criteria

- Only valid property tax auctions are added
- Script runs reliably on schedule
- No duplicates in the sheet
- Errors are logged clearly
- Code is clean, maintainable, and documented

---

## 📌 Setup Instructions (Coming Soon)

> Instructions for setting up credentials, environment, and scheduling will be added.

---

