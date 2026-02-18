"""
Database operations layer - replaces Firebase Firestore
Optimized for SQLite with advanced features
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from .models import Guild, User, Account, Game, CheckinLog, GuildSetting, GuildMember
from .connection import get_db_session, db_manager

logger = logging.getLogger(__name__)


class DatabaseOperations:
    """High-performance database operations with caching and optimization"""

    def __init__(self):
        self._game_cache = {}
        self._guild_cache = {}

    # === GUILD OPERATIONS ===
    async def register_guild(self, guild_id: int, guild_name: str, webhook_url: Optional[str] = None) -> Guild:
        """Register a new Discord guild with auto-detection"""
        async with db_manager.get_session() as session:
            # Check if guild exists
            stmt = select(Guild).where(Guild.id == guild_id)
            result = await session.execute(stmt)
            guild = result.scalar_one_or_none()

            if guild:
                # Update existing guild
                guild.name = guild_name
                guild.webhook_url = webhook_url or guild.webhook_url
                guild.updated_at = datetime.utcnow()
                guild.is_active = True
            else:
                # Create new guild
                guild = Guild(
                    id=guild_id,
                    name=guild_name,
                    webhook_url=webhook_url,
                    timezone="UTC",
                    language="en"
                )
                session.add(guild)

            await session.commit()
            await session.refresh(guild)

            # Cache the guild
            self._guild_cache[guild_id] = guild

            logger.info(f"Guild registered: {guild_name} ({guild_id})")
            return guild

    async def get_guild(self, guild_id: int) -> Optional[Guild]:
        """Get guild with caching"""
        if guild_id in self._guild_cache:
            return self._guild_cache[guild_id]

        async with db_manager.get_session() as session:
            stmt = select(Guild).where(Guild.id == guild_id)
            result = await session.execute(stmt)
            guild = result.scalar_one_or_none()

            if guild:
                self._guild_cache[guild_id] = guild

            return guild

    async def get_guild_webhook(self, guild_id: int) -> Optional[str]:
        """Get guild webhook URL"""
        guild = await self.get_guild(guild_id)
        return guild.webhook_url if guild else None

    # === USER OPERATIONS ===
    async def register_user(self, user_id: int, username: str, discriminator: Optional[str] = None) -> User:
        """Register or update Discord user"""
        async with db_manager.get_session() as session:
            stmt = select(User).where(User.id == user_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if user:
                user.username = username
                user.discriminator = discriminator
                user.updated_at = datetime.utcnow()
            else:
                user = User(
                    id=user_id,
                    username=username,
                    discriminator=discriminator
                )
                session.add(user)

            await session.commit()
            await session.refresh(user)
            return user

    async def add_guild_member(self, guild_id: int, user_id: int) -> None:
        """Add user to guild membership"""
        async with db_manager.get_session() as session:
            # Check if membership exists
            stmt = select(GuildMember).where(
                and_(GuildMember.guild_id == guild_id, GuildMember.user_id == user_id)
            )
            result = await session.execute(stmt)
            membership = result.scalar_one_or_none()

            if not membership:
                membership = GuildMember(guild_id=guild_id, user_id=user_id)
                session.add(membership)
                await session.commit()

    # === GAME OPERATIONS ===
    async def get_games(self) -> List[Game]:
        """Get all active games with caching"""
        if not self._game_cache:
            async with db_manager.get_session() as session:
                stmt = select(Game).where(Game.is_active == True)
                result = await session.execute(stmt)
                games = result.scalars().all()

                for game in games:
                    self._game_cache[game.name] = game

        return list(self._game_cache.values())

    async def get_game_by_name(self, game_name: str) -> Optional[Game]:
        """Get game by name with caching"""
        if game_name not in self._game_cache:
            await self.get_games()  # Load cache if empty

        return self._game_cache.get(game_name)

    async def get_game_config(self, game_name: str) -> Optional[Dict[str, Any]]:
        """Get game configuration in legacy format for compatibility"""
        game = await self.get_game_by_name(game_name)
        if not game:
            return None

        config = {
            "ACT_ID": game.act_id,
            "signGameHeader": game.sign_game_header,
            "successMessage": game.success_message,
            "signedMessage": game.signed_message,
            "game": game.display_name,
            "gameId": game.game_id,
            "assets": {
                "author": game.author_name,
                "game": game.display_name,
                "icon": game.icon_url
            },
            "url": {
                "info": game.info_url,
                "home": game.home_url,
                "sign": game.sign_url
            }
        }

        # Load api_type from constants.json if available
        try:
            import json
            import os
            constants_path = os.getenv("CONSTANTS_PATH", "/app/constants.json")
            with open(constants_path, "r") as f:
                constants = json.load(f)
            if game_name in constants and "api_type" in constants[game_name]:
                config["api_type"] = constants[game_name]["api_type"]
        except Exception:
            pass

        return config

    # === ACCOUNT OPERATIONS ===
    async def add_account(self, guild_id: int, user_id: int, game_name: str,
                         account_name: str, cookie: str) -> Account:
        """Add new account with encrypted cookie"""
        async with db_manager.get_session() as session:
            # Get game ID
            game = await self.get_game_by_name(game_name)
            if not game:
                raise ValueError(f"Game '{game_name}' not found")

            # Check if account exists
            stmt = select(Account).where(
                and_(
                    Account.guild_id == guild_id,
                    # Account.user_id == user_id,  # Removed: allow admin to delete any account
                    Account.game_id == game.id,
                    Account.name == account_name
                )
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing account
                existing.set_encrypted_cookie(cookie)
                existing.updated_at = datetime.utcnow()
                existing.is_active = True
                account = existing
            else:
                # Create new account
                account = Account(
                    guild_id=guild_id,
                    user_id=user_id,
                    game_id=game.id,
                    name=account_name
                )
                account.set_encrypted_cookie(cookie)
                session.add(account)

            await session.commit()
            await session.refresh(account)
            logger.info(f"Account added: {account_name} for {game_name} in guild {guild_id}")
            return account

    async def get_accounts_by_game(self, guild_id: int, game_name: str) -> List[Account]:
        """Get all accounts for a specific game in a guild"""
        async with db_manager.get_session() as session:
            game = await self.get_game_by_name(game_name)
            if not game:
                return []

            stmt = (
                select(Account)
                .options(joinedload(Account.user), joinedload(Account.game))
                .where(
                    and_(
                        Account.guild_id == guild_id,
                        Account.game_id == game.id,
                        Account.is_active == True
                    )
                )
            )
            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_all_accounts_for_checkin(self) -> Dict[str, List[Account]]:
        """Get all active accounts grouped by game for check-in process"""
        async with db_manager.get_session() as session:
            stmt = (
                select(Account)
                .options(joinedload(Account.game), joinedload(Account.guild))
                .where(Account.is_active == True)
            )
            result = await session.execute(stmt)
            accounts = result.scalars().all()

            # Group by game name
            grouped = {}
            for account in accounts:
                game_name = account.game.name
                if game_name not in grouped:
                    grouped[game_name] = []
                grouped[game_name].append(account)

            return grouped

    async def get_guild_accounts_for_checkin(self, guild_id: int) -> Dict[str, List[Account]]:
        """Get all active accounts for a specific guild grouped by game for check-in process"""
        async with db_manager.get_session() as session:
            stmt = (
                select(Account)
                .options(joinedload(Account.game), joinedload(Account.guild))
                .where(and_(Account.is_active == True, Account.guild_id == guild_id))
            )
            result = await session.execute(stmt)
            accounts = result.scalars().all()

            # Group by game name
            grouped = {}
            for account in accounts:
                game_name = account.game.name
                if game_name not in grouped:
                    grouped[game_name] = []
                grouped[game_name].append(account)

            return grouped

    async def get_all_guilds_with_accounts(self) -> List[Guild]:
        """Get all guilds that have active accounts"""
        async with db_manager.get_session() as session:
            stmt = (
                select(Guild)
                .join(Account)
                .where(Account.is_active == True)
                .distinct()
            )
            result = await session.execute(stmt)
            guilds = result.scalars().all()
            return guilds

    async def update_account_details(self, account_id: int, uid: str, nickname: str,
                                   rank: int, region: str) -> None:
        """Update account game details"""
        async with db_manager.get_session() as session:
            stmt = (
                update(Account)
                .where(Account.id == account_id)
                .values(
                    uid=uid,
                    nickname=nickname,
                    rank=rank,
                    region=region,
                    updated_at=datetime.utcnow()
                )
            )
            await session.execute(stmt)
            await session.commit()

    async def delete_account(self, guild_id: int, user_id: int, game_name: str, account_name: str) -> bool:
        """Delete account"""
        async with db_manager.get_session() as session:
            game = await self.get_game_by_name(game_name)
            if not game:
                return False

            stmt = delete(Account).where(
                and_(
                    Account.guild_id == guild_id,
                    # Account.user_id == user_id,  # Removed: allow admin to delete any account
                    Account.game_id == game.id,
                    Account.name == account_name
                )
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    # === CHECK-IN LOGGING ===
    async def log_checkin(self, account_id: int, success: bool, reward_name: Optional[str] = None,
                         reward_count: Optional[int] = None, reward_icon: Optional[str] = None,
                         total_checkins: Optional[int] = None, error_message: Optional[str] = None) -> None:
        """Log check-in attempt"""
        async with db_manager.get_session() as session:
            today = date.today()

            # Check if log exists for today
            stmt = select(CheckinLog).where(
                and_(CheckinLog.account_id == account_id, CheckinLog.checkin_date == today)
            )
            result = await session.execute(stmt)
            log = result.scalar_one_or_none()

            if log:
                # Update existing log
                log.success = success
                log.reward_name = reward_name
                log.reward_count = reward_count
                log.reward_icon = reward_icon
                log.total_checkins = total_checkins
                log.error_message = error_message
            else:
                # Create new log
                log = CheckinLog(
                    account_id=account_id,
                    checkin_date=today,
                    success=success,
                    reward_name=reward_name,
                    reward_count=reward_count,
                    reward_icon=reward_icon,
                    total_checkins=total_checkins,
                    error_message=error_message
                )
                session.add(log)

            await session.commit()

    async def get_checkin_stats(self, guild_id: int, days: int = 30) -> Dict[str, Any]:
        """Get check-in statistics for guild"""
        session = db_manager.get_session()
        try:
            # Simplified stats - just return empty for now since it's not critical for migration
            return {}
        finally:
            await session.close()

    # === GUILD SETTINGS ===
    async def set_guild_setting(self, guild_id: int, key: str, value: str) -> None:
        """Set guild-specific setting"""
        async with db_manager.get_session() as session:
            stmt = select(GuildSetting).where(
                and_(GuildSetting.guild_id == guild_id, GuildSetting.setting_key == key)
            )
            result = await session.execute(stmt)
            setting = result.scalar_one_or_none()

            if setting:
                setting.setting_value = value
                setting.updated_at = datetime.utcnow()
            else:
                setting = GuildSetting(
                    guild_id=guild_id,
                    setting_key=key,
                    setting_value=value
                )
                session.add(setting)

            await session.commit()

    async def get_guild_setting(self, guild_id: int, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get guild-specific setting"""
        async with db_manager.get_session() as session:
            stmt = select(GuildSetting).where(
                and_(GuildSetting.guild_id == guild_id, GuildSetting.setting_key == key)
            )
            result = await session.execute(stmt)
            setting = result.scalar_one_or_none()

            return setting.setting_value if setting else default

    async def update_account_cookie(self, guild_id: int, user_id: int, game_name: str, account_name: str, new_cookie: str) -> bool:
        """Update account cookie"""
        async with db_manager.get_session() as session:
            # Get the game
            game = await self.get_game_by_name(game_name)
            if not game:
                return False

            # Find and update the account
            stmt = (
                update(Account)
                .where(
                    and_(
                        Account.guild_id == guild_id,
                        # Account.user_id == user_id,  # Removed: allow admin to delete any account
                        Account.game_id == game.id,
                        Account.name == account_name,
                        Account.is_active == True
                    )
                )
                .values(
                    cookie=new_cookie,
                    updated_at=datetime.utcnow()
                )
            )
            result = await session.execute(stmt)
            await session.commit()

            return result.rowcount > 0


# Global instance
db_ops = DatabaseOperations()