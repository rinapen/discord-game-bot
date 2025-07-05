import pymongo
import config
import datetime
from datetime import timedelta

client = pymongo.MongoClient(config.MONGO_URI)
db = client[config.DB_NAME]

tokens_collection = db[config.TOKENS_COLLECTION]
blacklist_collection = db[config.BLACKLIST_COLLECTION]
user_transactions_collection = db[config.USER_TRANSACTIONS_COLLECTION]
casino_transactions_collection = db[config.CASINO_TRANSACTION_COLLECTION]
users_collection = db[config.USERS_COLLECTION]
casino_stats_collection = db[config.CASINO_STATS_COLLECTION]
models_collection = db[config.MODELS_COLLECTION]
bet_history_collection = db[config.BET_HISTORY_COLLECTION]
bot_state_collection = db[config.BOT_STATE_COLLECTION]

invited_users_collection = db["invited_users"]
invites_collection = db["invites"]
invite_redeem_collection = db["invite_redeem"] 
active_users_collection = db["active_users"]

pf_collection = db["pf_params"]

def load_pf_params(user_id: int):
    doc = pf_collection.find_one({"user_id": user_id})
    if doc:
        return doc.get("client_seed"), doc.get("nonce", 0)
    return None, None

def save_pf_params(user_id: int, client_seed: str, server_seed: str, nonce: int):
    pf_collection.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "client_seed": client_seed,
                "server_seed": server_seed,
                "nonce": nonce
            }
        },
        upsert=True
    )

def is_blacklisted(user_id: int) -> bool:
    return blacklist_collection.find_one({"user_id": user_id}) is not None

def get_tokens():
    return tokens_collection.find_one({}) or {}

def save_tokens(access_token, refresh_token, device_uuid):
    tokens_collection.update_one({}, {"$set": {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "device_uuid": device_uuid
    }}, upsert=True)

def get_user_balance(user_id):
    user = users_collection.find_one({"user_id": user_id})
    return user["balance"] if user else None

def update_user_balance(user_id, amount):
    """ユーザーのPNC残高を更新（増減）"""
    users_collection.update_one(
        {"user_id": user_id},
        {"$inc": {"balance": amount}},
        upsert=True
    )

def update_user_streak(user_id, game_type, is_win):
    """勝敗の連勝・連敗データを更新"""
    user_data = users_collection.find_one({"user_id": user_id})

    if not user_data:
        users_collection.insert_one({
            "user_id": user_id,
            "streaks": {game_type: {"win_streak": 0, "lose_streak": 0}}
        })
        user_data = users_collection.find_one({"user_id": user_id})

    streak_data = user_data.get("streaks", {}).get(game_type, {"win_streak": 0, "lose_streak": 0})
    win_streak = streak_data.get("win_streak", 0)
    lose_streak = streak_data.get("lose_streak", 0)

    if is_win:
        win_streak += 1
        lose_streak = 0
    else:
        lose_streak += 1
        win_streak = 0

    users_collection.update_one(
        {"user_id": user_id},
        {"$set": {f"streaks.{game_type}.win_streak": win_streak, f"streaks.{game_type}.lose_streak": lose_streak}},
        upsert=True
    )

def get_user_streaks(user_id, game_type):
    """ゲームタイプごとのユーザーの連勝・連敗記録を取得"""
    user = users_collection.find_one({"user_id": user_id}, {"streaks": 1})  # `streaks` フィールドのみ取得
    
    if not user or "streaks" not in user:
        return 0, 0

    game_streaks = user.get("streaks", {}).get(game_type, {})

    return game_streaks.get("win_streak", 0), game_streaks.get("lose_streak", 0)

def update_bet_history(user_id, game_type, amount, is_win):
    """ユーザーのベット履歴をデータベースに記録"""

    bet_entry = {
        "amount": amount,
        "is_win": bool(is_win),  # ✅ `bool` に変換
        "timestamp": datetime.datetime.now()
    }

    bet_history_collection.update_one(
        {"user_id": user_id},
        {"$push": {f"bet_history.{game_type}.bets": bet_entry}},
        upsert=True
    )

def register_user(user_id, sender_external_id):
    users_collection.update_one(
        {"user_id": user_id},
        {"$set": {
            "sender_external_id": sender_external_id,
            "balance": 0
        }},
        upsert=True
    )

def get_user_transactions(user_id: int, game_type: str = None, days: int = None):
    """指定ユーザーの取引履歴を取得（オプションでゲーム種別や期間も絞れる）"""
    doc = user_transactions_collection.find_one({"user_id": user_id})

    if not doc or "transactions" not in doc:
        return []

    transactions = doc["transactions"]

    if game_type:
        transactions = [t for t in transactions if t.get("type") == game_type]

    if days:
        threshold = datetime.datetime.now() - timedelta(days=days)
        transactions = [t for t in transactions if t.get("timestamp") and t["timestamp"] >= threshold]

    return transactions

async def save_account_panel_message_id(message_id: int):
    bot_state_collection.update_one(
        {"_id": "account_panel"},
        {"$set": {"message_id": message_id}},
        upsert=True
    )

async def get_account_panel_message_id():
    doc = bot_state_collection.find_one({"_id": "account_panel"})
    return doc["message_id"] if doc and "message_id" in doc else None

def get_all_user_balances():
    """全ユーザーのuser_idと残高を取得する"""
    cursor = users_collection.find({}, {"user_id": 1, "balance": 1})
    return [(doc["user_id"], doc.get("balance", 0)) for doc in cursor]

def get_user_invite(user_id: int):
    return invites_collection.find_one({"user_id": user_id})

def save_user_invite(user_id: int, url: str):
    invites_collection.update_one(
        {"user_id": user_id},
        {"$set": {"invite_url": url}},
        upsert=True
    )

def log_invited_user(invited_id: int, inviter_id: int, invite_code: str):
    """初参加ユーザーの招待ログを保存する"""
    invited_users_collection.insert_one({
        "invited_id": invited_id,
        "inviter_id": inviter_id,
        "invite_code": invite_code,
        "timestamp": datetime.datetime.utcnow()
    })

def get_invited_users(inviter_id: int):
    return list(invited_users_collection.find({"inviter_id": inviter_id}).sort("timestamp", -1))

def get_unredeemed_users(inviter_id: int):
    invited = invited_users_collection.find({"inviter_id": inviter_id})
    redeemed_ids = set(x["invited_id"] for x in invite_redeem_collection.find({"inviter_id": inviter_id}))
    return [doc for doc in invited if doc["invited_id"] not in redeemed_ids]

def mark_users_as_redeemed(inviter_id: int, invited_ids: list):
    for invited_id in invited_ids:
        invite_redeem_collection.insert_one({
            "inviter_id": inviter_id,
            "invited_id": invited_id
        })
        
def has_already_been_invited(user_id: int) -> bool:
    """ユーザーが過去に一度でも招待されているかチェック"""
    return invited_users_collection.find_one({"invited_id": user_id}) is not None

def mark_user_as_invited(user_id: int):
    invited_users_collection.insert_one({"user_id": user_id})