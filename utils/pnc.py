import datetime
from database.db import users_collection, user_transactions_collection
from datetime import timedelta
import pytz

JST = pytz.timezone("Asia/Tokyo")

def get_daily_profit(target_date: str):
    """指定した日のカジノの利益（入金額 + 手数料 - 出金額）を計算"""

    # **`target_date` を `datetime` に変換**
    try:
        target_datetime = datetime.datetime.strptime(target_date, "%Y-%m-%d").replace(tzinfo=JST)
    except ValueError:
        raise ValueError("日付の形式が正しくありません！`YYYY-MM-DD` の形式で指定してください。")

    # **指定した日の 00:00:00 〜 23:59:59 を計算**
    start_time = target_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
    end_time = target_datetime.replace(hour=23, minute=59, second=59, microsecond=999)

    # **ミリ秒単位で範囲を取得**
    start_timestamp = int(start_time.timestamp() * 1000)
    end_timestamp = int(end_time.timestamp() * 1000)

    # **利益計算のための変数**
    total_income = 0  # ✅ **入金額の合計**
    total_fees = 0    # ✅ **手数料の合計**
    total_expense = 0 # ✅ **出金額の合計**

    # **全ユーザーの取引データを取得**
    users = user_transactions_collection.find({})

    for user in users:
        transactions = user.get("transactions", [])
        for txn in transactions:
            txn_time = txn.get("timestamp")

            # **MongoDBのtimestamp型を統一**
            if isinstance(txn_time, dict):  # `{ "$date": { "$numberLong": "数値" } }` の場合
                txn_time = int(txn_time["$date"]["$numberLong"])
            elif isinstance(txn_time, datetime.datetime):
                txn_time = int(txn_time.timestamp() * 1000)  # `datetime` 型ならミリ秒に変換

            # **指定した日付の範囲内の取引を集計**
            if start_timestamp <= txn_time <= end_timestamp:
                if txn["type"] == "in":
                    # ✅ **入金額 (total) + 手数料 (fee) を加算**
                    total_income += int(txn["total"]) if isinstance(txn["total"], int) else int(txn["total"]["$numberInt"])
                    total_fees += int(txn["fee"]) if isinstance(txn["fee"], int) else int(txn["fee"]["$numberInt"])
                elif txn["type"] == "out":
                    total_expense += int(txn["amount"]) if isinstance(txn["amount"], int) else int(txn["amount"]["$numberInt"])

    # **最終利益 = 入金額 + 手数料 - 出金額**
    daily_profit = total_income + total_fees - total_expense

    return daily_profit

def get_total_pnc():
    """指定ユーザーを除いた全ユーザーのPNC合計を取得"""
    excluded_ids = [1135891552045121557, 1154344959646908449]

    total = list(users_collection.aggregate([
        {"$match": {"user_id": {"$nin": excluded_ids}}},
        {"$group": {"_id": None, "total_pnc": {"$sum": "$balance"}}}
    ]))

    return total[0]["total_pnc"] if total else 0

def get_monthly_revenue():
    """過去30日間の総売上（`income` タイプの合計）を取得"""
    today = datetime.datetime.now()
    start_date = (today - datetime.timedelta(days=30)).strftime("%Y-%m-%d")

    transactions = user_transactions_collection.find({"timestamp": {"$gte": start_date}})
    total_income = sum(txn["amount"] for txn in transactions if txn["type"] == "income")

    return total_income