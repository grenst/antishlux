"""
Message handlers for Telegram bot.
Contains async functions for handling different types of messages and commands.
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import ADMIN_TELEGRAM_ID

# Set up logging
logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler for /start command.
    Welcomes new users and provides basic information about the bot.
    """
    user = update.effective_user
    chat = update.effective_chat
    
    logger.info(f"User {user.id} ({user.username}) started the bot in chat {chat.id}")
    
    welcome_message = (
        f"Привет, {user.first_name}! 👋\n\n"
        "Добро пожаловать в наш бот!\n"
        "Здесь вы можете получить информацию и помощь.\n\n"
        "Используйте команды для взаимодействия с ботом."
    )
    
    await update.message.reply_text(welcome_message)


async def new_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler for new chat members.
    Welcomes new users when they join a group chat.
    """
    message = update.message
    new_members = message.new_chat_members
    
    for member in new_members:
        # Skip if the new member is a bot
        if member.is_bot:
            continue
            
        logger.info(f"New member {member.id} ({member.username}) joined chat {message.chat.id}")
        
        welcome_message = (
            f"Добро пожаловать в группу, {member.first_name}! 🎉\n\n"
            "Мы рады видеть вас здесь!\n"
            "Пожалуйста, ознакомьтесь с правилами группы."
        )
        
        await message.reply_text(welcome_message)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler for errors that occur during message processing.
    Logs errors and notifies admin if needed.
    """
    logger.error(f"Exception while handling an update: {context.error}")
    
    # Optionally notify admin about critical errors
    if context.error and hasattr(context, 'bot'):
        try:
            error_message = f"⚠️ Произошла ошибка в боте:\n\n{str(context.error)}"
            await context.bot.send_message(
                chat_id=ADMIN_TELEGRAM_ID,
                text=error_message
            )
        except Exception as e:
            logger.error(f"Failed to send error notification to admin: {e}")


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler for unknown commands.
    Responds to unrecognized commands with a helpful message.
    """
    await update.message.reply_text(
        "Извините, я не понимаю эту команду. 🤔\n"
        "Используйте /start для получения информации о доступных командах."
    )
