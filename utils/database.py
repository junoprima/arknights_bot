import logging

async def fetch_all_games():
    """Fetch all games from database"""
    try:
        from database.connection import db_manager
        from database.models import Game
        from sqlalchemy import select
        
        async with db_manager.get_session() as session:
            stmt = select(Game).where(Game.is_active == True)
            result = await session.execute(stmt)
            games = result.scalars().all()
            return [game.name for game in games]
    except Exception as e:
        logging.error(f"[DATABASE] fetch_all_games failed: {e}")
        # Fallback to endfield for arknights bot
        return ["endfield"]

async def get_guild_accounts(guild_id, game):
    from database.operations import db_ops
    try:
        accounts = await db_ops.get_accounts_by_game(guild_id, game)
        return accounts
    except:
        return []

async def get_account_names_for_game(guild_id, game):
    from database.operations import db_ops
    try:
        accounts = await db_ops.get_accounts_by_game(guild_id, game)
        return [acc.name for acc in accounts]
    except:
        return []

async def update_cookie_in_database(guild_id, user_id, game_name, account_name, cookie):
    from database.operations import db_ops
    try:
        await db_ops.add_account(guild_id, user_id, game_name, account_name, cookie)
        logging.info(f"[DATABASE] update_cookie_in_database success")
        return True
    except Exception as e:
        logging.error(f"[DATABASE] update_cookie_in_database failed: {e}")
        return False

async def delete_cookie_in_database(guild_id, user_id, game_name, account_name):
    from database.operations import db_ops
    try:
        result = await db_ops.delete_account(guild_id, user_id, game_name, account_name)
        if result:
            logging.info(f"[DATABASE] delete_cookie_in_database success: {account_name}")
            return True
        else:
            logging.warning(f"[DATABASE] delete_cookie_in_database: no matching record found for {account_name}")
            return False
    except Exception as e:
        logging.error(f"[DATABASE] delete_cookie_in_database failed: {e}")
        return False

async def edit_cookie_in_database(guild_id, user_id, game_name, account_name, new_cookie):
    logging.info(f"[DATABASE] edit_cookie_in_database called with guild_id={guild_id}, user_id={user_id}, game_name={game_name}, account_name={account_name}")
    from database.operations import db_ops
    try:
        result = await db_ops.update_account_cookie(guild_id, user_id, game_name, account_name, new_cookie)
        if result:
            logging.info(f"[DATABASE] edit_cookie_in_database success")
            return True
        else:
            logging.warning(f"[DATABASE] edit_cookie_in_database: no matching record found")
            return False
    except Exception as e:
        logging.error(f"[DATABASE] edit_cookie_in_database failed: {e}")
        return False

async def fetch_cookies_from_database(guild_id: int):
    from database.operations import db_ops
    try:
        accounts_by_game = await db_ops.get_guild_accounts_for_checkin(guild_id)
        cookies = {}
        for game_name, accounts in accounts_by_game.items():
            cookies[game_name] = []
            for account in accounts:
                cookies[game_name].append({
                    'name': account.name,
                    'cookie': account.decrypted_cookie
                })
        return cookies
    except Exception as e:
        print(f'Error fetching cookies for guild {guild_id}: {e}')
        return {}
