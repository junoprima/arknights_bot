"""
Database migration utilities for miHoYo Bot
Handles migration from Firebase to SQLite/PostgreSQL
"""
import asyncio
import logging
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# Firebase imports (for migration only)
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    logging.warning("Firebase not available - migration from Firebase will be skipped")

from database.connection import init_database, db_manager
from database.operations import db_ops

load_dotenv()
logger = logging.getLogger(__name__)


class FirebaseToSQLMigration:
    """Handle migration from Firebase Firestore to SQL database"""

    def __init__(self):
        self.firebase_db = None
        self.migration_log = []

    async def initialize_firebase(self) -> bool:
        """Initialize Firebase connection for migration"""
        if not FIREBASE_AVAILABLE:
            logger.error("Firebase libraries not available. Install with: pip install firebase-admin")
            return False

        try:
            firebase_key_path = os.getenv("FIREBASE_KEY", "firebase_key.json")

            if not os.path.exists(firebase_key_path):
                logger.error(f"Firebase key file not found at: {firebase_key_path}")
                return False

            # Initialize Firebase if not already done
            if not firebase_admin._apps:
                cred = credentials.Certificate(firebase_key_path)
                firebase_admin.initialize_app(cred)

            self.firebase_db = firestore.client()
            logger.info("Firebase initialized successfully for migration")
            return True

        except Exception as e:
            logger.error(f"Error initializing Firebase: {e}")
            return False

    async def fetch_firebase_data(self) -> Dict[str, Any]:
        """Fetch all data from Firebase Firestore"""
        if not self.firebase_db:
            logger.error("Firebase not initialized")
            return {}

        try:
            logger.info("Fetching data from Firebase Firestore...")
            data = {
                "game_cookies": {},
                "guilds": [],
                "users": [],
                "settings": {}
            }

            # Fetch game cookies collection
            cookies_ref = self.firebase_db.collection("game_cookies")
            docs = cookies_ref.stream()

            for doc in docs:
                game_name = doc.id
                doc_data = doc.to_dict()
                data["game_cookies"][game_name] = doc_data.get("data", [])
                logger.info(f"Fetched {len(data['game_cookies'][game_name])} accounts for {game_name}")

            # Fetch other collections if they exist
            collections = ["guilds", "users", "settings"]
            for collection_name in collections:
                try:
                    collection_ref = self.firebase_db.collection(collection_name)
                    docs = collection_ref.stream()
                    data[collection_name] = [{"id": doc.id, "data": doc.to_dict()} for doc in docs]
                except Exception as e:
                    logger.warning(f"Collection {collection_name} not found or error: {e}")

            logger.info("Firebase data fetched successfully")
            return data

        except Exception as e:
            logger.error(f"Error fetching Firebase data: {e}")
            return {}

    async def migrate_games_data(self) -> bool:
        """Migrate games data (already handled by init_database)"""
        try:
            logger.info("Games data migration completed during database initialization")
            self.migration_log.append("✅ Games data migrated successfully")
            return True
        except Exception as e:
            logger.error(f"Error migrating games: {e}")
            self.migration_log.append(f"❌ Games migration failed: {e}")
            return False

    async def migrate_accounts_data(self, firebase_data: Dict[str, Any], default_guild_id: int) -> bool:
        """Migrate account cookies from Firebase to SQL"""
        try:
            logger.info("Migrating account data...")
            game_cookies = firebase_data.get("game_cookies", {})

            if not game_cookies:
                logger.warning("No account data found in Firebase")
                self.migration_log.append("⚠️ No account data found to migrate")
                return True

            # Since Firebase didn't store guild/user associations, we'll assign to default guild
            # and create dummy users
            migrated_accounts = 0

            for game_name, accounts in game_cookies.items():
                logger.info(f"Migrating {len(accounts)} accounts for {game_name}")

                for account in accounts:
                    try:
                        account_name = account.get("name", "Unknown")
                        cookie = account.get("cookie", "")

                        if not cookie:
                            logger.warning(f"Skipping account {account_name} - no cookie")
                            continue

                        # Create dummy user for migration
                        user_id = hash(account_name) % 1000000000  # Generate consistent user ID
                        await db_ops.register_user(
                            user_id=user_id,
                            username=f"migrated_user_{account_name}",
                            discriminator=None
                        )

                        # Add guild membership
                        await db_ops.add_guild_member(default_guild_id, user_id)

                        # Add account
                        await db_ops.add_account(
                            guild_id=default_guild_id,
                            user_id=user_id,
                            game_name=game_name,
                            account_name=account_name,
                            cookie=cookie
                        )

                        migrated_accounts += 1
                        logger.debug(f"Migrated account: {account_name} for {game_name}")

                    except Exception as e:
                        logger.error(f"Error migrating account {account.get('name', 'Unknown')}: {e}")

            logger.info(f"Account migration completed. Migrated {migrated_accounts} accounts")
            self.migration_log.append(f"✅ Migrated {migrated_accounts} accounts successfully")
            return True

        except Exception as e:
            logger.error(f"Error migrating accounts: {e}")
            self.migration_log.append(f"❌ Account migration failed: {e}")
            return False

    async def create_default_guild(self, guild_id: Optional[int] = None, guild_name: str = "Migrated Guild") -> int:
        """Create a default guild for migration"""
        try:
            if not guild_id:
                guild_id = int(os.getenv("DISCORD_GUILD_ID", "123456789"))

            logger.info(f"Creating default guild: {guild_name} ({guild_id})")

            await db_ops.register_guild(
                guild_id=guild_id,
                guild_name=guild_name,
                webhook_url=os.getenv("DISCORD_WEBHOOK")
            )

            self.migration_log.append(f"✅ Created default guild: {guild_name}")
            return guild_id

        except Exception as e:
            logger.error(f"Error creating default guild: {e}")
            self.migration_log.append(f"❌ Failed to create default guild: {e}")
            raise

    async def backup_firebase_data(self, data: Dict[str, Any]) -> str:
        """Create a backup of Firebase data"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"firebase_backup_{timestamp}.json"
            backup_path = os.path.join("backups", backup_filename)

            # Create backups directory
            os.makedirs("backups", exist_ok=True)

            with open(backup_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)

            logger.info(f"Firebase data backed up to: {backup_path}")
            self.migration_log.append(f"✅ Backup created: {backup_filename}")
            return backup_path

        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            self.migration_log.append(f"❌ Backup failed: {e}")
            return ""

    async def run_migration(self, guild_id: Optional[int] = None, guild_name: str = "Migrated Guild") -> bool:
        """Run complete migration process"""
        logger.info("🚀 Starting Firebase to SQL migration...")
        self.migration_log.append("🚀 Migration started")

        try:
            # Initialize SQL database
            await init_database()
            self.migration_log.append("✅ SQL database initialized")

            # Initialize Firebase
            if not await self.initialize_firebase():
                logger.error("Firebase initialization failed - migration aborted")
                return False

            # Fetch Firebase data
            firebase_data = await self.fetch_firebase_data()
            if not firebase_data:
                logger.error("No data fetched from Firebase - migration aborted")
                return False

            # Create backup
            await self.backup_firebase_data(firebase_data)

            # Create default guild
            default_guild_id = await self.create_default_guild(guild_id, guild_name)

            # Migrate games (handled by init_database)
            await self.migrate_games_data()

            # Migrate accounts
            await self.migrate_accounts_data(firebase_data, default_guild_id)

            logger.info("🎉 Migration completed successfully!")
            self.migration_log.append("🎉 Migration completed successfully")

            # Print migration summary
            print("\n" + "="*60)
            print("🔄 MIGRATION SUMMARY")
            print("="*60)
            for log_entry in self.migration_log:
                print(log_entry)
            print("="*60)

            return True

        except Exception as e:
            logger.error(f"Migration failed: {e}")
            self.migration_log.append(f"❌ Migration failed: {e}")
            return False

        finally:
            await db_manager.close()


async def run_migration_cli():
    """CLI interface for running migration"""
    print("🔄 miHoYo Bot Database Migration Tool")
    print("="*50)

    migration = FirebaseToSQLMigration()

    # Get guild information
    guild_id = input("Enter Discord Guild ID (press Enter for default): ").strip()
    if guild_id:
        try:
            guild_id = int(guild_id)
        except ValueError:
            print("❌ Invalid Guild ID. Using default.")
            guild_id = None
    else:
        guild_id = None

    guild_name = input("Enter Guild Name (press Enter for 'Migrated Guild'): ").strip()
    if not guild_name:
        guild_name = "Migrated Guild"

    print(f"\n🚀 Starting migration...")
    print(f"Guild ID: {guild_id or 'Default'}")
    print(f"Guild Name: {guild_name}")
    print("-" * 50)

    success = await migration.run_migration(guild_id, guild_name)

    if success:
        print("\n✅ Migration completed successfully!")
        print("\nNext steps:")
        print("1. Update your Docker configuration to use the new database")
        print("2. Test the bot with the new database")
        print("3. Update environment variables")
        print("4. Remove Firebase dependencies if no longer needed")
    else:
        print("\n❌ Migration failed. Check logs for details.")

    return success


if __name__ == "__main__":
    asyncio.run(run_migration_cli())