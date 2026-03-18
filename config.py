import os
from dotenv import load_dotenv

load_dotenv()

# ==============================
# BOT SETUP
# ==============================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 523694323
ADMIN_PASSWORD = "AlphaTrade2026"

# ==============================
# ADMIN GROUP
# ==============================
GROUP_CHAT_ID = -5224217487
ADMIN_IDS = [523694323, 8639162466]  # Add more admin IDs as needed

# ==============================
# DEPOSIT CONFIGURATION
# ==============================
DEPOSIT_NETWORKS = ["TRC20"]
USDT_TRC20_WALLET = "TDMmSvX5j5A8eQR4FhnW9Sn8JkLZZYhise"
MIN_DEPOSIT = 30.0
INVESTMENT_DURATION = 24 # Hours

# ==============================
# TRONSCAN API
# ==============================
TRONSCAN_API = "https://apilist.tronscan.org/api/transaction-info"

# ==============================
# BUSINESS LOGIC
# ==============================
REFERRAL_PERCENTAGE = 0.05 # 5%

# ==============================
# DATABASE
# ==============================
DB_PATH = "database/alphatrade.db"
