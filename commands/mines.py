import discord
import re
import secrets

from config import MIN_BET
from database.db import get_user_balance, update_user_balance, load_pf_params

from utils.embed import create_embed
from utils.color import BASE_COLOR_CODE
from utils.embed_factory import EmbedFactory

from ui.game.mines import MinesGame, MinesView, CashoutButton, create_mines_embed

MINE_OPTIONS = list[int](range(1, 25))

games = {}
async def on_mines_command(message: discord.Message):
    try:
        args = message.content.strip().split()
        if len(args) != 2 or (not args[1].isdigit() or not args[2].isdigit()):
            embed = create_embed("", "`?マインズ 金額 地雷数`の形式で入力してください。", discord.Color.red())
            await message.channel.send(embed=embed)
            return

        amount = int(args[1])
        mine_count = int(args.group[2])
        user = message.author
        user_id = user.id
        
        min_bet = MIN_BET["mines"]
        if amount < min_bet:
            embed = EmbedFactory.bet_too_low(min_bet=min_bet)
            await message.channel.send(embed=embed)
            return

        if mine_count not in MINE_OPTIONS:
            embed = create_embed("", "地雷数は 1〜24 の範囲で指定してください。", discord.Color.red())
            await message.channel.send(embed=embed)
            return

        balance = get_user_balance(user_id)
        if balance is None:
            embed = EmbedFactory.not_registered()
            await message.channel.send(embed=embed)
            return
        if balance < amount:
            embed = EmbedFactory.insufficient_balance(balance=balance)
            await message.channel.send(embed=embed)
            return

        update_user_balance(user_id, -amount)
        client_seed, nonce = load_pf_params(user_id)
        if client_seed is None:
            client_seed = secrets.token_hex(8)
            nonce = 0

        game = MinesGame(user, bet=amount, mine_count=mine_count,
                        client_seed=client_seed, nonce=nonce)
        games[user_id] = game
        await message.channel.send(f"[🔐] hash: `{game.server_seed_hash}`")
        
        game_embed = create_mines_embed(game)
        game_view = MinesView(user_id, game)
        game_message = await message.channel.send(embed=game_embed, view=game_view)
        game.message_id = game_message.id

        cashout_embed = create_embed("", "現在の報酬を引き出すにはボタンを押してください。", color=BASE_COLOR_CODE)
        cashout_view = discord.ui.View()
        cashout_view.add_item(CashoutButton(user_id, game, disabled=False))
        cashout_message = await message.channel.send(embed=cashout_embed, view=cashout_view)
        game.cashout_message_id = cashout_message.id
    except Exception as e:
        print(f"[ERROR] on_mines_command: {e}")
        import traceback
        traceback.print_exc()

        error_embed = create_embed("エラー", "ゲーム中にエラーが発生しました。", discord.Color.red())
        await message.channel.send(embed=error_embed)
