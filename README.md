# Python Telegram Bot

**Language:** [English](#english-version) | [Українська](#ukrainian-version)

<a id="english-version"></a>
## English Version

Base for a Telegram bot using python-telegram-bot (v20+) and asyncio.

### Project Structure

```
.
├── main.py           # Entry point, bot startup
├── config.py         # Environment variables loader
├── handlers.py       # Message and command handlers
├── db.py            # PostgreSQL module (skeleton)
├── requirements.txt  # Project dependencies
├── .env.example     # Environment variables template
└── README.md        # This file
```

### Installation & Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Create `.env` file:**
   ```bash
   cp .env.example .env
   ```

3. **Configure environment variables:**
   ```
   TELEGRAM_BOT_TOKEN=ваш_токен_бота
   ADMIN_TELEGRAM_ID=ваш_telegram_id
   GEMINI_API_KEY=AIzaSyB...
   DB_HOST=your_db_host
   DB_PORT=5432
   DB_USER=your_db_user
   DB_PASSWORD=your_db_password
   DB_NAME=your_db_name
   ```

### Features

- Async startup/shutdown
- PostgreSQL integration
- User verification system
- Admin error notifications

<a id="ukrainian-version"></a>
## Українська Версія

База для Telegram-бота з використанням python-telegram-bot (версії 20+) та asyncio.

### Структура проекту

```
.
├── main.py           # Точка входу, запуск бота
├── config.py         # Завантаження змінних оточення
├── handlers.py       # Обробники повідомлень та команд
├── db.py            # Модуль для роботи з PostgreSQL (заготівля)
├── requirements.txt  # Залежності проекту
├── .env.example     # Приклад файлу зі змінними оточення
└── README.md        # Цей файл
```

### Встановлення та налаштування

1. **Встановіть залежності:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Створіть файл `.env`:**
   ```bash
   cp .env.example .env
   ```

3. **Налаштуйте змінні оточення:**
   ```
   TELEGRAM_BOT_TOKEN=ваш_токен_бота
   ADMIN_TELEGRAM_ID=ваш_telegram_id
   GEMINI_API_KEY=AIzaSyB...
   DB_HOST=your_db_host
   DB_PORT=5432
   DB_USER=your_db_user
   DB_PASSWORD=your_db_password
   DB_NAME=your_db_name
   ```

### Можливості

- Асинхронний запуск/зупинка
- Інтеграція з PostgreSQL
- Система верифікації користувачів
- Сповіщення про помилки для адміністратора
