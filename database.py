import pymongo
import datetime
from config import MONGO_URI, DB_NAME, TOKENS_COLLECTION, USERS_COLLECTION, USER_TRANSACTIONS_COLLECTION, SETTINGS_COLLECTION, CASINO_STATS_COLLECTION, MODELS_COLLECTION, CASINO_TRANSACTION_COLLECTION

client = pymongo.MongoClient(MONGO_URI)
db = client[DB_NAME]
tokens_collection = db[TOKENS_COLLECTION]
users_collection = db[USERS_COLLECTION]
settings_collection = db[SETTINGS_COLLECTION]
casino_stats_collection = db[CASINO_STATS_COLLECTION]
models_collection = db[MODELS_COLLECTION]

user_transactions_collection = db[USER_TRANSACTIONS_COLLECTION]
casino_transactions_collection = db[CASINO_TRANSACTION_COLLECTION]

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
    users_collection.update_one(
        {"user_id": user_id},
        {"$inc": {"balance": int(amount)}},
        upsert=True
    )

def register_user(user_id, username, sender_external_id):
    users_collection.update_one(
        {"user_id": user_id},
        {"$set": {
            "username": username,
            "sender_external_id": sender_external_id,
            "balance": 0
        }},
        upsert=True
    )

def log_transaction(user_id, type, amount, fee, total, receiver=None):
    """ ユーザーの取引履歴を `transactions` にリスト形式で記録 (JST対応) """

    now = datetime.datetime.now()
    transaction = {
        "type": type,  # "in", "out", "send"
        "amount": amount,
        "fee": fee,
        "total": total,
        "receiver": receiver,
        "timestamp": now  # **JST（日本標準時）**
    }

    user_transactions_collection.update_one(
        {"user_id": user_id},
        {"$push": {"transactions": transaction}}, 
        upsert=True
    )