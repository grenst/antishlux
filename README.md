# Python Telegram Bot "AntiShlux" (beta)
developed by [grenst](https://github.com/grenst)

**Language:** [English](#english-version) | [Українська](#ukrainian-version)

<a id="english-version"></a>
## English Version

An intelligent, multi-layered moderation bot for Telegram, designed to protect group chats from spam, malicious links, and unwanted content using a combination of rule-based filters and advanced AI analysis.

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

- Multi-Layered Defense System: Implements a sophisticated, multi-level filtering funnel to maximize accuracy and minimize costs.
- New User Verification (CAPTCHA): New members must pass a simple "I'm not a bot" check before they can post, effectively blocking low-level automated bots.   
- Stop-Word Filtering: Instantly removes messages containing words from a customizable blocklist.
- AI-Powered Semantic Analysis: Leverages Google Gemini's Large Language Models (LLMs) to analyze the intent behind messages containing links, detecting sophisticated spam, phishing, and adult content that keyword filters miss.   
- Proactive Profile Picture Analysis: A cutting-edge feature that uses a multimodal LLM to analyze new users' profile pictures for signs of being AI-generated, flagging potentially fake accounts before they can act.   
- Reputation and Warning System: Tracks user violations and automatically bans repeat offenders after a set number of warnings.   
- Database Integration: Uses PostgreSQL to log moderation actions and user data, creating a dataset for future model fine-tuning.
- Admin-Friendly: Provides clear notifications to administrators for critical errors and high-confidence moderation actions.
- Asynchronous Architecture: Built with Python and asyncio for high performance and the ability to handle many concurrent users efficiently.

<a id="ukrainian-version"></a>
## Українська Версія

Інтелектуальний, багаторівневий бот-модератор для Telegram, розроблений для захисту групових чатів від спаму, шкідливих посилань та небажаного контенту (до прикладу "шлюхоботів") за допомогою комбінації фільтрів на основі правил та передового ШІ-аналізу.

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

- Багаторівнева система захисту: Впроваджує складний, багаторівневий фільтраційний конвеєр для максимізації точності та мінімізації витрат.
- Верифікація нових користувачів (CAPTCHA): Нові учасники повинні пройти просту перевірку "Я не бот", перш ніж зможуть публікувати повідомлення, що ефективно блокує найпростіших автоматизованих ботів.   
- Фільтрація за стоп-словами: Миттєво видаляє повідомлення, що містять слова з настроюваного чорного списку.
- Семантичний аналіз на основі ШІ: Використовує великі мовні моделі (LLM) Google Gemini для аналізу намірів у повідомленнях, що містять посилання, виявляючи складний спам, фішинг та контент для дорослих, який пропускають ключові фільтри.   
- Проактивний аналіз зображень профілю: Передова функція, яка використовує мультимодальну LLM для аналізу фотографій профілю нових користувачів на ознаки генерації ШІ, позначаючи потенційно фейкові акаунти ще до того, як вони почнуть діяти.   
- Система репутації та попереджень: Відстежує порушення користувачів і автоматично блокує повторних порушників після визначеної кількості попереджень.   
- Інтеграція з базою даних: Використовує PostgreSQL для логування дій модерації та даних користувачів, створюючи набір даних для майбутнього доналаштування (fine-tuning) моделі.
- Зручність для адміністратора: Надає чіткі сповіщення адміністраторам про критичні помилки та дії модерації з високою впевненістю.
- Асинхронна архітектура: Створений на Python та asyncio для високої продуктивності та здатності ефективно обробляти багато одночасних користувачів.