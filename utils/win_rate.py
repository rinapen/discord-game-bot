import numpy as np
from database.db import users_collection, bet_history_collection, casino_transactions_collection
from models.xgb_model import load_model_from_mongodb

def get_dynamic_win_rate(game_type, base_rate, user_id):
    """プレイヤーごとの勝率をデータベースから取得して動的に調整"""
    user_data = users_collection.find_one({"user_id": user_id})
    bet_data = bet_history_collection.find_one({"user_id": user_id})

    if not user_data or not bet_data:
        return 44.0  # データがない場合のデフォルト勝率

    total_bets = user_data.get("total_bets", 1)  # ゼロ除算防止
    total_wins = user_data.get("total_wins", 0)
    user_win_rate = (total_wins / total_bets) * 100

    bet_amounts = [bet["amount"] for bet in bet_data["bets"]]
    avg_bet = sum(bet_amounts) / len(bet_amounts)

    model = load_model_from_mongodb()
    if model:
        features = np.array([[user_win_rate, avg_bet, base_rate]])
        predicted_win_rate = model.predict(features)[0]
    else:
        predicted_win_rate = base_rate

    if user_data.get("current_streak", 0) > 3:
        predicted_win_rate -= 5
    elif user_data.get("current_streak", 0) < -3:
        predicted_win_rate += 5

    if avg_bet > 500:
        predicted_win_rate -= 3

    adjusted_win_rate = max(5, min(95, predicted_win_rate))
    print(f"[DEBUG] {user_id} の調整後勝率: {adjusted_win_rate:.2f}%")
    return adjusted_win_rate