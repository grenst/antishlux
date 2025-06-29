"""
Unit tests for handlers.py module.
Tests chat member verification system using mocks.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import (
    Update, 
    Chat, 
    User, 
    ChatMember, 
    ChatMemberUpdated, 
    CallbackQuery,
    Message,
    InlineKeyboardMarkup,
    ChatPermissions
)
from telegram.ext import ContextTypes

# Import handlers to test
from handlers import (
    chat_member_handler,
    verification_callback,
    verification_timeout,
    pending_verifications,
    message_filter_handler
)


class TestChatMemberHandler:
    """Test class for chat member verification system."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock context."""
        context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
        context.bot = AsyncMock()
        context.application = MagicMock()
        context.application.bot_data = {'db_pool': AsyncMock()}
        return context

    @pytest.fixture
    def mock_user(self):
        """Create a mock user."""
        user = MagicMock(spec=User)
        user.id = 123456789
        user.username = "testuser"
        user.first_name = "Test"
        user.is_bot = False
        return user

    @pytest.fixture
    def mock_chat(self):
        """Create a mock chat."""
        chat = MagicMock(spec=Chat)
        chat.id = -1001234567890
        chat.type = "supergroup"
        return chat

    @pytest.fixture
    def mock_chat_member_update(self, mock_user, mock_chat):
        """Create a mock chat member update for new member joining."""
        update = MagicMock(spec=Update)
        
        old_member = MagicMock(spec=ChatMember)
        old_member.status = ChatMember.LEFT
        
        new_member = MagicMock(spec=ChatMember)
        new_member.status = ChatMember.MEMBER
        new_member.user = mock_user
        
        chat_member_updated = MagicMock(spec=ChatMemberUpdated)
        chat_member_updated.old_chat_member = old_member
        chat_member_updated.new_chat_member = new_member
        chat_member_updated.chat = mock_chat
        
        update.chat_member = chat_member_updated
        return update

    @pytest.mark.asyncio
    async def test_chat_member_handler_new_member_success(
        self, 
        mock_chat_member_update, 
        mock_context, 
        mock_user, 
        mock_chat
    ):
        """Test successful handling of new member joining."""
        # Clear any existing verifications
        pending_verifications.clear()
        
        # Setup mocks
        mock_context.bot.restrict_chat_member = AsyncMock()
        mock_context.bot.send_message = AsyncMock()
        
        sent_message = MagicMock()
        sent_message.message_id = 12345
        mock_context.bot.send_message.return_value = sent_message
        
        with patch('handlers.db.add_new_user', new_callable=AsyncMock) as mock_add_user:
            mock_add_user.return_value = True
            
            with patch('handlers.asyncio.create_task') as mock_create_task:
                # Make create_task return a mock task instead of trying to create real coroutines
                mock_task = MagicMock()
                mock_create_task.return_value = mock_task
                
                # Act
                await chat_member_handler(mock_chat_member_update, mock_context)
                
                # Assert
                mock_add_user.assert_called_once_with(
                    mock_context.application.bot_data['db_pool'],
                    mock_user.id,
                    mock_user.username,
                    mock_user.first_name
                )
                
                mock_context.bot.restrict_chat_member.assert_called_once()
                mock_context.bot.send_message.assert_called_once()
                mock_create_task.assert_called_once()
                
                # Check verification was stored
                verification_key = f"{mock_chat.id}_{mock_user.id}"
                assert verification_key in pending_verifications
        
        # Cleanup
        pending_verifications.clear()

    @pytest.mark.asyncio
    async def test_chat_member_handler_bot_user_skipped(
        self, 
        mock_chat_member_update, 
        mock_context
    ):
        """Test that bot users are skipped in chat member handler."""
        # Arrange - make user a bot
        mock_chat_member_update.chat_member.new_chat_member.user.is_bot = True
        
        # Act
        await chat_member_handler(mock_chat_member_update, mock_context)
        
        # Assert - no database or bot actions should be called
        mock_context.bot.restrict_chat_member.assert_not_called()
        mock_context.bot.send_message.assert_not_called()


