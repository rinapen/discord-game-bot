"""
PNC（仮想通貨）関連ユーティリティ
PNCと日本円の変換、利益計算、ランキング機能を提供します
"""
import datetime
import random
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Final

import discord
from discord import Embed, ButtonStyle
from discord.ui import View, Button
import pytz

from database.db import users_collection, user_transactions_collection
from bot import bot

# ========================================
# 定数
# ========================================
JPY_PER_PNC: Final[Decimal] = Decimal("0.1")
JST: Final = pytz.timezone("Asia/Tokyo")
EXCLUDED_USER_IDS: Final[list[int]] = [1135891552045121557, 1154344959646908449, 1324832394079109301]


# ========================================
# 通貨変換関数
# ========================================
def jpy_to_pnc(jpy: Decimal) -> Decimal:
    """
    日本円をPNCに変換
    
    Args:
        jpy: 日本円の金額
    
    Returns:
        Decimal: PNC金額（整数に丸められる）
    """
    return (jpy / JPY_PER_PNC).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def pnc_to_jpy(pnc: Decimal) -> Decimal:
    """
    PNCを日本円に変換
    
    Args:
        pnc: PNC金額
    
    Returns:
        Decimal: 日本円金額（整数に丸められる）
    """
    return (pnc * JPY_PER_PNC).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def generate_random_amount() -> Decimal:
    """
    ランダムな金額を生成（1-90円）
    
    Returns:
        Decimal: ランダムな金額
    """
    return Decimal(random.randint(1, 90))

# ========================================
# 利益計算関数
# ========================================
def get_daily_profit(target_date: str) -> int:
    """
    指定した日のカジノの純利益（payin合計 - payout合計）を計算
    
    Args:
        target_date: 対象日付（YYYY-MM-DD形式）
    
    Returns:
        int: 純利益（円）
    
    Raises:
        ValueError: 日付形式が不正な場合
    """
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

def get_total_pnc() -> int:
    """
    指定ユーザーを除いた全ユーザーのPNC合計を取得
    
    Returns:
        int: 全ユーザーの合計PNC
    """
    total = list(users_collection.aggregate([
        {"$match": {"user_id": {"$nin": EXCLUDED_USER_IDS}}},
        {"$group": {"_id": None, "total_pnc": {"$sum": "$balance"}}}
    ]))

    return total[0]["total_pnc"] if total else 0


def get_total_revenue() -> int:
    """
    カジノ全体の累計純利益（全期間の payin 合計 - payout 合計）を計算
    
    Returns:
        int: 累計純利益（円）
    """
    total_profit = 0
    user_count = 0
    txn_count = 0

    users = user_transactions_collection.find({})
    for user in users:
        user_id = user.get("user_id", "不明")
        if user_id in EXCLUDED_USER_IDS:
            continue
            
        transactions = user.get("transactions", [])
        if not transactions:
            continue

        user_count += 1

        for txn in transactions:
            ttype = txn.get("type")
            amount = txn.get("amount", 0)

            # MongoDBの特殊な数値型を処理
            if isinstance(amount, dict):
                amount = int(amount.get("$numberInt", 0))
            elif not isinstance(amount, (int, float)):
                continue

            if ttype == "payin":
                txn_count += 1
                total_profit += amount
            elif ttype == "payout":
                total_profit -= amount

    print(f"\n📊 処理完了: {user_count}人、payin {txn_count}件")
    print(f"💰 カジノ全体の累計純利益: {total_profit:,}円")

    return total_profit

# ========================================
# ランキングUI
# ========================================
class PncRankPaginator(View):
    """PNCランキングのページネーションビュー"""
    
    def __init__(self, pages: list[Embed]):
        super().__init__(timeout=300)
        self.pages = pages
        self.current = 0

    @discord.ui.button(label="⬅️", style=ButtonStyle.secondary)
    async def back(self, interaction: discord.Interaction, button: Button):
        """前のページに戻る"""
        if self.current > 0:
            self.current -= 1
            await interaction.response.edit_message(embed=self.pages[self.current], view=self)

    @discord.ui.button(label="➡️", style=ButtonStyle.secondary)
    async def forward(self, interaction: discord.Interaction, button: Button):
        """次のページに進む"""
        if self.current < len(self.pages) - 1:
            self.current += 1
            await interaction.response.edit_message(embed=self.pages[self.current], view=self)


def create_pnc_rank_pages(user_data: list[tuple[int, int]], per_page: int = 10) -> list[Embed]:
    """
    ユーザーデータからランキングEmbedページを作成
    
    Args:
        user_data: (user_id, balance)のタプルリスト
        per_page: 1ページあたりの表示数
    
    Returns:
        list[Embed]: ページ化されたEmbedリスト
    """
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
                user = bot.get_user(user_id)
                if not user:
                    # キャッシュにない場合はAPIから取得（awaitはできないので後続処理で）
                    name = f"User({user_id})"
                else:
                    name = user.name
            except Exception as e:
                print(f"[WARN] fetch_user error for {user_id}: {e}")
                name = f"Unknown({user_id})"

            embed.add_field(name=f"#{rank} {name}", value=f"`{balance:,} PNC`", inline=False)

        pages.append(embed)

    return pages