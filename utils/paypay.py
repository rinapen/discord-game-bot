from datetime import datetime, timedelta
import pytz
from database.db import casino_stats_collection 
from paypay_session import paypay_session

JST = pytz.timezone("Asia/Tokyo")

def get_today_date():
    return datetime.now(JST).strftime("%Y-%m-%d")

def get_yesterday_date():
    return (datetime.now(JST) - timedelta(days=1)).strftime("%Y-%m-%d")

def get_paypay_winrate():
    now = datetime.now()
    hour_key = now.strftime("%Y-%m-%d_%H")  # e.g. "2025-06-04_15"

    balance_info = paypay_session.paypay.get_balance()
    current_balance = balance_info.all_balance

    record = casino_stats_collection.find_one({"_id": f"paypay_balance_{hour_key}"})

    if not record:
        casino_stats_collection.update_one(
            {"_id": f"paypay_balance_{hour_key}"},
            {"$set": {"balance": current_balance, "timestamp": now}},
            upsert=True
        )
        return 0.3  # 初回は低リスクで

    past_balance = record["balance"]

    # 残高差分をチェック
    diff = current_balance - past_balance

    # 最新の値に更新して次回比較用にする
    casino_stats_collection.update_one(
        {"_id": f"paypay_balance_{hour_key}"},
        {"$set": {"balance": current_balance, "timestamp": now}},
        upsert=True
    )

    if diff > 15000:
        return 0.5
    elif diff > 10000:
        return 0.45
    elif diff > 5000:
        return 0.4
    elif diff > 2000:
        return 0.35
    else:
        return 0.3
