"""
Optimized SQLite configuration for DigitalOcean 1GB RAM server
"""
import os
from sqlalchemy import event
from sqlalchemy.engine import Engine
import sqlite3


def configure_sqlite_engine(engine):
    """Configure SQLite engine with performance optimizations for low-memory server"""

    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """Set SQLite PRAGMA statements for optimal performance"""
        if isinstance(dbapi_connection, sqlite3.Connection):
            cursor = dbapi_connection.cursor()

            # Performance optimizations for 1GB RAM server
            cursor.execute("PRAGMA journal_mode=WAL")           # Write-Ahead Logging
            cursor.execute("PRAGMA synchronous=NORMAL")        # Balance safety/performance
            cursor.execute("PRAGMA cache_size=8000")           # 8MB cache (conservative)
            cursor.execute("PRAGMA temp_store=memory")         # Temp tables in RAM
            cursor.execute("PRAGMA mmap_size=268435456")       # 256MB memory mapping

            # Connection optimizations
            cursor.execute("PRAGMA busy_timeout=30000")        # 30 second timeout
            cursor.execute("PRAGMA foreign_keys=ON")          # Enable foreign keys

            # For concurrent access
            cursor.execute("PRAGMA wal_autocheckpoint=1000")   # Checkpoint every 1000 pages

            cursor.close()


# Optimized connection settings for your server
SQLITE_CONNECTION_CONFIG = {
    "pool_size": 5,                    # Small pool for 1GB RAM
    "max_overflow": 10,                # Limited overflow
    "pool_timeout": 30,
    "pool_recycle": 3600,              # Recycle connections every hour
    "pool_pre_ping": True,
    "connect_args": {
        "check_same_thread": False,    # Allow multi-threading
        "timeout": 30                  # Connection timeout
    }
}