import discord
import re
import io
from io import BytesIO
import secrets
import aiohttp

from database.db import get_user_balance, update_user_balance, load_pf_params, save_pf_params
from utils.embed import create_embed
from utils.emojis import PNC_EMOJI_STR
from utils.color import BLACKJACK_COLOR
from utils.embed_factory import EmbedFactory

from ui.game.blackjack import BlackjackGame, BlackjackView, blackjack_games

async def on_blackjack_command(message: discord.Message):
    try:
        pattern = r"\$bj\s+(\d+)"
        match = re.match(pattern, message.content)

        if not match:
            embed = create_embed("", "使い方: `$bj <掛け金>`", discord.Color.red())
            await message.channel.send(embed=embed)
            return

        bet = int(match.group(1))
        user = message.author
        user_id = user.id
        min_bet = 100

        if bet < min_bet:
            embed = EmbedFactory.bet_too_low(min_bet=min_bet)
            await message.channel.send(embed=embed)
            return

        balance = get_user_balance(user_id)
        if balance is None:
            embed = EmbedFactory.not_registered()
            await message.channel.send(embed=embed)
            return
        if balance < bet:
            embed = EmbedFactory.insufficient_balance(balance=balance)
            await message.channel.send(embed=embed)
            return
        
        update_user_balance(user_id, -bet)

        params = load_pf_params(user_id)
        if params and len(params) == 3:
            client_seed, server_seed, nonce = params
        else:
            client_seed = secrets.token_hex(8)
            server_seed = secrets.token_hex(32)
            nonce = 0

        game = BlackjackGame(bet=bet, client_seed=client_seed, nonce=nonce)
        game.deal_initial()
        blackjack_games[user_id] = game

        save_pf_params(user_id, client_seed, server_seed, nonce + 1)

        await message.channel.send(f"🔐 サーバーシードハッシュ: `{game.pf.server_seed_hash}`")

        async with message.channel.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get(user.display_avatar.url) as resp:
                    avatar_bytes = BytesIO(await resp.read())

            img = game.render_image(user_displayname=user.display_name, user_avatar_data=avatar_bytes)
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            buf.seek(0)
            file = discord.File(buf, filename="blackjack.png")

            embed = create_embed("PNCブラックジャック", f"{user.mention}", BLACKJACK_COLOR)
            embed.set_image(url="attachment://blackjack.png")
            embed.add_field(name="掛け金", value=f"{PNC_EMOJI_STR}`{bet:,}`", inline=False)
            embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
            embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1219916908485283880/1386317663231414272/ChatGPT_Image_2025622_21_11_08.png?ex=6859446f&is=6857f2ef&hm=19507da3f6ae2ea49377b1112e687a6690cd37bb229cc4ebcd5a1fef2c5965e6&")

            view = BlackjackView(user_id)
            await message.channel.send(embed=embed, view=view, file=file)

    except Exception as e:
        print(f"[ERROR] on_blackjack_command: {e}")
        embed = create_embed("エラー", "⚠ ゲーム開始中にエラーが発生しました。", discord.Color.red())
        await message.channel.send(embed=embed)