class TestVerificationCallback:
    """Test class for verification callback handler."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock context."""
        context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
        context.bot = AsyncMock()
        context.application = MagicMock()
        context.application.bot_data = {'db_pool': AsyncMock()}
        return context

    @pytest.fixture
    def mock_callback_query(self):
        """Create a mock callback query."""
        query = MagicMock(spec=CallbackQuery)
        query.data = "verify_123456789"
        query.from_user = MagicMock(spec=User)
        query.from_user.id = 123456789
        query.from_user.first_name = "Test"
        
        query.message = MagicMock(spec=Message)
        query.message.chat = MagicMock(spec=Chat)
        query.message.chat.id = -1001234567890
        
        query.answer = AsyncMock()
        query.delete_message = AsyncMock()
        query.edit_message_text = AsyncMock()
        
        return query

    @pytest.fixture
    def setup_pending_verification(self):
        """Setup a pending verification."""
        verification_key = "-1001234567890_123456789"
        timeout_task = MagicMock()
        timeout_task.done.return_value = False
        timeout_task.cancel = MagicMock()
        
        pending_verifications[verification_key] = {
            'user_id': 123456789,
            'chat_id': -1001234567890,
            'message_id': 12345,
            'timeout_task': timeout_task,
            'join_time': datetime.now()
        }
        
        yield verification_key
        
        # Cleanup
        if verification_key in pending_verifications:
            del pending_verifications[verification_key]

    @pytest.mark.asyncio
    async def test_verification_callback_success(
        self, 
        mock_callback_query, 
        mock_context,
        setup_pending_verification
    ):
        """Test successful verification callback."""
        verification_key = setup_pending_verification
        
        with patch('handlers.db.approve_user', new_callable=AsyncMock) as mock_approve:
            mock_approve.return_value = True
            mock_context.bot.restrict_chat_member = AsyncMock()
            mock_context.bot.send_message = AsyncMock()
            
            success_message = MagicMock()
            success_message.message_id = 54321
            mock_context.bot.send_message.return_value = success_message
            
            with patch('handlers.asyncio.create_task') as mock_create_task:
                # Act
                update = MagicMock(spec=Update)
                update.callback_query = mock_callback_query
                
                await verification_callback(update, mock_context)
                
                # Assert
                mock_callback_query.answer.assert_called_once()
                mock_approve.assert_called_once_with(
                    mock_context.application.bot_data['db_pool'],
                    123456789
                )
                mock_context.bot.restrict_chat_member.assert_called_once()
                mock_callback_query.delete_message.assert_called_once()
                mock_context.bot.send_message.assert_called_once()
                mock_create_task.assert_called_once()
                
                # Check verification was cleaned up
                assert verification_key not in pending_verifications

    @pytest.mark.asyncio
    async def test_verification_callback_wrong_user(
        self, 
        mock_callback_query, 
        mock_context,
        setup_pending_verification
    ):
        """Test verification callback when wrong user clicks button."""
        # Change user ID to simulate wrong user clicking
        mock_callback_query.from_user.id = 987654321
        mock_callback_query.answer = AsyncMock()
        
        # Act
        update = MagicMock(spec=Update)
        update.callback_query = mock_callback_query
        
        await verification_callback(update, mock_context)
        
        # Assert - answer() is called twice: once at start, once with error
        assert mock_callback_query.answer.call_count == 2
        mock_callback_query.answer.assert_called_with(
            "Эта кнопка предназначена не для вас!",
            show_alert=True
        )


