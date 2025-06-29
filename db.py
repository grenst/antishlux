"""
Database module for PostgreSQL interactions.
Handles user management, message logging, and database operations.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

import asyncpg
from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME

# Set up logging
logger = logging.getLogger(__name__)


async def get_pool() -> asyncpg.Pool:
    """
    Creates and returns a connection pool to PostgreSQL database.
    
    Returns:
        asyncpg.Pool: Database connection pool
        
    Raises:
        Exception: If connection to database fails
    """
    try:
        pool = await asyncpg.create_pool(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            min_size=1,
            max_size=10,
            command_timeout=60
        )
        logger.info(f"Successfully created database connection pool to {DB_HOST}:{DB_PORT}")
        return pool
    except Exception as e:
        logger.error(f"Failed to create database connection pool: {e}")
        raise


async def init_db(pool: asyncpg.Pool) -> None:
    """
    Initializes the database by creating required tables if they don't exist.
    
    Args:
        pool: Database connection pool
        
    Raises:
        Exception: If table creation fails
    """
    logger.info("Initializing database tables...")
    
    # SQL for creating users table
    create_users_table = """
    CREATE TABLE IF NOT EXISTS users (
        user_id BIGINT PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        join_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        is_approved BOOLEAN DEFAULT FALSE,
        spam_reports INTEGER DEFAULT 0
    );
    """
    
    # SQL for creating messages table
    create_messages_table = """
    CREATE TABLE IF NOT EXISTS messages (
        message_id SERIAL PRIMARY KEY,
        user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
        message_text TEXT,
        is_spam BOOLEAN DEFAULT FALSE,
        timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """
    
    # SQL for creating indexes for better performance
    create_indexes = [
        "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);",
        "CREATE INDEX IF NOT EXISTS idx_users_is_approved ON users(is_approved);",
        "CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);",
        "CREATE INDEX IF NOT EXISTS idx_messages_is_spam ON messages(is_spam);"
    ]
    
    try:
        async with pool.acquire() as connection:
            # Create tables
            await connection.execute(create_users_table)
            await connection.execute(create_messages_table)
            
            # Create indexes
            for index_sql in create_indexes:
                await connection.execute(index_sql)
                
            logger.info("Database tables and indexes created successfully")
            
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def add_new_user(
    pool: asyncpg.Pool, 
    user_id: int, 
    username: Optional[str], 
    first_name: Optional[str]
) -> bool:
    """
    Adds a new user to the users table.
    
    Args:
        pool: Database connection pool
        user_id: Telegram user ID
        username: Telegram username (can be None)
        first_name: User's first name (can be None)
        
    Returns:
        bool: True if user was added successfully, False if user already exists
        
    Raises:
        Exception: If database operation fails
    """
    try:
        async with pool.acquire() as connection:
            # Check if user already exists
            existing_user = await connection.fetchrow(
                "SELECT user_id FROM users WHERE user_id = $1",
                user_id
            )
            
            if existing_user:
                logger.info(f"User {user_id} already exists in database")
                return False
            
            # Insert new user
            await connection.execute(
                """
                INSERT INTO users (user_id, username, first_name, join_date)
                VALUES ($1, $2, $3, $4)
                """,
                user_id, username, first_name, datetime.now(timezone.utc)
            )
            
            logger.info(f"Successfully added new user {user_id} ({username}) to database")
            return True
            
    except Exception as e:
        logger.error(f"Failed to add user {user_id}: {e}")
        raise


async def get_user(pool: asyncpg.Pool, user_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieves user information by user ID.
    
    Args:
        pool: Database connection pool
        user_id: Telegram user ID
        
    Returns:
        Optional[Dict[str, Any]]: User data dict or None if user not found
        
    Raises:
        Exception: If database operation fails
    """
    try:
        async with pool.acquire() as connection:
            user_record = await connection.fetchrow(
                """
                SELECT user_id, username, first_name, join_date, is_approved, spam_reports
                FROM users 
                WHERE user_id = $1
                """,
                user_id
            )
            
            if user_record:
                user_data = {
                    'user_id': user_record['user_id'],
                    'username': user_record['username'],
                    'first_name': user_record['first_name'],
                    'join_date': user_record['join_date'],
                    'is_approved': user_record['is_approved'],
                    'spam_reports': user_record['spam_reports']
                }
                logger.debug(f"Retrieved user data for {user_id}")
                return user_data
            else:
                logger.debug(f"User {user_id} not found in database")
                return None
                
    except Exception as e:
        logger.error(f"Failed to get user {user_id}: {e}")
        raise


async def approve_user(pool: asyncpg.Pool, user_id: int) -> bool:
    """
    Approves a user by setting is_approved to TRUE.
    
    Args:
        pool: Database connection pool
        user_id: Telegram user ID
        
    Returns:
        bool: True if user was approved, False if user not found
        
    Raises:
        Exception: If database operation fails
    """
    try:
        async with pool.acquire() as connection:
            result = await connection.execute(
                "UPDATE users SET is_approved = TRUE WHERE user_id = $1",
                user_id
            )
            
            # Check if any rows were affected
            rows_affected = int(result.split()[-1])
            
            if rows_affected > 0:
                logger.info(f"Successfully approved user {user_id}")
                return True
            else:
                logger.warning(f"User {user_id} not found for approval")
                return False
                
    except Exception as e:
        logger.error(f"Failed to approve user {user_id}: {e}")
        raise


async def log_message(
    pool: asyncpg.Pool, 
    user_id: int, 
    message_text: str, 
    is_spam: bool = False
) -> int:
    """
    Logs a message to the messages table.
    
    Args:
        pool: Database connection pool
        user_id: Telegram user ID
        message_text: Text content of the message
        is_spam: Whether the message is classified as spam
        
    Returns:
        int: ID of the inserted message record
        
    Raises:
        Exception: If database operation fails
    """
    try:
        async with pool.acquire() as connection:
            message_id = await connection.fetchval(
                """
                INSERT INTO messages (user_id, message_text, is_spam, timestamp)
                VALUES ($1, $2, $3, $4)
                RETURNING message_id
                """,
                user_id, message_text, is_spam, datetime.now(timezone.utc)
            )
            
            logger.debug(f"Logged message {message_id} from user {user_id} (spam: {is_spam})")
            return message_id
            
    except Exception as e:
        logger.error(f"Failed to log message from user {user_id}: {e}")
        raise


async def increment_spam_reports(pool: asyncpg.Pool, user_id: int) -> bool:
    """
    Increments the spam report count for a user.
    
    Args:
        pool: Database connection pool
        user_id: Telegram user ID
        
    Returns:
        bool: True if spam reports were incremented, False if user not found
        
    Raises:
        Exception: If database operation fails
    """
    try:
        async with pool.acquire() as connection:
            result = await connection.execute(
                "UPDATE users SET spam_reports = spam_reports + 1 WHERE user_id = $1",
                user_id
            )
            
            rows_affected = int(result.split()[-1])
            
            if rows_affected > 0:
                logger.info(f"Incremented spam reports for user {user_id}")
                return True
            else:
                logger.warning(f"User {user_id} not found for spam report increment")
                return False
                
    except Exception as e:
        logger.error(f"Failed to increment spam reports for user {user_id}: {e}")
        raise


async def get_user_stats(pool: asyncpg.Pool) -> Dict[str, int]:
    """
    Gets basic statistics about users in the database.
    
    Args:
        pool: Database connection pool
        
    Returns:
        Dict[str, int]: Dictionary with user statistics
        
    Raises:
        Exception: If database operation fails
    """
    try:
        async with pool.acquire() as connection:
            stats = await connection.fetchrow(
                """
                SELECT 
                    COUNT(*) as total_users,
                    COUNT(*) FILTER (WHERE is_approved = TRUE) as approved_users,
                    COUNT(*) FILTER (WHERE spam_reports > 0) as users_with_reports
                FROM users
                """
            )
            
            return {
                'total_users': stats['total_users'],
                'approved_users': stats['approved_users'],
                'users_with_reports': stats['users_with_reports'],
                'pending_approval': stats['total_users'] - stats['approved_users']
            }
            
    except Exception as e:
        logger.error(f"Failed to get user stats: {e}")
        raise
