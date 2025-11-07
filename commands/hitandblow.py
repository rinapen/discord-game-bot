import discord
import re
import random
from database.db import get_user_balance
from utils.embed import create_embed
from utils.embed_factory import EmbedFactory
from utils.emojis import PNC_EMOJI_STR
from utils.color import BASE_COLOR_CODE
from config import HITANDBLOW_CATEGORY_ID
from ui.game.hitandblow import (
    DigitInputView,
    HitAndBlowAcceptButton,
    generate_board_image,
    download_avatar,
)

async def on_hitandblow_command(message: discord.Message):
    try:
        pattern = r"\?ヒットアンドブロー\s+<@!?(\d+)>\s+(\d+)"
        match = re.match(pattern, message.content)
        if not match:
            embed = create_embed("", "`?ヒットアンドブロー @ユーザー 掛け金` の形式で入力してください。", discord.Color.red())
            await message.channel.send(embed=embed)
            return

        challenger = message.author
        opponent_id = int(match.group(1))
        amount = int(match.group(2))

        if challenger.id == opponent_id:
            embed = create_embed("", "自分自身には対戦を申し込めません。", BASE_COLOR_CODE)
            await message.channel.send(embed=embed)
            return

        opponent = await message.guild.fetch_member(opponent_id)

        challenger_balance = get_user_balance(challenger.id)
        opponent_balance = get_user_balance(opponent.id)

        if challenger_balance is None or opponent_balance is None:
            embed = EmbedFactory.not_registered()
            await message.channel.send(embed=embed)
            return

        if challenger_balance < amount:
            embed = EmbedFactory.insufficient_balance(balance=challenger_balance)
            await message.channel.send(embed=embed)
            return

        if opponent_balance < amount:
            embed = create_embed("", f"{opponent.display_name} の残高が不足しています。", discord.Color.red())
            await message.channel.send(embed=embed)
            return

        # 承諾ボタン表示
        view = HitAndBlowAcceptButton(challenger, opponent, amount)
        embed = create_embed(
            title="ヒットアンドブローの申し込み",
            description=f"{challenger.mention} があなたに {PNC_EMOJI_STR}`{amount}` でヒットアンドブローを申し込んでいます。\n\n承諾するには下のボタンを押してください（制限時間：60秒）",
            color=BASE_COLOR_CODE
        )
        await message.channel.send(content=opponent.mention, embed=embed, view=view)
        await view.wait()

        if not view.accepted:
            await message.channel.send("⏳ 時間切れ。対戦はキャンセルされました。")
            return

        category = message.guild.get_channel(HITANDBLOW_CATEGORY_ID)

        players = {
            challenger.id: {"member": challenger},
            opponent.id: {"member": opponent}
        }

        # チャンネルと数字入力準備
        for pid, pdata in players.items():
            player = pdata["member"]
            overwrites = {
                message.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                player: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
                message.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
            }

            channel_name = f"{player.display_name}様のお部屋"
            channel = await message.guild.create_text_channel(name=channel_name, overwrites=overwrites, category=category)
            pdata["channel"] = channel

            await channel.send(f"{player.mention} ようこそ、あなた専用のお部屋へ！")
            view = DigitInputView(user=player)
            embed = discord.Embed(
                title="数字を入力してください",
                description="0〜9から **3桁の重複しない数字** を選んでください。",
                color=BASE_COLOR_CODE
            )
            view.message = await channel.send(embed=embed, view=view)
            pdata["view"] = view

        # 入力完了まで待つ
        for pid, pdata in players.items():
            await pdata["view"].wait()
            pdata["digits"] = pdata["view"].digits

        # 先攻後攻をランダムに決定
        first_player_id = random.choice(list(players.keys()))
        second_player_id = [pid for pid in players if pid != first_player_id][0]
        players[first_player_id]["turn"] = True
        players[second_player_id]["turn"] = False

        # 数字確認用画像送信
        for pid, pdata in players.items():
            digits = pdata["digits"]
            channel = pdata["channel"]
            member = pdata["member"]

            opponent_id = [other_pid for other_pid in players if other_pid != pid][0]
            opponent = players[opponent_id]["member"]

            user_icon_path = await download_avatar(member.display_avatar.url, member.id)
            opponent_icon_path = await download_avatar(opponent.display_avatar.url, opponent.id)

            image_path = generate_board_image(
                digits=digits,
                user_id=member.id,
                user_icon_path=user_icon_path,
                user_name=member.display_name,
                opponent_icon_path=opponent_icon_path,
                opponent_name=opponent.display_name
            )

            file = discord.File(image_path, filename="board.png")
            embed = discord.Embed(
                title="🎮 ゲーム開始！",
                description="あなたが選んだ数字がこちらです。\n" +
                            ("🟥 あなたが先攻です！" if players[pid]["turn"] else "🟦 あなたは後攻です。相手のターンを待ちましょう。"),
                color=BASE_COLOR_CODE
            )
            embed.set_image(url="attachment://board.png")
            await channel.send(embed=embed, file=file)

    except Exception as e:
        print(f"[ERROR] on_hitandblow_command: {e}")
        import traceback
        traceback.print_exc()
        embed = create_embed("エラー", "⚠ 処理中にエラーが発生しました。", discord.Color.red())
        await message.channel.send(embed=embed)