class TestVerificationTimeout:
    """Test class for verification timeout functionality."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock context."""
        context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
        context.bot = AsyncMock()
        return context

    @pytest.fixture
    def setup_pending_verification_for_timeout(self):
        """Setup a pending verification for timeout test."""
        chat_id = -1001234567890
        user_id = 123456789
        verification_key = f"{chat_id}_{user_id}"
        
        pending_verifications[verification_key] = {
            'user_id': user_id,
            'chat_id': chat_id,
            'message_id': 12345,
            'timeout_task': MagicMock(),
            'join_time': datetime.now()
        }
        
        yield chat_id, user_id, verification_key
        
        # Cleanup
        if verification_key in pending_verifications:
            del pending_verifications[verification_key]

    @pytest.mark.asyncio
    async def test_verification_timeout_removes_user(
        self, 
        mock_context,
        setup_pending_verification_for_timeout
    ):
        """Test that verification timeout removes user from chat."""
        chat_id, user_id, verification_key = setup_pending_verification_for_timeout
        message_id = 12345
        
        mock_context.bot.ban_chat_member = AsyncMock()
        mock_context.bot.unban_chat_member = AsyncMock()
        mock_context.bot.delete_message = AsyncMock()
        mock_context.bot.send_message = AsyncMock()
        
        # Mock asyncio.sleep to avoid actual delay in test
        with patch('handlers.asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            # Act
            await verification_timeout(mock_context, chat_id, user_id, message_id)
            
            # Assert
            mock_sleep.assert_called_once_with(120)  # 2 minutes
            mock_context.bot.ban_chat_member.assert_called_once_with(
                chat_id=chat_id,
                user_id=user_id
            )
            mock_context.bot.unban_chat_member.assert_called_once_with(
                chat_id=chat_id,
                user_id=user_id
            )
            mock_context.bot.delete_message.assert_called_once_with(
                chat_id=chat_id,
                message_id=message_id
            )
            mock_context.bot.send_message.assert_called_once()
            
            # Check verification was cleaned up
            assert verification_key not in pending_verifications

    @pytest.mark.asyncio
    async def test_verification_timeout_user_already_verified(
        self, 
        mock_context
    ):
        """Test timeout when user has already been verified."""
        chat_id = -1001234567890
        user_id = 123456789
        message_id = 12345
        
        # No pending verification setup (user already verified)
        
        mock_context.bot.ban_chat_member = AsyncMock()
        
        # Mock asyncio.sleep to avoid actual delay in test
        with patch('handlers.asyncio.sleep', new_callable=AsyncMock):
            # Act
            await verification_timeout(mock_context, chat_id, user_id, message_id)
            
            # Assert - no actions should be taken
            mock_context.bot.ban_chat_member.assert_not_called()


class TestMessageFilter:
    """Test class for message filtering functionality."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock context."""
        context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
        context.bot = AsyncMock()
        context.application = MagicMock()
        context.application.bot_data = {'db_pool': AsyncMock()}
        return context

    @pytest.fixture
    def mock_user(self):
        """Create a mock user."""
        user = MagicMock(spec=User)
        user.id = 123456789
        user.username = "testuser"
        user.first_name = "Test"
        user.is_bot = False
        return user

    @pytest.fixture
    def mock_chat(self):
        """Create a mock chat."""
        chat = MagicMock(spec=Chat)
        chat.id = -1001234567890
        chat.type = "supergroup"
        return chat

    @pytest.fixture
    def mock_message(self, mock_user, mock_chat):
        """Create a mock message."""
        message = MagicMock(spec=Message)
        message.message_id = 12345
        message.text = "Hello, this is a test message"
        message.photo = None
        message.video = None
        message.document = None
        message.audio = None
        
        update = MagicMock(spec=Update)
        update.message = message
        update.effective_user = mock_user
        update.effective_chat = mock_chat
        
        return update

    @pytest.mark.asyncio
    async def test_message_filter_unapproved_user_deleted(
        self, 
        mock_message, 
        mock_context,
        mock_user
    ):
        """Test that messages from unapproved users are deleted."""
        # Setup user data - not approved
        user_data = {
            'user_id': mock_user.id,
            'username': mock_user.username,
            'first_name': mock_user.first_name,
            'is_approved': False,
            'spam_reports': 0
        }
        
        with patch('handlers.db.get_user', new_callable=AsyncMock) as mock_get_user:
            mock_get_user.return_value = user_data
            mock_context.bot.delete_message = AsyncMock()
            
            # Act
            await message_filter_handler(mock_message, mock_context)
            
            # Assert
            mock_get_user.assert_called_once_with(
                mock_context.application.bot_data['db_pool'],
                mock_user.id
            )
            mock_context.bot.delete_message.assert_called_once_with(
                chat_id=mock_message.effective_chat.id,
                message_id=mock_message.message.message_id
            )

    @pytest.mark.asyncio
    async def test_message_filter_approved_user_clean_message(
        self, 
        mock_message, 
        mock_context,
        mock_user
    ):
        """Test that clean messages from approved users are not deleted."""
        # Setup user data - approved
        user_data = {
            'user_id': mock_user.id,
            'username': mock_user.username,
            'first_name': mock_user.first_name,
            'is_approved': True,
            'spam_reports': 0
        }
        
        with patch('handlers.db.get_user', new_callable=AsyncMock) as mock_get_user:
            with patch('handlers.db.log_message', new_callable=AsyncMock) as mock_log_message:
                mock_get_user.return_value = user_data
                mock_context.bot.delete_message = AsyncMock()
                
                # Act
                await message_filter_handler(mock_message, mock_context)
                
                # Assert
                mock_get_user.assert_called_once()
                mock_context.bot.delete_message.assert_not_called()
                mock_log_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_message_filter_approved_user_spam_message(
        self, 
        mock_message, 
        mock_context,
        mock_user
    ):
        """Test that spam messages from approved users are deleted and user gets warning."""
        # Setup spam message
        mock_message.message.text = "Привет! Смотри мой приват за деньги!"
        
        # Setup user data - approved with no previous warnings
        user_data = {
            'user_id': mock_user.id,
            'username': mock_user.username,
            'first_name': mock_user.first_name,
            'is_approved': True,
            'spam_reports': 0
        }
        
        updated_user_data = {
            **user_data,
            'spam_reports': 1
        }
        
        with patch('handlers.db.get_user', new_callable=AsyncMock) as mock_get_user:
            with patch('handlers.db.log_message', new_callable=AsyncMock) as mock_log_message:
                with patch('handlers.db.increment_spam_reports', new_callable=AsyncMock) as mock_increment:
                    mock_get_user.side_effect = [user_data, updated_user_data]
                    mock_context.bot.delete_message = AsyncMock()
                    mock_context.bot.send_message = AsyncMock()
                    
                    warning_message = MagicMock()
                    warning_message.message_id = 54321
                    mock_context.bot.send_message.return_value = warning_message
                    
                    with patch('handlers.asyncio.create_task') as mock_create_task:
                        # Act
                        await message_filter_handler(mock_message, mock_context)
                        
                        # Assert
                        mock_context.bot.delete_message.assert_called_once()
                        mock_log_message.assert_called_once_with(
                            mock_context.application.bot_data['db_pool'],
                            mock_user.id,
                            mock_message.message.text,
                            is_spam=True
                        )
                        mock_increment.assert_called_once()
                        mock_context.bot.send_message.assert_called_once()
                        mock_create_task.assert_called_once()  # For auto-delete warning

    @pytest.mark.asyncio
    async def test_message_filter_spam_user_gets_banned(
        self, 
        mock_message, 
        mock_context,
        mock_user
    ):
        """Test that user with 3 spam reports gets banned."""
        # Setup spam message
        mock_message.message.text = "Заработок в интернете без вложений!"
        
        # Setup user data - approved with 2 previous warnings
        user_data = {
            'user_id': mock_user.id,
            'username': mock_user.username,
            'first_name': mock_user.first_name,
            'is_approved': True,
            'spam_reports': 2
        }
        
        updated_user_data = {
            **user_data,
            'spam_reports': 3
        }
        
        with patch('handlers.db.get_user', new_callable=AsyncMock) as mock_get_user:
            with patch('handlers.db.log_message', new_callable=AsyncMock) as mock_log_message:
                with patch('handlers.db.increment_spam_reports', new_callable=AsyncMock) as mock_increment:
                    mock_get_user.side_effect = [user_data, updated_user_data]
                    mock_context.bot.delete_message = AsyncMock()
                    mock_context.bot.ban_chat_member = AsyncMock()
                    mock_context.bot.send_message = AsyncMock()
                    
                    # Act
                    await message_filter_handler(mock_message, mock_context)
                    
                    # Assert
                    mock_context.bot.delete_message.assert_called_once()
                    mock_log_message.assert_called_once()
                    mock_increment.assert_called_once()
                    mock_context.bot.ban_chat_member.assert_called_once_with(
                        chat_id=mock_message.effective_chat.id,
                        user_id=mock_user.id
                    )
                    # Should send ban notification and admin notification
                    assert mock_context.bot.send_message.call_count >= 1

    @pytest.mark.asyncio
    async def test_message_filter_user_not_in_database(
        self, 
        mock_message, 
        mock_context,
        mock_user
    ):
        """Test that messages from users not in database are allowed."""
        with patch('handlers.db.get_user', new_callable=AsyncMock) as mock_get_user:
            mock_get_user.return_value = None  # User not found
            mock_context.bot.delete_message = AsyncMock()
            
            # Act
            await message_filter_handler(mock_message, mock_context)
            
            # Assert
            mock_get_user.assert_called_once()
            mock_context.bot.delete_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_message_filter_bot_messages_skipped(
        self, 
        mock_message, 
        mock_context
    ):
        """Test that bot messages are skipped."""
        # Make user a bot
        mock_message.effective_user.is_bot = True
        
        with patch('handlers.db.get_user', new_callable=AsyncMock) as mock_get_user:
            # Act
            await message_filter_handler(mock_message, mock_context)
            
            # Assert
            mock_get_user.assert_not_called()

    @pytest.mark.asyncio
    async def test_message_filter_private_chat_skipped(
        self, 
        mock_message, 
        mock_context
    ):
        """Test that private chat messages are skipped."""
        # Make chat private
        mock_message.effective_chat.type = 'private'
        
        with patch('handlers.db.get_user', new_callable=AsyncMock) as mock_get_user:
            # Act
            await message_filter_handler(mock_message, mock_context)
            
            # Assert
            mock_get_user.assert_not_called()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])


