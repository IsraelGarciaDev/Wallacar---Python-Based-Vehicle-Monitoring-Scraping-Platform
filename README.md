# 🚗 Wallacar - Marketplace Opportunities Scraper

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Selenium](https://img.shields.io/badge/selenium-4.0%2B-green)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

An advanced vehicle marketplace monitoring tool and scraper. This bot automates vehicle searches, analyzes market pricing anomalies, and sends real-time "bargain" alerts directly to a Telegram chat.

## ✨ Features

- **Automated Web Scraping**: Modular architecture using Selenium to extract real-time vehicle listings from high-traffic marketplaces.
- **Market Data Analysis**: Calculates local average market prices and instantly detects price deviations (bargains).
- **Smart Notifications**: Sends automated alerts via Telegram (`notifier.py` / `bot_handler.py`) containing images, key technical data, and price grading (🟢 Bargain, 🟡 Fair Price, 🔴 Overpriced).
- **Anti-Bot Evasion**: Utilizes `undetected-chromedriver` and automated User-Agent rotation to prevent blocks and ensure uninterrupted tracking.
- **Resource Management**: Robust internal handling for clearing dangling Chrome processes and optimizing memory consumption.
- **Data Persistence**: Built-in relational data management using SQLite to store price histories and search statistics.

## 🚀 Installation & Setup

### Prerequisites

- Python 3.10 or higher.
- Google Chrome installed.

### Local Configuration

1. **Clone the repository** (or download the source files):

2. **Create a virtual environment** (recommended):
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Linux/Mac
    .venv\Scripts\activate     # On Windows
    ```

3. **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4. **Environment Variables**:
    Copy the provided example file and set up your private keys:
    ```bash
    cp .env.example .env
    ```
    Edit `.env` to input your custom Telegram Bot Token and Chat ID.

## ⚙️ Usage

To launch the automation engine, run:

```bash
python bot_handler.py
python main.py
