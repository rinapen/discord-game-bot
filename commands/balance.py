import discord

from database.db import get_user_balance, users_collection
from utils.embed_factory import EmbedFactory

async def on_balance_command(message: discord.Message) -> None:
    user_id = message.author.id

    try:
        user_info = users_collection.find_one({"user_id": user_id})
        if not user_info:
            embed = EmbedFactory.require_registration_prompt()
            await message.channel.send(embed=embed)
            return

        balance = get_user_balance(user_id)
        embed = EmbedFactory.balance_display(balance=balance)
        embed.set_author(name=f"{message.author.display_name} | {message.author.name}")
        embed.set_thumbnail(url=message.author.display_avatar.url)
        
        await message.channel.send(embed=embed)
        
    except Exception as e:
        print(f"[ERROR] on_balance_command: {e}")
        embed = EmbedFactory.error("内部エラーが発生しました。")
        await message.channel.send(embed=embed)