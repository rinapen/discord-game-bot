import discord
import random
from discord import app_commands
from bot import bot
from database.db import (
    get_user_balance,
    update_user_balance,
    update_user_streak,
    get_user_streaks
)
from utils.embed import create_embed
from utils.logs import send_casino_log
from utils.pnc import get_total_pnc
from utils.stats import log_transaction, get_user_net_profit
from config import WIN_EMOJI, LOSE_EMOJI
from paypay_session import paypay_session

VALID_BETS = {"red": "🔴", "black": "⚫", "green": "🟢"}
MIN_BET = 25
BASELINE = 9000  # 元々の運営元金（初期資金）

BET_PENALTY = {25: 0, 50: -1.0, 100: -2.0, 200: -3.5, 500: -5.5, 1000: -8.0}
BASE_WIN_RATE = {"red": 43, "black": 43, "green": 2.0}

def get_operator_balance():
    """PayPay残高を取得（失敗時は保守的な仮値）"""
    try:
        return int(paypay_session.paypay.get_balance().useable_balance)
    except Exception:
        return 5000  # 取得失敗時は中間の仮想残高

@bot.tree.command(name="roulette", description="ルーレットで賭ける")
@app_commands.describe(bet="ベットする色を選択", amount="賭ける金額を選択")
@app_commands.choices(
    bet=[
        app_commands.Choice(name="🔴 x2", value="red"),
        app_commands.Choice(name="⚫ x2", value="black"),
        app_commands.Choice(name="🟢 x14", value="green"),
    ],
    amount=[app_commands.Choice(name=f"{v} PNC", value=v) for v in BET_PENALTY]
)
async def roulette(interaction: discord.Interaction, bet: str, amount: int):
    user = interaction.user
    user_id = user.id
    balance = get_user_balance(user_id)

    if balance is None or balance < amount:
        return await interaction.response.send_message(
            embed=create_embed("❌ 残高不足", f"現在の残高: `{balance:,} PNC`", discord.Color.red()),
            ephemeral=True
        )

    win_streak, lose_streak = get_user_streaks(user_id, "roulette")
    win_rate = BASE_WIN_RATE[bet]

    if bet != "green":
        # 🧠 勝率補正：ベース + ベット補正 + ストリーク
        win_rate += BET_PENALTY[amount]
        win_rate -= win_streak * 5
        win_rate += lose_streak * 2

        # ✅ 損益ベースの勝率補正
        profit = get_user_net_profit(user_id, "roulette", days=7)
        if profit < -2000:
            win_rate += 5  # 救済
        elif profit > 3000:
            win_rate -= 5  # 回収

        # ✅ 運営のPayPay残高による全体勝率調整
        op_balance = get_operator_balance()
        op_ratio = op_balance / BASELINE

        if op_ratio < 0.3:
            win_rate -= 7
        elif op_ratio < 0.6:
            win_rate -= 4
        elif op_ratio < 1.0:
            win_rate -= 2
        elif op_ratio > 2.0:
            win_rate += 4
        elif op_ratio > 1.5:
            win_rate += 2

        # 📈 PNC経済全体による補正
        total_pnc = get_total_pnc()
        inflation_ratio = total_pnc / 300000  # 想定供給量

        if inflation_ratio > 1.5:
            win_rate -= 5
        elif inflation_ratio > 1.2:
            win_rate -= 3
        elif inflation_ratio < 0.8:
            win_rate += 3
        elif inflation_ratio < 0.5:
            win_rate += 5

        # 🎯 最終補正
        win_rate = max(0, min(win_rate, 100))

        print(f"{user_id}: {win_rate}")
    is_win = random.uniform(0, 100) <= win_rate
    update_user_balance(user_id, -amount)

    if is_win:
        payout = amount * (14 if bet == "green" else 2)
        update_user_balance(user_id, payout)
        update_user_streak(user_id, "roulette", True)
        log_transaction(user_id, "roulette", amount, payout)
        log_amount = payout - amount
        color = discord.Color.green()
        emoji = WIN_EMOJI
        result_text = f"✅ **勝利！** {VALID_BETS[bet]}"
    else:
        update_user_streak(user_id, "roulette", False)
        log_transaction(user_id, "roulette", amount, 0)
        log_amount = amount
        color = discord.Color.red()
        emoji = LOSE_EMOJI
        loss_emoji = random.choice([v for k, v in VALID_BETS.items() if k != bet])
        result_text = f"❌ **敗北...** {loss_emoji}"

    embed = create_embed("ルーレット結果", f"ルーレットの結果: {result_text}", color)
    embed.add_field(name="🎯 ベット", value=f"`{VALID_BETS[bet]}`", inline=True)
    embed.add_field(name="💸 ベット額", value=f"`{amount:,} PNC`", inline=True)

    if is_win:
        embed.add_field(name="💰 獲得", value=f"`+{log_amount:,} PNC`", inline=True)
    else:
        embed.add_field(name="📉 損失", value=f"`-{log_amount:,} PNC`", inline=True)

    embed.set_footer(text=f"現在の残高: {get_user_balance(user_id):,} PNC")

    await interaction.response.send_message(embed=embed)
    await send_casino_log(interaction, emoji, log_amount if is_win else -log_amount, "", color)