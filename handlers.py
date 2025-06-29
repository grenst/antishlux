"""
Message handlers for Telegram bot.
Contains async functions for handling different types of messages and commands.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    ChatMember,
    ChatPermissions
)
from telegram.ext import ContextTypes
from config import ADMIN_TELEGRAM_ID, STOP_WORDS
import db
from llm_client import LLMClient

# Set up logging
logger = logging.getLogger(__name__)

# Store pending verifications with timeout tasks
pending_verifications = {}

# Initialize LLM Client
llm_client = LLMClient()



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


async def chat_member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler for chat member updates (new members joining).
    Implements verification system with restricted permissions.
    """
    chat_member_update = update.chat_member
    
    # Check if this is a new member joining
    if (
        chat_member_update.old_chat_member.status == ChatMember.LEFT and
        chat_member_update.new_chat_member.status == ChatMember.MEMBER
    ):
        user = chat_member_update.new_chat_member.user
        chat = chat_member_update.chat
        
        # Skip if the new member is a bot
        if user.is_bot:
            return
            
        logger.info(f"New member {user.id} ({user.username}) joined chat {chat.id}")
        
        try:
            # Add user to database
            pool = context.application.bot_data.get('db_pool')
            if pool:
                await db.add_new_user(
                    pool, 
                    user.id, 
                    user.username, 
                    user.first_name
                )
                logger.info(f"Added user {user.id} to database")

            # Analyze profile picture
            profile_photos = await user.get_profile_photos()
            if profile_photos and profile_photos.photos:
                photo = profile_photos.photos[-1][0] # Get the largest photo
                photo_file = await photo.get_file()
                photo_bytes = await photo_file.download_as_bytearray()

                analysis_result = await llm_client.analyze_profile_picture(bytes(photo_bytes))
                if analysis_result.get("is_fake") and analysis_result.get("confidence", 0) > 0.85:
                    report_text = (
                        f"🚨 **Обнаружен поддельный аватар** 🚨\n\n"
                        f"**Пользователь:** {user.first_name} (`{user.id}`)\n"
                        f"**Причина от LLM:** {analysis_result.get('reason', 'N/A')}"
                    )
                    await context.bot.send_message(
                        chat_id=ADMIN_TELEGRAM_ID,
                        text=report_text,
                        parse_mode='Markdown'
                    )

            # Restrict user permissions
            restricted_permissions = ChatPermissions(
                can_send_messages=True,
                can_send_audios=False,
                can_send_documents=False,
                can_send_photos=False,
                can_send_videos=False,
                can_send_video_notes=False,
                can_send_voice_notes=False,
                can_send_polls=False,
                can_send_other_messages=False,
                can_add_web_page_previews=False,
                can_change_info=False,
                can_invite_users=False,
                can_pin_messages=False
            )
            
            await context.bot.restrict_chat_member(
                chat_id=chat.id,
                user_id=user.id,
                permissions=restricted_permissions
            )
            logger.info(f"Restricted permissions for user {user.id}")
            
            # Create verification button
            keyboard = [
                [InlineKeyboardButton("Я не бот 🤖", callback_data=f"verify_{user.id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Send welcome message with verification button
            welcome_text = (
                f"Добро пожаловать, {user.first_name}! 👋\n\n"
                f"Для обеспечения безопасности чата, пожалуйста, подтвердите, "
                f"что вы не бот, нажав на кнопку ниже.\n\n"
                f"⏰ У вас есть 2 минуты для подтверждения."
            )
            
            sent_message = await context.bot.send_message(
                chat_id=chat.id,
                text=welcome_text,
                reply_markup=reply_markup
            )
            
            # Set up timeout task
            verification_key = f"{chat.id}_{user.id}"
            timeout_task = asyncio.create_task(
                verification_timeout(context, chat.id, user.id, sent_message.message_id)
            )
            
            # Store verification info
            pending_verifications[verification_key] = {
                'user_id': user.id,
                'chat_id': chat.id,
                'message_id': sent_message.message_id,
                'timeout_task': timeout_task,
                'join_time': datetime.now()
            }
            
            logger.info(f"Set up verification for user {user.id} with 2-minute timeout")
            
        except Exception as e:
            logger.error(f"Error handling new chat member {user.id}: {e}")
            # Notify admin about the error
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_TELEGRAM_ID,
                    text=f"Ошибка при обработке нового участника {user.id}: {e}"
                )
            except Exception:
                pass


async def verification_timeout(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int, message_id: int) -> None:
    """
    Handle verification timeout - remove user if they don't verify within 2 minutes.
    """
    await asyncio.sleep(120)  # 2 minutes
    
    verification_key = f"{chat_id}_{user_id}"
    
    # Check if user is still pending verification
    if verification_key in pending_verifications:
        try:
            # Remove user from chat
            await context.bot.ban_chat_member(
                chat_id=chat_id,
                user_id=user_id
            )
            
            # Immediately unban to allow them to join again later
            await context.bot.unban_chat_member(
                chat_id=chat_id,
                user_id=user_id
            )
            
            # Delete the verification message
            try:
                await context.bot.delete_message(
                    chat_id=chat_id,
                    message_id=message_id
                )
            except Exception:
                pass  # Message might already be deleted
            
            # Send timeout notification
            await context.bot.send_message(
                chat_id=chat_id,
                text="⏰ Пользователь не прошел верификацию в течение 2 минут и был удален из чата."
            )
            
            # Clean up
            del pending_verifications[verification_key]
            
            logger.info(f"User {user_id} removed from chat {chat_id} due to verification timeout")
            
        except Exception as e:
            logger.error(f"Error during verification timeout for user {user_id}: {e}")


async def verification_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle verification button callback.
    Approve user and restore full permissions.
    """
    query = update.callback_query
    await query.answer()
    
    # Parse callback data
    if not query.data.startswith("verify_"):
        return
    
    try:
        user_id_from_button = int(query.data.split("_")[1])
    except (IndexError, ValueError):
        logger.error(f"Invalid callback data: {query.data}")
        return
    
    # Check if the person clicking is the same as the one being verified
    if query.from_user.id != user_id_from_button:
        await query.answer(
            "Эта кнопка предназначена не для вас!", 
            show_alert=True
        )
        return
    
    chat_id = query.message.chat.id
    user_id = query.from_user.id
    verification_key = f"{chat_id}_{user_id}"
    
    # Check if verification is still pending
    if verification_key not in pending_verifications:
        await query.edit_message_text(
            "Время верификации истекло или верификация уже завершена."
        )
        return
    
    try:
        # Cancel timeout task
        verification_info = pending_verifications[verification_key]
        if not verification_info['timeout_task'].done():
            verification_info['timeout_task'].cancel()
        
        # Restore full permissions
        full_permissions = ChatPermissions(
            can_send_messages=True,
            can_send_audios=True,
            can_send_documents=True,
            can_send_photos=True,
            can_send_videos=True,
            can_send_video_notes=True,
            can_send_voice_notes=True,
            can_send_polls=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
            can_change_info=False,  # Usually restricted for regular members
            can_invite_users=True,
            can_pin_messages=False   # Usually restricted for regular members
        )
        
        await context.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions=full_permissions
        )
        
        # Approve user in database
        pool = context.application.bot_data.get('db_pool')
        if pool:
            await db.approve_user(pool, user_id)
            logger.info(f"Approved user {user_id} in database")
        
        # Delete the verification message
        await query.delete_message()
        
        # Send success message
        success_message = await context.bot.send_message(
            chat_id=chat_id,
            text=f"✅ {query.from_user.first_name} успешно прошел верификацию! Добро пожаловать в чат!"
        )
        
        # Auto-delete success message after 10 seconds to keep chat clean
        asyncio.create_task(delete_message_after_delay(
            context, chat_id, success_message.message_id, 10
        ))
        
        # Clean up verification data
        del pending_verifications[verification_key]
        
        logger.info(f"User {user_id} successfully verified in chat {chat_id}")
        
    except Exception as e:
        logger.error(f"Error during verification for user {user_id}: {e}")
        await query.edit_message_text(
            "Произошла ошибка при верификации. Обратитесь к администратору."
        )


async def delete_message_after_delay(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay: int) -> None:
    """
    Delete a message after a specified delay.
    """
    await asyncio.sleep(delay)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        logger.debug(f"Could not delete message {message_id}: {e}")


async def message_filter_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler for filtering messages based on user approval status and stop words.
    Deletes messages from unapproved users and checks approved users for spam.
    """
    message = update.message
    user = update.effective_user
    chat = update.effective_chat
    
    # Skip processing for bots and private chats
    if user.is_bot or chat.type == 'private':
        return
    
    try:
        # Get user information from database
        pool = context.application.bot_data.get('db_pool')
        if not pool:
            logger.warning("Database pool not available for message filtering")
            return
        
        user_data = await db.get_user(pool, user.id)
        
        # If user is not in database, they haven't been processed yet
        if not user_data:
            logger.debug(f"User {user.id} not found in database, allowing message")
            return

        # Level 0: Verification Check
        if not user_data['is_approved']:
            try:
                await context.bot.delete_message(
                    chat_id=chat.id,
                    message_id=message.message_id
                )
                logger.info(f"Deleted message from unapproved user {user.id} in chat {chat.id}")
            except Exception as e:
                logger.error(f"Failed to delete message from unapproved user {user.id}: {e}")
            return
        
        # User is approved - check for spam if message has text
        if message.text:
            message_text = message.text.lower()
            
            # Level 1: Stop-Word Check
            found_stop_words = [word for word in STOP_WORDS if word in message_text]
            
            if found_stop_words:
                # Message contains spam - delete it
                try:
                    await context.bot.delete_message(
                        chat_id=chat.id,
                        message_id=message.message_id
                    )
                    logger.info(f"Deleted spam message from user {user.id} containing: {found_stop_words}")
                except Exception as e:
                    logger.error(f"Failed to delete spam message from user {user.id}: {e}")
                
                # Log the spam message
                await db.log_message(pool, user.id, message.text, is_spam=True)
                
                # Increment spam reports
                await db.increment_spam_reports(pool, user.id)
                
                # Get updated user data to check spam count
                updated_user_data = await db.get_user(pool, user.id)
                spam_count = updated_user_data['spam_reports'] if updated_user_data else 0
                
                logger.info(f"User {user.id} now has {spam_count} spam reports")
                
                # Ban user if they have 3 or more spam reports
                if spam_count >= 3:
                    try:
                        await context.bot.ban_chat_member(
                            chat_id=chat.id,
                            user_id=user.id
                        )
                        
                        # Send ban notification
                        await context.bot.send_message(
                            chat_id=chat.id,
                            text=f"🚫 Пользователь {user.first_name} был забанен за спам (3 предупреждения)."
                        )
                        
                        # Notify admin
                        try:
                            await context.bot.send_message(
                                chat_id=ADMIN_TELEGRAM_ID,
                                text=f"🚫 Пользователь {user.id} ({user.username}) забанен в чате {chat.id} за спам"
                            )
                        except Exception:
                            pass
                        
                        logger.info(f"Banned user {user.id} for spam in chat {chat.id}")
                        
                    except Exception as e:
                        logger.error(f"Failed to ban user {user.id}: {e}")
                else:
                    # Send warning (auto-delete after 5 seconds)
                    try:
                        warning_message = await context.bot.send_message(
                            chat_id=chat.id,
                            text=f"⚠️ {user.first_name}, ваше сообщение было удалено за нарушение правил. "
                                 f"Предупреждение {spam_count}/3."
                        )
                        
                        # Auto-delete warning after 5 seconds
                        asyncio.create_task(delete_message_after_delay(
                            context, chat.id, warning_message.message_id, 5
                        ))
                        
                    except Exception as e:
                        logger.error(f"Failed to send warning to user {user.id}: {e}")
                return

            # Level 2: LLM Analysis for messages with links
            if 'http' in message_text or 't.me' in message_text:
                logger.info(f"Message from {user.id} contains a link, analyzing with LLM...")
                analysis_result = await llm_client.analyze_text(message.text)

                is_spam = analysis_result.get('is_spam', False)
                confidence = analysis_result.get('confidence', 0.0)
                reason = analysis_result.get('reason', 'Причина не указана.')

                if is_spam:
                    if confidence > 0.8:
                        # Ban user
                        try:
                            await context.bot.delete_message(chat_id=chat.id, message_id=message.message_id)
                            await context.bot.ban_chat_member(chat_id=chat.id, user_id=user.id)
                            logger.info(f"Banned user {user.id} based on LLM analysis (confidence: {confidence})")
                            await context.bot.send_message(
                                chat_id=ADMIN_TELEGRAM_ID,
                                text=f"🚫 Пользователь {user.first_name} ({user.id}) был забанен по результатам LLM-анализа.\n"
                                     f"Причина: {reason}\n"
                                     f"Сообщение: {message.text}"
                            )
                        except Exception as e:
                            logger.error(f"Failed to ban user {user.id} based on LLM analysis: {e}")
                    elif 0.6 <= confidence <= 0.8:
                        # Delete message and report to admin
                        try:
                            await context.bot.delete_message(chat_id=chat.id, message_id=message.message_id)
                            logger.info(f"Deleted message from {user.id} and reporting to admin based on LLM analysis (confidence: {confidence})")
                            report_text = (
                                f"⚠️ **Подозрительное сообщение для проверки** ⚠️\n\n"
                                f"**Пользователь:** {user.first_name} (`{user.id}`)\n"
                                f"**Сообщение:**\n```\n{message.text}\n```\n"
                                f"**Причина от LLM:** {reason}\n"
                                f"**Уверенность:** {confidence}"
                            )
                            await context.bot.send_message(
                                chat_id=ADMIN_TELEGRAM_ID,
                                text=report_text,
                                parse_mode='Markdown'
                            )
                        except Exception as e:
                            logger.error(f"Failed to report suspicious message from {user.id}: {e}")
        else:
            # For non-text messages from approved users, just log them
            if message.photo or message.video or message.document or message.audio:
                await db.log_message(pool, user.id, "[Media message]", is_spam=False)
    
    except Exception as e:
        logger.error(f"Error in message filter handler for user {user.id}: {e}")


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler for unknown commands.
    Responds to unrecognized commands with a helpful message.
    """
    await update.message.reply_text(
        "Извините, я не понимаю эту команду. 🤔\n"
        "Используйте /start для получения информации о доступных командах."
    )
