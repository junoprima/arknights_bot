"""
Database models for miHoYo Bot
Replaces Firebase Firestore with SQLAlchemy ORM
"""
from datetime import datetime, date
from typing import Optional, List
from sqlalchemy import BigInteger, String, Text, Boolean, Integer, Date, DateTime, ForeignKey
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from cryptography.fernet import Fernet
import os


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all database models"""
    pass


class Guild(Base):
    __tablename__ = "guilds"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    webhook_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    language: Mapped[str] = mapped_column(String(10), default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    accounts: Mapped[List["Account"]] = relationship("Account", back_populates="guild")
    settings: Mapped[List["GuildSetting"]] = relationship("GuildSetting", back_populates="guild")
    members: Mapped[List["GuildMember"]] = relationship("GuildMember", back_populates="guild")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    discriminator: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    accounts: Mapped[List["Account"]] = relationship("Account", back_populates="user")
    guild_memberships: Mapped[List["GuildMember"]] = relationship("GuildMember", back_populates="user")


class GuildMember(Base):
    __tablename__ = "guild_members"

    guild_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("guilds.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    guild: Mapped["Guild"] = relationship("Guild", back_populates="members")
    user: Mapped["User"] = relationship("User", back_populates="guild_memberships")


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    act_id: Mapped[str] = mapped_column(String(100), nullable=False)
    sign_game_header: Mapped[str] = mapped_column(String(50), nullable=False)
    success_message: Mapped[str] = mapped_column(Text, nullable=False)
    signed_message: Mapped[str] = mapped_column(Text, nullable=False)
    game_id: Mapped[int] = mapped_column(Integer, nullable=False)
    author_name: Mapped[str] = mapped_column(String(100), nullable=False)
    icon_url: Mapped[str] = mapped_column(Text, nullable=False)
    info_url: Mapped[str] = mapped_column(Text, nullable=False)
    home_url: Mapped[str] = mapped_column(Text, nullable=False)
    sign_url: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    accounts: Mapped[List["Account"]] = relationship("Account", back_populates="game")


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("guilds.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    game_id: Mapped[int] = mapped_column(Integer, ForeignKey("games.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    cookie: Mapped[str] = mapped_column(Text, nullable=False)  # Encrypted
    uid: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    nickname: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    region: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    guild: Mapped["Guild"] = relationship("Guild", back_populates="accounts")
    user: Mapped["User"] = relationship("User", back_populates="accounts")
    game: Mapped["Game"] = relationship("Game", back_populates="accounts")
    checkin_logs: Mapped[List["CheckinLog"]] = relationship("CheckinLog", back_populates="account")

    @property
    def decrypted_cookie(self) -> str:
        """Decrypt and return the cookie"""
        encryption_key = os.getenv("ENCRYPTION_KEY")
        if not encryption_key:
            return self.cookie  # Fallback if no encryption

        try:
            fernet = Fernet(encryption_key.encode())
            return fernet.decrypt(self.cookie.encode()).decode()
        except:
            return self.cookie  # Fallback if decryption fails

    def set_encrypted_cookie(self, cookie: str) -> None:
        """Encrypt and set the cookie"""
        encryption_key = os.getenv("ENCRYPTION_KEY")
        if not encryption_key:
            self.cookie = cookie  # Fallback if no encryption
            return

        try:
            fernet = Fernet(encryption_key.encode())
            self.cookie = fernet.encrypt(cookie.encode()).decode()
        except:
            self.cookie = cookie  # Fallback if encryption fails


class CheckinLog(Base):
    __tablename__ = "checkin_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"))
    checkin_date: Mapped[date] = mapped_column(Date, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reward_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reward_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    reward_icon: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    total_checkins: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    account: Mapped["Account"] = relationship("Account", back_populates="checkin_logs")


class GuildSetting(Base):
    __tablename__ = "guild_settings"

    guild_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("guilds.id", ondelete="CASCADE"), primary_key=True)
    setting_key: Mapped[str] = mapped_column(String(100), primary_key=True)
    setting_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    guild: Mapped["Guild"] = relationship("Guild", back_populates="settings")