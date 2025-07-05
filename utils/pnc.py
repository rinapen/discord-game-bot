import datetime
from database.db import users_collection, user_transactions_collection
from datetime import timedelta
import pytz
from discord.ui import View, Button
from discord import Embed, ButtonStyle
import discord
from bot import bot
import random
from decimal import Decimal, ROUND_HALF_UP

JPY_PER_PNC = Decimal("0.1")

JST = pytz.timezone("Asia/Tokyo")

def jpy_to_pnc(jpy: Decimal) -> Decimal:
    return (jpy / JPY_PER_PNC).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

def pnc_to_jpy(pnc: Decimal) -> Decimal:
    return (pnc * JPY_PER_PNC).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

def generate_random_amount():
    return Decimal(random.randint(1, 90))

def get_daily_profit(target_date: str):
    """指定した日のカジノの純利益（payin合計 - payout合計）を計算"""

    try:
        target_datetime = datetime.datetime.strptime(target_date, "%Y-%m-%d").replace(tzinfo=JST)
    except ValueError:
        raise ValueError("日付の形式が正しくありません！`YYYY-MM-DD` の形式で指定してください。")

    start_time = target_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
    end_time = target_datetime.replace(hour=23, minute=59, second=59, microsecond=999)

    total_profit = 0

    users = user_transactions_collection.find({})
    for user in users:
        for txn in user.get("transactions", []):
            ts = txn.get("timestamp")
            if not ts:
                continue

            # ISODate → datetime変換
            if isinstance(ts, str):
                ts = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
            elif isinstance(ts, dict) and "$date" in ts:
                ts = datetime.datetime.fromtimestamp(int(ts["$date"]["$numberLong"]) / 1000, tz=JST)
            elif isinstance(ts, datetime.datetime):
                ts = ts.astimezone(JST)

            if not (start_time <= ts <= end_time):
                continue

            ttype = txn.get("type")
            amount = txn.get("amount", 0)
            if isinstance(amount, dict):
                amount = int(amount.get("$numberInt", 0))
            elif not isinstance(amount, (int, float)):
                amount = 0

            if ttype == "payin":
                total_profit += amount  # ユーザーが賭けた → カジノの利益
            elif ttype == "payout":
                total_profit -= amount  # ユーザーが受け取った → カジノの損

    return total_profit

def get_total_pnc():
    """指定ユーザーを除いた全ユーザーのPNC合計を取得"""
    excluded_ids = [1135891552045121557, 1154344959646908449, 1324832394079109301]

    total = list(users_collection.aggregate([
        {"$match": {"user_id": {"$nin": excluded_ids}}},
        {"$group": {"_id": None, "total_pnc": {"$sum": "$balance"}}}
    ]))

    return total[0]["total_pnc"] if total else 0

def get_total_revenue():
    """カジノ全体の累計純利益（全期間の payin 合計 - payout 合計）を返す（payinのみ表示）"""
    total_profit = 0
    user_count = 0
    txn_count = 0

    users = user_transactions_collection.find({})
    for user in users:
        user_id = user.get("user_id", "不明")
        if user_id == 1154344959646908449:
            continue
        transactions = user.get("transactions", [])  # ✅ フィールド名確認済み

        if not transactions:
            continue

        user_count += 1

        for txn in transactions:
            ttype = txn.get("type")
            amount = txn.get("amount", 0)
            timestamp = txn.get("timestamp")

            if isinstance(amount, dict):
                amount = int(amount.get("$numberInt", 0))
            elif not isinstance(amount, (int, float)):
                continue

            if ttype == "payin":
                txn_count += 1
                total_profit += amount
 
            elif ttype == "payout":
                total_profit -= amount  # 出力しな

    print(f"\n📊 処理完了: {user_count}人、payin {txn_count}件")
    print(f"💰 カジノ全体の累計純利益: {total_profit:,}円")

    return total_profit

class PncRankPaginator(View):
    def __init__(self, pages):
        super().__init__(timeout=300)
        self.pages = pages
        self.current = 0

    @discord.ui.button(label="⬅️", style=ButtonStyle.secondary)
    async def back(self, interaction: discord.Interaction, button: Button):
        if self.current > 0:
            self.current -= 1
            await interaction.response.edit_message(embed=self.pages[self.current], view=self)

    @discord.ui.button(label="➡️", style=ButtonStyle.secondary)
    async def forward(self, interaction: discord.Interaction, button: Button):
        if self.current < len(self.pages) - 1:
            self.current += 1
            await interaction.response.edit_message(embed=self.pages[self.current], view=self)

def create_pnc_rank_pages(user_data, per_page=10):
    """ユーザーデータからEmbedページを作成"""
    pages = []
    total_pages = (len(user_data) + per_page - 1) // per_page

    for i in range(total_pages):
        start = i * per_page
        end = start + per_page
        embed = Embed(
            title="💰 PNC保有ランキング",
            description=f"全ユーザーの残高一覧（{i+1}/{total_pages}）",
            color=discord.Color.gold()
        )

        for rank, (user_id, balance) in enumerate(user_data[start:end], start=start + 1):
            try:
                user = bot.get_user(user_id) or bot.fetch_user(user_id)
                name = user.name
            except Exception as e:
                print(f"[!] fetch_user error: {e}")
                name = f"Unknown({user_id})"

            embed.add_field(name=f"#{rank} {name}", value=f"`{balance:,} PNC`", inline=False)

        pages.append(embed)

    return pages