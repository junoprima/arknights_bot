import logging
async def fetch_all_games():
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
        logging.info(f"[DATABASE] edit_cookie_in_database success")
        return True
    except:
        logging.error(f"[DATABASE] edit_cookie_in_database failed with exception")
        return False

async def delete_cookie_in_database(guild_id, user_id, game_name, account_name):
    from database.operations import db_ops
    try:
        await db_ops.delete_account(guild_id, user_id, game_name, account_name)
        logging.info(f"[DATABASE] edit_cookie_in_database success")
        return True
    except:
        logging.error(f"[DATABASE] edit_cookie_in_database failed with exception")
        return False

async def edit_cookie_in_database(guild_id, user_id, game_name, account_name, new_cookie):
    import logging
    logging.info(f"[DATABASE] edit_cookie_in_database called with guild_id={guild_id}, user_id={user_id}, game_name={game_name}, account_name={account_name}")
    from database.operations import db_ops
    try:
        await db_ops.update_account_cookie(guild_id, user_id, game_name, account_name, new_cookie)
        logging.info(f"[DATABASE] edit_cookie_in_database success")
        return True
    except:
        logging.error(f"[DATABASE] edit_cookie_in_database failed with exception")
        return False

async def fetch_cookies_from_database(guild_id: int):
    from database.operations import db_ops
    try:
        # Get accounts for this guild organized by game
        accounts_by_game = await db_ops.get_guild_accounts_for_checkin(guild_id)

        # Convert Account objects to dictionaries for compatibility
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