class TestLLMMessageFilter:
    """Test class for LLM-based message filtering functionality."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock context."""
        context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
        context.bot = AsyncMock()
        context.application = MagicMock()
        context.application.bot_data = {'db_pool': AsyncMock()}
        return context

    @pytest.fixture
    def mock_user(self):
        """Create a mock user."""
        user = MagicMock(spec=User)
        user.id = 123456789
        user.username = "testuser"
        user.first_name = "Test"
        user.is_bot = False
        return user

    @pytest.fixture
    def mock_chat(self):
        """Create a mock chat."""
        chat = MagicMock(spec=Chat)
        chat.id = -1001234567890
        chat.type = "supergroup"
        return chat

    @pytest.fixture
    def mock_message(self, mock_user, mock_chat):
        """Create a mock message."""
        message = MagicMock(spec=Message)
        message.message_id = 12345
        message.text = "Hello, this is a test message"
        message.photo = None
        message.video = None
        message.document = None
        message.audio = None
        
        update = MagicMock(spec=Update)
        update.message = message
        update.effective_user = mock_user
        update.effective_chat = mock_chat
        
        return update

    @pytest.fixture
    def approved_user_data(self, mock_user):
        """Return data for an approved user."""
        return {
            'user_id': mock_user.id,
            'username': mock_user.username,
            'first_name': mock_user.first_name,
            'is_approved': True,
            'spam_reports': 0
        }

    @pytest.mark.asyncio
    async def test_message_with_link_triggers_llm_analysis(
        self, mock_message, mock_context, approved_user_data
    ):
        """Test that a message with a link from an approved user triggers LLM analysis."""
        mock_message.message.text = "Check out this link: https://example.com"
        
        with patch('handlers.db.get_user', new_callable=AsyncMock) as mock_get_user:
            with patch('handlers.llm_client.analyze_text', new_callable=AsyncMock) as mock_analyze_text:
                mock_get_user.return_value = approved_user_data
                mock_analyze_text.return_value = {"is_spam": False, "confidence": 0.1, "reason": ""}

                await message_filter_handler(mock_message, mock_context)

                mock_analyze_text.assert_called_once_with(mock_message.message.text)

    @pytest.mark.asyncio
    async def test_message_without_link_skips_llm_analysis(
        self, mock_message, mock_context, approved_user_data
    ):
        """Test that a message without a link from an approved user does not trigger LLM analysis."""
        mock_message.message.text = "This is a normal message without links."
        
        with patch('handlers.db.get_user', new_callable=AsyncMock) as mock_get_user:
            with patch('handlers.llm_client.analyze_text', new_callable=AsyncMock) as mock_analyze_text:
                mock_get_user.return_value = approved_user_data

                await message_filter_handler(mock_message, mock_context)

                mock_analyze_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_llm_detects_high_confidence_spam_and_bans_user(
        self, mock_message, mock_context, approved_user_data, mock_user, mock_chat
    ):
        """Test that a high-confidence spam message results in a ban."""
        mock_message.message.text = "Super secret content here: https://spam.com"
        
        with patch('handlers.db.get_user', new_callable=AsyncMock) as mock_get_user:
            with patch('handlers.llm_client.analyze_text', new_callable=AsyncMock) as mock_analyze_text:
                mock_get_user.return_value = approved_user_data
                mock_analyze_text.return_value = {"is_spam": True, "confidence": 0.9, "reason": "High-risk spam"}

                await message_filter_handler(mock_message, mock_context)

                mock_context.bot.delete_message.assert_called_once_with(chat_id=mock_chat.id, message_id=mock_message.message.message_id)
                mock_context.bot.ban_chat_member.assert_called_once_with(chat_id=mock_chat.id, user_id=mock_user.id)
                mock_context.bot.send_message.assert_called_once() # Admin notification

    @pytest.mark.asyncio
    async def test_llm_detects_medium_confidence_spam_and_reports(
        self, mock_message, mock_context, approved_user_data, mock_chat
    ):
        """Test that a medium-confidence spam message is deleted and reported."""
        mock_message.message.text = "Maybe spammy link: https://maybe-spam.com"
        
        with patch('handlers.db.get_user', new_callable=AsyncMock) as mock_get_user:
            with patch('handlers.llm_client.analyze_text', new_callable=AsyncMock) as mock_analyze_text:
                mock_get_user.return_value = approved_user_data
                mock_analyze_text.return_value = {"is_spam": True, "confidence": 0.7, "reason": "Medium-risk spam"}

                await message_filter_handler(mock_message, mock_context)

                mock_context.bot.delete_message.assert_called_once_with(chat_id=mock_chat.id, message_id=mock_message.message.message_id)
                mock_context.bot.ban_chat_member.assert_not_called()
                mock_context.bot.send_message.assert_called_once() # Admin report

    @pytest.mark.asyncio
    async def test_llm_detects_non_spam_and_takes_no_action(
        self, mock_message, mock_context, approved_user_data
    ):
        """Test that a non-spam message with a link is ignored."""
        mock_message.message.text = "Here is a normal link: https://google.com"
        
        with patch('handlers.db.get_user', new_callable=AsyncMock) as mock_get_user:
            with patch('handlers.llm_client.analyze_text', new_callable=AsyncMock) as mock_analyze_text:
                mock_get_user.return_value = approved_user_data
                mock_analyze_text.return_value = {"is_spam": False, "confidence": 0.1, "reason": "Not spam"}

                await message_filter_handler(mock_message, mock_context)

                mock_context.bot.delete_message.assert_not_called()
                mock_context.bot.ban_chat_member.assert_not_called()
                mock_context.bot.send_message.assert_not_called()

