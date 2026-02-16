"""
Database connection management for miHoYo Bot
"""
import os
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import create_engine
from dotenv import load_dotenv

from .models import Base

load_dotenv()

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Database connection manager with async support"""

    def __init__(self):
        self._engine = None
        self._async_session = None
        self._sync_engine = None

    def get_database_url(self) -> str:
        """Get database URL from environment variables"""
        # For SQLite (recommended for 1GB RAM server)
        db_path = os.getenv('DB_PATH', '/app/data/mihoyo_bot.db')
        return f"sqlite+aiosqlite:///{db_path}"

        # PostgreSQL option (requires 4GB+ RAM server)
        # if all(env in os.environ for env in ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']):
        #     return (
        #         f"postgresql+asyncpg://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        #         f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
        #     )

    def get_sync_database_url(self) -> str:
        """Get synchronous database URL for migrations"""
        # For SQLite (recommended for 1GB RAM server)
        db_path = os.getenv('DB_PATH', '/app/data/mihoyo_bot.db')
        return f"sqlite:///{db_path}"

    @property
    def engine(self):
        """Get async database engine"""
        if self._engine is None:
            database_url = self.get_database_url()
            logger.info(f"Creating database engine for: {database_url.split('@')[0]}@***")

            # Import SQLite config for performance optimization
            from .sqlite_config import SQLITE_CONNECTION_CONFIG, configure_sqlite_engine

            self._engine = create_async_engine(
                database_url,
                echo=os.getenv("DB_ECHO", "false").lower() == "true",
                **SQLITE_CONNECTION_CONFIG
            )

            # Configure SQLite specific optimizations
            if "sqlite" in database_url:
                configure_sqlite_engine(self._engine)
        return self._engine

    @property
    def sync_engine(self):
        """Get sync database engine for migrations"""
        if self._sync_engine is None:
            database_url = self.get_sync_database_url()
            self._sync_engine = create_engine(
                database_url,
                echo=os.getenv("DB_ECHO", "false").lower() == "true"
            )
        return self._sync_engine

    @property
    def session_factory(self):
        """Get async session factory"""
        if self._async_session is None:
            self._async_session = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=True,
                autocommit=False
            )
        return self._async_session

    def get_session(self) -> AsyncSession:
        """Get async database session"""
        return self.session_factory()

    async def create_tables(self):
        """Create all database tables"""
        logger.info("Creating database tables...")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")

    async def drop_tables(self):
        """Drop all database tables (use with caution!)"""
        logger.warning("Dropping all database tables...")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("Database tables dropped")

    async def close(self):
        """Close database connections"""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._async_session = None

        if self._sync_engine:
            self._sync_engine.dispose()
            self._sync_engine = None

        logger.info("Database connections closed")


# Global database manager instance
db_manager = DatabaseManager()


async def get_db_session() -> AsyncSession:
    """Dependency for getting database session"""
    session = db_manager.get_session()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def init_database():
    """Initialize database tables and default data"""
    logger.info("Initializing database...")
    await db_manager.create_tables()

    # Insert default games data
    session = db_manager.get_session()
    try:
        from .models import Game
        from sqlalchemy import select

        # Check if games already exist
        result = await session.execute(select(Game))
        existing_games = result.scalars().all()

        if not existing_games:
            logger.info("Inserting default games data...")
            games_data = [
                {
                    "name": "genshin",
                    "display_name": "Genshin Impact",
                    "act_id": "e202102251931481",
                    "sign_game_header": "hk4e",
                    "success_message": "Congratulations, Traveler! You have successfully checked in today~",
                    "signed_message": "Traveler, you've already checked in today~",
                    "game_id": 2,
                    "author_name": "Paimon",
                    "icon_url": "https://fastcdn.hoyoverse.com/static-resource-v2/2024/04/12/b700cce2ac4c68a520b15cafa86a03f0_2812765778371293568.png",
                    "info_url": "https://sg-hk4e-api.hoyolab.com/event/sol/info",
                    "home_url": "https://sg-hk4e-api.hoyolab.com/event/sol/home",
                    "sign_url": "https://sg-hk4e-api.hoyolab.com/event/sol/sign"
                },
                {
                    "name": "honkai",
                    "display_name": "Honkai Impact 3rd",
                    "act_id": "e202110291205111",
                    "sign_game_header": "honkai",
                    "success_message": "You have successfully checked in today, Captain~",
                    "signed_message": "You've already checked in today, Captain~",
                    "game_id": 1,
                    "author_name": "Kiana",
                    "icon_url": "https://fastcdn.hoyoverse.com/static-resource-v2/2024/02/29/3d96534fd7a35a725f7884e6137346d1_3942255444511793944.png",
                    "info_url": "https://sg-public-api.hoyolab.com/event/mani/info",
                    "home_url": "https://sg-public-api.hoyolab.com/event/mani/home",
                    "sign_url": "https://sg-public-api.hoyolab.com/event/mani/sign"
                },
                {
                    "name": "zenless",
                    "display_name": "Zenless Zone Zero",
                    "act_id": "e202406031448091",
                    "sign_game_header": "zzz",
                    "success_message": "Congratulations Proxy! You have successfully checked in today!~",
                    "signed_message": "You have already checked in today, Proxy!~",
                    "game_id": 8,
                    "author_name": "Eous",
                    "icon_url": "https://hyl-static-res-prod.hoyolab.com/communityweb/business/nap.png",
                    "info_url": "https://sg-public-api.hoyolab.com/event/luna/zzz/os/info",
                    "home_url": "https://sg-public-api.hoyolab.com/event/luna/zzz/os/home",
                    "sign_url": "https://sg-public-api.hoyolab.com/event/luna/zzz/os/sign"
                },
                {
                    "name": "starrail",
                    "display_name": "Honkai: Star Rail",
                    "act_id": "e202303301540311",
                    "sign_game_header": "hkrpg",
                    "success_message": "You have successfully checked in today, Trailblazer~",
                    "signed_message": "You've already checked in today, Trailblazer~",
                    "game_id": 6,
                    "author_name": "PomPom",
                    "icon_url": "https://fastcdn.hoyoverse.com/static-resource-v2/2024/04/12/74330de1ee71ada37bbba7b72775c9d3_1883015313866544428.png",
                    "info_url": "https://sg-public-api.hoyolab.com/event/luna/os/info",
                    "home_url": "https://sg-public-api.hoyolab.com/event/luna/os/home",
                    "sign_url": "https://sg-public-api.hoyolab.com/event/luna/os/sign"
                }
            ]

            for game_data in games_data:
                game = Game(**game_data)
                session.add(game)

            await session.commit()
            logger.info("Default games data inserted successfully")

    finally:
        await session.close()

    logger.info("Database initialization completed")