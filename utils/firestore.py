import logging
import os
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

load_dotenv()
FIREBASE_KEY = os.getenv("FIREBASE_KEY")

# Initialize Firebase if not already initialized
if not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_KEY)
    firebase_admin.initialize_app(cred)

db = firestore.client()

def fetch_cookies_from_firestore():
    """Fetch account cookies from Firestore."""
    logging.info("Fetching account cookies from Firestore...")
    cookies = {}
    try:
        collection_ref = db.collection("game_cookies")
        documents = collection_ref.stream()

        for doc in documents:
            logging.info(f"Retrieved document: {doc.id}")
            cookies[doc.id] = doc.to_dict()["data"]  # "data" is the list of account dictionaries
    except Exception as e:
        logging.error(f"Error fetching cookies from Firestore: {e}")
    finally:
        logging.info("Account cookies fetched successfully.")
        return cookies

def update_cookie_in_firestore(game_name, cookie_data, append=False):
    """
    Updates or adds cookies in Firestore for the specified game.
    :param game_name: Name of the game (e.g., "genshin", "starrail").
    :param cookie_data: List of cookie dictionaries to be updated.
    :param append: Whether to append to existing cookies (default: False).
    """
    try:
        logging.info(f"Updating cookie for {game_name} in Firestore...")
        collection_ref = db.collection("game_cookies")
        doc_ref = collection_ref.document(game_name)
        doc = doc_ref.get()

        if doc.exists and append:
            existing_data = doc.to_dict().get("data", [])
            cookie_data = existing_data + cookie_data

        doc_ref.set({"data": cookie_data})
        logging.info(f"Cookie for {game_name} updated successfully.")
        return True
    except Exception as e:
        logging.error(f"Error updating cookie for {game_name} in Firestore: {e}")
        return False


def delete_cookie_in_firestore(game_name, account_name):
    """
    Deletes a cookie by account name for the specified game.
    :param game_name: Name of the game (e.g., "genshin", "starrail").
    :param account_name: The name of the account to be deleted.
    """
    logging.info(f"Deleting cookie for account '{account_name}' in game '{game_name}'...")
    try:
        collection_ref = db.collection("game_cookies")
        doc_ref = collection_ref.document(game_name)
        doc = doc_ref.get()

        if doc.exists:
            data = doc.to_dict()["data"]
            updated_data = [account for account in data if account["name"] != account_name]

            if len(updated_data) == len(data):
                logging.warning(f"Account '{account_name}' not found in {game_name}. No deletion performed.")
                return False

            doc_ref.set({"data": updated_data})
            logging.info(f"Account '{account_name}' deleted successfully from {game_name}.")
            return True
        else:
            logging.warning(f"Game '{game_name}' does not exist in Firestore.")
            return False
    except Exception as e:
        logging.error(f"Error deleting cookie for {game_name}: {e}")
        return False

def edit_cookie_in_firestore(game_name, account_name, updated_cookie):
    """
    Edits a cookie for a specific account in Firestore.
    :param game_name: Name of the game (e.g., "genshin", "starrail").
    :param account_name: The name of the account to be edited.
    :param updated_cookie: The updated cookie string.
    """
    logging.info(f"Editing cookie for account '{account_name}' in game '{game_name}'...")
    try:
        collection_ref = db.collection("game_cookies")
        doc_ref = collection_ref.document(game_name)
        doc = doc_ref.get()

        if doc.exists:
            data = doc.to_dict()["data"]
            for account in data:
                if account["name"] == account_name:
                    account["cookie"] = updated_cookie
                    doc_ref.set({"data": data})
                    logging.info(f"Account '{account_name}' updated successfully in {game_name}.")
                    return True

            logging.warning(f"Account '{account_name}' not found in {game_name}. No edit performed.")
            return False
        else:
            logging.warning(f"Game '{game_name}' does not exist in Firestore.")
            return False
    except Exception as e:
        logging.error(f"Error editing cookie for {game_name}: {e}")
        return False

def fetch_all_games():
    """Fetch all game names (document IDs) from Firestore."""
    try:
        logging.info("Fetching all game names...")
        collection_ref = db.collection("game_cookies")
        documents = collection_ref.stream()
        games = [doc.id for doc in documents]
        logging.info(f"Fetched games: {games}")
        return games
    except Exception as e:
        logging.error(f"Error fetching games from Firestore: {e}")
        return []
