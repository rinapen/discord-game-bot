import datetime
import os
from typing import Optional

import discord

from bot import bot
import config
from database.db import financial_transactions_collection

async def send_casino_log(
    interaction: discord.Interaction,
    winorlose: str,
    emoji: str,
    price: int,
    description: str,
    color: discord.Color,
) -> None:
    price = abs(price)

    desc = f"### {emoji} **{winorlose}** ＋ {price:,}"
    if description:
        desc += f"\n{description}"

    embed = discord.Embed(description=desc, color=color)
    embed.set_author(
        name=f"{interaction.user.name}",
        icon_url=interaction.user.display_avatar.url
    )

    try:
        if not config.CASINO_LOG_CHANNEL_ID:
            print("[WARN] CASINO_LOG_CHANNEL_ID is not set")
            return
            
        casino_channel = bot.get_channel(int(config.CASINO_LOG_CHANNEL_ID))
        if casino_channel:
            await casino_channel.send(embed=embed)
        else:
            print(f"[ERROR] Casino log channel not found: {config.CASINO_LOG_CHANNEL_ID}")
    except Exception as e:
        print(f"[ERROR] Failed to send casino log: {e}")

def log_financial_transaction(
    user_id: int,
    transaction_type: str,
    amount: int,
    net_amount: int = None
) -> None:
    if transaction_type not in ["payin", "payout", "exchange"]:
        print(f"[WARN] log_financial_transaction: 無効なトランザクションタイプ '{transaction_type}' はスキップされました")
        return
    
    if net_amount is None:
        net_amount = amount
    
    transaction = {
        "type": transaction_type,
        "amount": amount,
        "net_amount": net_amount,
        "timestamp": datetime.datetime.now()
    }

    financial_transactions_collection.update_one(
        {"user_id": user_id},
        {"$push": {"transactions": transaction}},
        upsert=True
    )


def log_transaction(user_id: int, type: str, amount: int, payout: int) -> None:
     if type in ["payin", "payout"]:
        log_financial_transaction(user_id, type, amount, payout)