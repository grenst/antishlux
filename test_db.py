"""
Unit tests for db.py module.
Tests database functions using mocks to avoid real database connections.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

import asyncpg

# Import functions to test
from db import (
    get_pool,
    init_db,
    add_new_user,
    get_user,
    approve_user,
    log_message,
    increment_spam_reports,
    get_user_stats
)


class TestDatabaseFunctions:
    """Test class for database functions."""

    @pytest.fixture
    def mock_pool(self):
        """Create a mock database pool."""
        pool = AsyncMock(spec=asyncpg.Pool)
        return pool

    @pytest.fixture
    def mock_connection(self):
        """Create a mock database connection."""
        connection = AsyncMock(spec=asyncpg.Connection)
        return connection

    @pytest.fixture
    def mock_pool_with_connection(self, mock_pool, mock_connection):
        """Create a mock pool that returns a mock connection."""
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        mock_pool.acquire.return_value.__aexit__.return_value = None
        return mock_pool, mock_connection

    @pytest.mark.asyncio
    @patch('db.asyncpg.create_pool')
    async def test_get_pool_success(self, mock_create_pool):
        """Test successful database pool creation."""
        # Arrange
        expected_pool = AsyncMock(spec=asyncpg.Pool)
        # Make create_pool return a coroutine that resolves to the pool
        async def mock_pool_creation(*args, **kwargs):
            return expected_pool
        mock_create_pool.side_effect = mock_pool_creation

        # Act
        result = await get_pool()

        # Assert
        assert result == expected_pool
        mock_create_pool.assert_called_once()

    @pytest.mark.asyncio
    @patch('db.asyncpg.create_pool')
    async def test_get_pool_failure(self, mock_create_pool):
        """Test database pool creation failure."""
        # Arrange
        async def mock_pool_failure(*args, **kwargs):
            raise Exception("Connection failed")
        mock_create_pool.side_effect = mock_pool_failure

        # Act & Assert
        with pytest.raises(Exception, match="Connection failed"):
            await get_pool()

    @pytest.mark.asyncio
    async def test_init_db_success(self, mock_pool_with_connection):
        """Test successful database initialization."""
        # Arrange
        mock_pool, mock_connection = mock_pool_with_connection

        # Act
        await init_db(mock_pool)

        # Assert
        # Verify that execute was called for tables and indexes
        assert mock_connection.execute.call_count >= 2  # At least 2 tables + indexes

    @pytest.mark.asyncio
    async def test_init_db_failure(self, mock_pool_with_connection):
        """Test database initialization failure."""
        # Arrange
        mock_pool, mock_connection = mock_pool_with_connection
        mock_connection.execute.side_effect = Exception("Table creation failed")

        # Act & Assert
        with pytest.raises(Exception, match="Table creation failed"):
            await init_db(mock_pool)

    @pytest.mark.asyncio
    async def test_add_new_user_success(self, mock_pool_with_connection):
        """Test successfully adding a new user."""
        # Arrange
        mock_pool, mock_connection = mock_pool_with_connection
        mock_connection.fetchrow.return_value = None  # User doesn't exist
        
        user_id = 123456789
        username = "testuser"
        first_name = "Test"

        # Act
        result = await add_new_user(mock_pool, user_id, username, first_name)

        # Assert
        assert result is True
        mock_connection.fetchrow.assert_called_once()
        mock_connection.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_new_user_already_exists(self, mock_pool_with_connection):
        """Test adding a user that already exists."""
        # Arrange
        mock_pool, mock_connection = mock_pool_with_connection
        mock_connection.fetchrow.return_value = {'user_id': 123456789}  # User exists
        
        user_id = 123456789
        username = "testuser"
        first_name = "Test"

        # Act
        result = await add_new_user(mock_pool, user_id, username, first_name)

        # Assert
        assert result is False
        mock_connection.fetchrow.assert_called_once()
        mock_connection.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_new_user_database_error(self, mock_pool_with_connection):
        """Test add_new_user with database error."""
        # Arrange
        mock_pool, mock_connection = mock_pool_with_connection
        mock_connection.fetchrow.side_effect = Exception("Database error")
        
        user_id = 123456789
        username = "testuser"
        first_name = "Test"

        # Act & Assert
        with pytest.raises(Exception, match="Database error"):
            await add_new_user(mock_pool, user_id, username, first_name)

    @pytest.mark.asyncio
    async def test_get_user_found(self, mock_pool_with_connection):
        """Test successfully retrieving an existing user."""
        # Arrange
        mock_pool, mock_connection = mock_pool_with_connection
        
        user_data = {
            'user_id': 123456789,
            'username': 'testuser',
            'first_name': 'Test',
            'join_date': datetime.now(timezone.utc),
            'is_approved': False,
            'spam_reports': 0
        }
        mock_connection.fetchrow.return_value = user_data
        
        user_id = 123456789

        # Act
        result = await get_user(mock_pool, user_id)

        # Assert
        assert result is not None
        assert result['user_id'] == user_id
        assert result['username'] == 'testuser'
        assert result['first_name'] == 'Test'
        assert result['is_approved'] is False
        assert result['spam_reports'] == 0
        mock_connection.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, mock_pool_with_connection):
        """Test retrieving a non-existent user."""
        # Arrange
        mock_pool, mock_connection = mock_pool_with_connection
        mock_connection.fetchrow.return_value = None
        
        user_id = 123456789

        # Act
        result = await get_user(mock_pool, user_id)

        # Assert
        assert result is None
        mock_connection.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_database_error(self, mock_pool_with_connection):
        """Test get_user with database error."""
        # Arrange
        mock_pool, mock_connection = mock_pool_with_connection
        mock_connection.fetchrow.side_effect = Exception("Database error")
        
        user_id = 123456789

        # Act & Assert
        with pytest.raises(Exception, match="Database error"):
            await get_user(mock_pool, user_id)

    @pytest.mark.asyncio
    async def test_approve_user_success(self, mock_pool_with_connection):
        """Test successfully approving a user."""
        # Arrange
        mock_pool, mock_connection = mock_pool_with_connection
        mock_connection.execute.return_value = "UPDATE 1"  # 1 row affected
        
        user_id = 123456789

        # Act
        result = await approve_user(mock_pool, user_id)

        # Assert
        assert result is True
        mock_connection.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_approve_user_not_found(self, mock_pool_with_connection):
        """Test approving a non-existent user."""
        # Arrange
        mock_pool, mock_connection = mock_pool_with_connection
        mock_connection.execute.return_value = "UPDATE 0"  # 0 rows affected
        
        user_id = 123456789

        # Act
        result = await approve_user(mock_pool, user_id)

        # Assert
        assert result is False
        mock_connection.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_approve_user_database_error(self, mock_pool_with_connection):
        """Test approve_user with database error."""
        # Arrange
        mock_pool, mock_connection = mock_pool_with_connection
        mock_connection.execute.side_effect = Exception("Database error")
        
        user_id = 123456789

        # Act & Assert
        with pytest.raises(Exception, match="Database error"):
            await approve_user(mock_pool, user_id)

    @pytest.mark.asyncio
    async def test_log_message_success(self, mock_pool_with_connection):
        """Test successfully logging a message."""
        # Arrange
        mock_pool, mock_connection = mock_pool_with_connection
        mock_connection.fetchval.return_value = 1  # Message ID
        
        user_id = 123456789
        message_text = "Test message"
        is_spam = False

        # Act
        result = await log_message(mock_pool, user_id, message_text, is_spam)

        # Assert
        assert result == 1
        mock_connection.fetchval.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_message_spam(self, mock_pool_with_connection):
        """Test logging a spam message."""
        # Arrange
        mock_pool, mock_connection = mock_pool_with_connection
        mock_connection.fetchval.return_value = 2  # Message ID
        
        user_id = 123456789
        message_text = "Spam message"
        is_spam = True

        # Act
        result = await log_message(mock_pool, user_id, message_text, is_spam)

        # Assert
        assert result == 2
        mock_connection.fetchval.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_message_database_error(self, mock_pool_with_connection):
        """Test log_message with database error."""
        # Arrange
        mock_pool, mock_connection = mock_pool_with_connection
        mock_connection.fetchval.side_effect = Exception("Database error")
        
        user_id = 123456789
        message_text = "Test message"

        # Act & Assert
        with pytest.raises(Exception, match="Database error"):
            await log_message(mock_pool, user_id, message_text)

    @pytest.mark.asyncio
    async def test_increment_spam_reports_success(self, mock_pool_with_connection):
        """Test successfully incrementing spam reports."""
        # Arrange
        mock_pool, mock_connection = mock_pool_with_connection
        mock_connection.execute.return_value = "UPDATE 1"  # 1 row affected
        
        user_id = 123456789

        # Act
        result = await increment_spam_reports(mock_pool, user_id)

        # Assert
        assert result is True
        mock_connection.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_increment_spam_reports_user_not_found(self, mock_pool_with_connection):
        """Test incrementing spam reports for non-existent user."""
        # Arrange
        mock_pool, mock_connection = mock_pool_with_connection
        mock_connection.execute.return_value = "UPDATE 0"  # 0 rows affected
        
        user_id = 123456789

        # Act
        result = await increment_spam_reports(mock_pool, user_id)

        # Assert
        assert result is False
        mock_connection.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_stats_success(self, mock_pool_with_connection):
        """Test successfully getting user statistics."""
        # Arrange
        mock_pool, mock_connection = mock_pool_with_connection
        
        stats_data = {
            'total_users': 100,
            'approved_users': 80,
            'users_with_reports': 5
        }
        mock_connection.fetchrow.return_value = stats_data

        # Act
        result = await get_user_stats(mock_pool)

        # Assert
        assert result['total_users'] == 100
        assert result['approved_users'] == 80
        assert result['users_with_reports'] == 5
        assert result['pending_approval'] == 20  # total - approved
        mock_connection.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_stats_database_error(self, mock_pool_with_connection):
        """Test get_user_stats with database error."""
        # Arrange
        mock_pool, mock_connection = mock_pool_with_connection
        mock_connection.fetchrow.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(Exception, match="Database error"):
            await get_user_stats(mock_pool)


class TestIntegrationScenarios:
    """Integration-style tests for common user workflows."""

    @pytest.fixture
    def mock_pool_with_connection(self):
        """Create a mock pool that returns a mock connection."""
        pool = AsyncMock(spec=asyncpg.Pool)
        connection = AsyncMock(spec=asyncpg.Connection)
        pool.acquire.return_value.__aenter__.return_value = connection
        pool.acquire.return_value.__aexit__.return_value = None
        return pool, connection

    @pytest.mark.asyncio
    async def test_new_user_workflow(self, mock_pool_with_connection):
        """Test complete workflow for a new user."""
        # Arrange
        mock_pool, mock_connection = mock_pool_with_connection
        
        user_id = 123456789
        username = "newuser"
        first_name = "New"
        
        # Setup mocks for add_new_user
        mock_connection.fetchrow.side_effect = [
            None,  # User doesn't exist (for add_new_user)
            {  # User exists after creation (for get_user)
                'user_id': user_id,
                'username': username,
                'first_name': first_name,
                'join_date': datetime.now(timezone.utc),
                'is_approved': False,
                'spam_reports': 0
            }
        ]
        mock_connection.execute.return_value = "UPDATE 1"

        # Act - Add new user
        add_result = await add_new_user(mock_pool, user_id, username, first_name)
        
        # Get user to verify
        user_data = await get_user(mock_pool, user_id)
        
        # Approve user
        approve_result = await approve_user(mock_pool, user_id)

        # Assert
        assert add_result is True
        assert user_data is not None
        assert user_data['user_id'] == user_id
        assert user_data['is_approved'] is False  # Not yet approved in this mock
        assert approve_result is True

    @pytest.mark.asyncio
    async def test_spam_reporting_workflow(self, mock_pool_with_connection):
        """Test workflow for reporting spam from a user."""
        # Arrange
        mock_pool, mock_connection = mock_pool_with_connection
        
        user_id = 123456789
        spam_message = "This is spam!"
        
        # Setup mocks
        mock_connection.fetchval.return_value = 1  # Message ID
        mock_connection.execute.return_value = "UPDATE 1"  # Spam report increment

        # Act
        message_id = await log_message(mock_pool, user_id, spam_message, is_spam=True)
        spam_increment_result = await increment_spam_reports(mock_pool, user_id)

        # Assert
        assert message_id == 1
        assert spam_increment_result is True


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
