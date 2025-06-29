"""
Main entry point for the Telegram bot.
Handles async bot startup, shutdown, and message routing.
"""

import asyncio
import logging
import signal
import sys
from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ChatMemberHandler,
    filters,
    ContextTypes
)

from config import TELEGRAM_BOT_TOKEN
from handlers import (
    start_command, 
    new_chat_member, 
    error_handler, 
    unknown_command,
    chat_member_handler,
    verification_callback,
    message_filter_handler
)
from db import get_pool, init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class TelegramBot:
    """
    Main Telegram bot class that manages the application lifecycle.
    """
    
    def __init__(self):
        self.application: Application = None
        self.db_pool = None
        self._shutdown_event = asyncio.Event()
    
    async def setup_application(self) -> None:
        """
        Sets up the Telegram bot application with handlers.
        """
        logger.info("Setting up Telegram bot application...")
        
        # Build application
        self.application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
        
        # Store db_pool in bot_data for handlers to access
        self.application.bot_data['db_pool'] = self.db_pool
        
        # Add command handlers
        self.application.add_handler(CommandHandler("start", start_command))
        
        # Add chat member handler for new joins (using ChatMemberHandler)
        self.application.add_handler(ChatMemberHandler(chat_member_handler))
        
        # Add callback query handler for verification buttons
        self.application.add_handler(CallbackQueryHandler(verification_callback))
        
        # Add message filter handler for text and media messages
        self.application.add_handler(
            MessageHandler(
                filters.TEXT | filters.PHOTO | filters.VIDEO | filters.ATTACHMENT | filters.AUDIO,
                message_filter_handler
            )
        )
        
        # Add message handlers (fallback for older method)
        self.application.add_handler(
            MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_chat_member)
        )
        
        # Add handler for unknown commands (must be last)
        self.application.add_handler(
            MessageHandler(filters.COMMAND, unknown_command)
        )
        
        # Add error handler
        self.application.add_error_handler(error_handler)
        
        logger.info("Application setup completed")
    
    async def start(self) -> None:
        """
        Starts the bot using polling.
        """
        logger.info("Starting Telegram bot...")
        
        try:
            # Initialize application
            await self.application.initialize()
            await self.application.start()
            
            # Start polling
            await self.application.updater.start_polling(
                drop_pending_updates=True,
                allowed_updates=Update.ALL_TYPES
            )
            
            logger.info("Bot started successfully and is polling for updates")
            
            # Wait for shutdown signal
            await self._shutdown_event.wait()
            
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            raise
    
    async def stop(self) -> None:
        """
        Gracefully stops the bot.
        """
        logger.info("Shutting down Telegram bot...")
        
        try:
            if self.application and self.application.updater:
                # Stop polling
                await self.application.updater.stop()
                
                # Stop application
                await self.application.stop()
                await self.application.shutdown()
            
            # Close database pool
            if self.db_pool:
                await self.db_pool.close()
                logger.info("Database pool closed")
                
            logger.info("Bot stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")
        finally:
            self._shutdown_event.set()
    
    def signal_handler(self, signum, frame):
        """
        Handles shutdown signals (SIGINT, SIGTERM).
        """
        logger.info(f"Received signal {signum}, initiating shutdown...")
        asyncio.create_task(self.stop())


async def main():
    """
    Main async function that runs the bot.
    """
    bot = TelegramBot()
    
    # Set up signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        bot.signal_handler(signum, frame)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Initialize database
        logger.info("Initializing database connection...")
        db_pool = await get_pool()
        await init_db(db_pool)
        
        # Store db_pool in bot for later use
        bot.db_pool = db_pool
        
        # Setup and start the bot
        await bot.setup_application()
        await bot.start()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise
    finally:
        await bot.stop()


if __name__ == "__main__":
    """
    Entry point of the application.
    """
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
