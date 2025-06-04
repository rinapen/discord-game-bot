import discord
import random
from discord import app_commands
from bot import bot
from database.db import get_user_balance, update_user_balance, update_user_streak, get_user_streaks, update_bet_history
from utils.logs import send_casino_log
from config import WIN_EMOJI, LOSE_EMOJI
from utils.paypay import get_paypay_winrate

@bot.tree.command(name="lottery", description="ただかけるだけさ")
@app_commands.describe(amount="ベット額を入力（例: 100, 500, 1000）")
@app_commands.choices(amount=[
    app_commands.Choice(name="100 PNC", value=100),
    app_commands.Choice(name="500 PNC", value=500),
    app_commands.Choice(name="1000 PNC", value=1000)
])
async def lottery(interaction: discord.Interaction, amount: int):
    user_id = interaction.user.id
    balance = get_user_balance(user_id)

    if balance is None or balance < amount:
        embed = discord.Embed(title="❌ エラー", description="残高が不足しています。", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    try:
        winrate = get_paypay_winrate()
        print(winrate)
    except Exception as e:
        print(f"[ERROR] PayPay取得失敗: {e}")
        winrate = 0.3

    is_win = random.random() <= winrate
    update_user_balance(user_id, -amount)

    if is_win:
        winnings = amount * 2
        update_user_balance(user_id, winnings)
        update_user_streak(user_id, "lottery", True)
        result_text = f"`{winnings} PNC`"
        color = discord.Color.green()
        emoji = WIN_EMOJI
    else:
        winnings = 0
        update_user_streak(user_id, "lottery", False)
        result_text = f"`{amount} PNC`"
        color = discord.Color.red()
        emoji = LOSE_EMOJI

    update_bet_history(user_id, "lottery", amount, is_win)
    await send_casino_log(interaction, emoji, amount, "", color, "Lottery")

    new_balance = get_user_balance(user_id)
    embed = discord.Embed(title="結果", description=result_text, color=color)
    embed.add_field(name="**ベット額**", value=f"`{amount} PNC`", inline=False)
    embed.set_footer(text=f"現在の残高: {new_balance} PNC")

    await interaction.response.send_message(embed=embed)