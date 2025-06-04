import discord
from discord import app_commands
from database.db import users_collection, user_transactions_collection, get_user_balance
from bot import bot
from utils.embed import create_embed
import datetime

@bot.tree.command(name="zandaka", description="口座残高を表示")
async def zandaka(interaction: discord.Interaction):
    print("[LOG] /zandaka command called")

    user_id = interaction.user.id
    print(f"[LOG] User ID: {user_id}")

    user_info = users_collection.find_one({"user_id": user_id})
    if not user_info:
        print("[WARN] User not found in DB")
        embed = create_embed("", "あなたの口座は登録されていません。\n `/kouza` で口座を開設してください。", discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    balance = get_user_balance(user_id)
    print(f"[LOG] Current balance: {balance}")

    embed = discord.Embed(title="口座残高", description=f"# {balance:,} PNC", color=discord.Color.green())

    user_transactions = user_transactions_collection.find_one({"user_id": user_id})
    transactions = user_transactions.get("transactions", [])[-5:]
    print(f"[LOG] Fetched {len(transactions)} recent transactions")
    if transactions:
        print(f"[LOG] Fetched {len(transactions)} recent transactions")

        history_text = ""
        for txn in reversed(transactions):
            type_emoji = "📥" if txn["type"] == "in" else "📤" if txn["type"] == "out" else "🔄"

            if isinstance(txn["timestamp"], str):
                txn["timestamp"] = int(txn["timestamp"])

            if isinstance(txn["timestamp"], datetime.datetime):
                timestamp = txn["timestamp"].strftime('%Y-%m-%d %H:%M:%S')
            else:
                timestamp = datetime.datetime.fromtimestamp(txn["timestamp"] / 1000).strftime('%Y-%m-%d %H:%M:%S')

            line = f"{type_emoji} `{timestamp}` - `{txn['type'].capitalize()}`: `{txn['total']:,} PNC`\n"
            print(f"[TXN] {line.strip()}")
            history_text += line

        embed.add_field(name="**直近の取引履歴**", value=history_text, inline=False)
    else:
        print("[LOG] No transactions found")
        embed.add_field(name="**直近の取引履歴**", value="取引履歴がありません。", inline=False)

    embed.set_footer(text=f"{interaction.user.display_name}様 | ID: {interaction.user.name}")
    print("[LOG] Sending final embed to user")
    try:
        await interaction.response.send_message(embed=embed, ephemeral=True)
        print("[LOG] Embed sent successfully")
    except Exception as e:
        print(f"[ERROR] Failed to send embed: {e}")


