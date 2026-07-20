import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Telegram Config ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
PAYMENT_TOKEN = os.getenv("PAYMENT_TOKEN") # Antes STRIPE_TOKEN, ahora genérico

if not TELEGRAM_TOKEN:
    print("⚠️ WARNING: TELEGRAM_TOKEN not set in .env")

if not PAYMENT_TOKEN:
    print("⚠️ WARNING: PAYMENT_TOKEN not set in .env (Pagos desactivados)")

# --- Database Config ---
DB_NAME = os.getenv("DB_NAME", "rastreador_coches.db")

# --- Scraper Settings ---
DEFAULT_MIN_PRICE = int(os.getenv("DEFAULT_MIN_PRICE", 500))
DEFAULT_SCROLL_PAUSE = float(os.getenv("DEFAULT_SCROLL_PAUSE", 0.3))
DEFAULT_SCAN_TIME = int(os.getenv("DEFAULT_SCAN_TIME", 20))
ERROR_LOG = os.path.join("logs", "errors.log")
HEADLESS = os.getenv("HEADLESS", "True").lower() == "true"

# --- Proxies ---
PROXIES = []

# --- Fuel Mappings ---
FUEL_OPTIONS = {
    "1": ("petrol", "Gasolina ⛽"),
    "2": ("diesel", "Diesel 🚜"),
    "3": ("hybrid_house_plug_in", "Híbrido 🔋"),
    "4": ("electric", "Eléctrico ⚡")
}

# --- Anti-Bot Settings ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (AppleWebKit/537.36, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Edge/121.0.0.0"
]

# --- Business Logic: Tiers & Limits ---
TIERS = {
    "free": {"max_searches": 1, "scan_interval": 120, "photos": False},
    "premium": {"max_searches": 10, "scan_interval": 15, "photos": True},
    "pro": {"max_searches": 999, "scan_interval": 5, "photos": True}
}

# --- Valid Car Brands ---
CAR_BRANDS = [
    "abarth", "alfa romeo", "alpine", "aston martin", "audi", "bentley", "bmw", "bugatti", 
    "cadillac", "chevrolet", "chrysler", "citroen", "cupra", "dacia", "daewoo", "dodge", 
    "ds", "ferrari", "fiat", "ford", "honda", "hummer", "hyundai", "infiniti", "isuzu", 
    "jaguar", "jeep", "kia", "lamborghini", "lancia", "land rover", "lexus", "lotus", 
    "maserati", "mazda", "mclaren", "mercedes-benz", "mercedes", "mg", "mini", "mitsubishi", 
    "nissan", "opel", "peugeot", "porsche", "renault", "rolls-royce", "rover", "saab", 
    "seat", "skoda", "smart", "ssangyong", "subaru", "suzuki", "tesla", "toyota", 
    "volkswagen", "volvo"
]
