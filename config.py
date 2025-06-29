"""
Configuration module for Telegram bot.
Loads environment variables from .env file.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Bot configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_TELEGRAM_ID = os.getenv('ADMIN_TELEGRAM_ID')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Validate required environment variables
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")

if not ADMIN_TELEGRAM_ID:
    raise ValueError("ADMIN_TELEGRAM_ID environment variable is required")

# Convert ADMIN_TELEGRAM_ID to integer
try:
    ADMIN_TELEGRAM_ID = int(ADMIN_TELEGRAM_ID)
except ValueError:
    raise ValueError("ADMIN_TELEGRAM_ID must be a valid integer")

# Database configuration
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')

# Validate database configuration
if not DB_USER:
    raise ValueError("DB_USER environment variable is required")

if not DB_PASSWORD:
    raise ValueError("DB_PASSWORD environment variable is required")

if not DB_NAME:
    raise ValueError("DB_NAME environment variable is required")

# Convert DB_PORT to integer
try:
    DB_PORT = int(DB_PORT)
except ValueError:
    raise ValueError("DB_PORT must be a valid integer")

# Anti-spam configuration
STOP_WORDS = [
    "приват",
    "onlyfans", 
    "горячие фото",
    "сливы",
    "знакомства",
    "интим",
    "крипто",
    "майнинг",
    "заработок",
    "инвестиции",
    "продам",
    "куплю",
    "реклама",
    "бизнес",
    "млм",
    "пирамида",
    "схема",
    "деньги быстро",
    "легкие деньги",
    "без вложений",
    "телеграм канал",
    "подписывайся",
    "переходи по ссылке",
    "жми на ссылку",
    "регистрируйся",
    "скачай приложение"
]

# Convert to lowercase for case-insensitive matching
STOP_WORDS = [word.lower() for word in STOP_WORDS]
