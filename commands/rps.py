import discord
import random
import re
import hmac
import hashlib
import secrets
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from utils.embed import create_embed
from utils.emojis import PNC_EMOJI_STR, WIN_EMOJI, ROCK_HAND_EMOJI, SCISSOR_HAND_EMOJI, PAPER_HAND_EMOJI
from utils.logs import send_casino_log
from utils.color import RPS_COLOR, SUCCESS_COLOR, DRAW_COLOR
from database.db import get_user_balance, update_user_balance, load_pf_params
from config import CURRENCY_NAME, MIN_BET
import aiohttp
import traceback

FONT_PATH = "assets/font/NotoSansJP-VariableFont_wght.ttf"
SLOT_CARD_BACK = "assets/rps/slot_back.png"

class ProvablyFairParams:
    def __init__(self, client_seed=None, server_seed=None, nonce=0):
        self.client_seed = client_seed or secrets.token_hex(8)
        self.server_seed = server_seed or secrets.token_hex(32)
        self.server_seed_hash = hashlib.sha256(self.server_seed.encode()).hexdigest()
        self.nonce = nonce

    def generate_number(self):
        msg = f"{self.client_seed}:{self.nonce}".encode()
        h = hmac.new(self.server_seed.encode(), msg, hashlib.sha256).hexdigest()
        r = int(h[:8], 16)
        return r / 0xFFFFFFFF

    def get_opponent_hand(self):  
        num = self.generate_number()
        hands = ["rock", "paper", "scissors"]
        return hands[int(num * 3)]

    def get_pf_info(self):
        return f"ServerSeed: `{self.server_seed}`\nClientSeed: `{self.client_seed}`\nNonce: `{self.nonce}`"

class RPSGameSession:
    def __init__(self, user_id, bet_amount, client_seed=None, server_seed=None, nonce=0):
        self.user_id = user_id
        self.bet_amount = bet_amount
        self.base_multiplier = 1.96
        self.round = 0
        self.pf = ProvablyFairParams(client_seed, server_seed, nonce)
        self.history = []

    def next_round(self):
        self.round += 1
        self.pf.nonce += 1

    def get_multiplier(self, round_index):
        return self.base_multiplier * (2 ** round_index)

    def calc_win_amount(self):
        win_count = sum(1 for entry in self.history if entry["result"] == "win")
        if win_count == 0:
            return self.bet_amount
        multiplier = self.base_multiplier * (2 ** (win_count - 1))
        return int(self.bet_amount * multiplier)

game_sessions = {}

def determine_result(player, opponent):
    if player == opponent:
        return "draw"
    elif (player == "rock" and opponent == "scissors") or \
         (player == "scissors" and opponent == "paper") or \
         (player == "paper" and opponent == "rock"):
        return "win"
    else:
        return "lose"

def resize_by_width(image: Image.Image, target_width: int) -> Image.Image:
    w, h = image.size
    aspect_ratio = h / w
    new_height = int(target_width * aspect_ratio)
    return image.resize((target_width, new_height))

def resize_keep_aspect(image: Image.Image, target_width: int) -> Image.Image:
    w, h = image.size
    scale = target_width / w
    return image.resize((int(w * scale), int(h * scale)))


async def generate_rps_progress_image(session, user_avatar, username):
    width = 1280
    height = 500
    bg = Image.new("RGBA", (width, height), (20, 20, 30, 255))
    draw = ImageDraw.Draw(bg)
    font = ImageFont.truetype(FONT_PATH, 20)

    # カードと手のサイズ
    focus_card_w = 120
    focus_card_h = int(focus_card_w * 1.45)

    # 手の最大幅
    hand_target_width = int(focus_card_w * 0.89)
    
    # 中央のカード位置（右寄せ）
    card_x = width - focus_card_w - 100
    center_y = height // 2
    opponent_card_y = center_y - focus_card_h - 20
    player_card_y = center_y + 20

    card_back = resize_by_width(Image.open(SLOT_CARD_BACK), focus_card_w)

    if session.history:
        latest = session.history[-1]
        player_hand = latest["player"]
        opponent_hand = latest["opponent"]

        bg.paste(card_back, (card_x, opponent_card_y), card_back)
        bg.paste(card_back, (card_x, player_card_y), card_back)

        player_img = resize_keep_aspect(Image.open(f"assets/rps/{player_hand}.1.png").convert("RGBA"), hand_target_width)
        opponent_img = resize_keep_aspect(Image.open(f"assets/rps/{opponent_hand}.2.png").convert("RGBA"), hand_target_width)

        opponent_hand_x = card_x - opponent_img.width - 10
        player_hand_x = card_x - player_img.width - 10

        # 正しいX座標を後から設定
        opponent_hand_x = card_x - opponent_img.width - 10
        player_hand_x = card_x - player_img.width - 10

        # Y座標（中央合わせ）
        oy = opponent_card_y + (focus_card_h - opponent_img.height) // 2 + 5
        py = player_card_y + (focus_card_h - player_img.height) // 2 + 5

        # 手を描画
        bg.paste(opponent_img, (opponent_hand_x, oy), opponent_img)
        bg.paste(player_img, (player_hand_x, py), player_img)


    # 左下の履歴表示
    card_w = 40
    spacing = 50
    offset_x = 30
    bot_y = 50
    player_y = bot_y + 60
    multiplier_y = player_y + card_w + 5
    win_count = 0

    for i, entry in enumerate(session.history):
        x = offset_x + i * spacing
        result = entry["result"]
        player_hand = entry["player"]
        opponent_hand = entry["opponent"]

        p_img = Image.open(f"assets/rps/{player_hand}.1.thumb.png").resize((card_w, card_w))
        o_img = Image.open(f"assets/rps/{opponent_hand}.2.thumb.png").resize((card_w, card_w))


        border_color = {"win": (0, 255, 0), "draw": (255, 255, 0), "lose": (255, 0, 0)}[result]

        draw.rectangle([x - 2, player_y - 2, x + card_w + 2, player_y + card_w + 2], outline=border_color, width=2)
        draw.rectangle([x - 2, bot_y - 2, x + card_w + 2, bot_y + card_w + 2], outline=border_color, width=2)

        bg.paste(p_img, (x, player_y), p_img)
        bg.paste(o_img, (x, bot_y), o_img)

        # 倍率計算
        if result == "win":
            win_count += 1
            multiplier = 1.96 * (2 ** (win_count - 1))
        elif result == "draw":
            multiplier = 1.00 if win_count == 0 else 1.96 * (2 ** (win_count - 1))
        else:
            multiplier = 0

        color = border_color
        multiplier_str = f"{multiplier:.2f}x"
        text_width = draw.textlength(multiplier_str, font=font)
        draw.text((x + (card_w - text_width) / 2, multiplier_y), multiplier_str, font=font, fill=color)

    # プレイヤー情報
    avatar = Image.open(user_avatar).resize((60, 60)).convert("RGBA")
    mask = Image.new("L", (60, 60), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 60, 60), fill=255)
    avatar = Image.composite(avatar, Image.new("RGBA", avatar.size), mask)
    bg.paste(avatar, (20, height - 70), avatar)
    draw.text((90, height - 60), username, font=font, fill=(255, 255, 255))

    return bg

async def on_rps_command(message: discord.Message):
    try: 
        args = message.content.strip().split()
        if len(args) != 2 or not args[1].isdigit():
            embed = create_embed("コマンドの使い方", "`?じゃんけん <掛け金>`の形式で入力してください。", discord.Color.red())
            await message.channel.send(embed=embed)
            return

        amount = int(args[1])
        uid = message.author.id
        balance = get_user_balance(uid)
        min_bet = MIN_BET["rps"]
        if amount < min_bet:
            embed = create_embed("", f"掛け金は最低{PNC_EMOJI_STR}`100`以上にしてください。", discord.Color.red())
            await message.channel.send(embed=embed)
            return

        if amount > balance:
            embed = create_embed("", f"残高が足りません。\n現在の残高: {PNC_EMOJI_STR}`{balance}`", discord.Color.red())
            await message.channel.send(embed=embed)
            return

        pf_data = load_pf_params(uid)
        if pf_data and len(pf_data) == 3:
            client_seed, server_seed, nonce = pf_data
        else:
            client_seed = None
            server_seed = None
            nonce = 0
        session = RPSGameSession(uid, amount, client_seed, server_seed, nonce)
        game_sessions[uid] = session

        update_user_balance(uid, -amount)
        await message.channel.send(f"[🔐] hash: `{session.pf.server_seed_hash}`")

        async with aiohttp.ClientSession() as session_http:
            async with session_http.get(message.author.display_avatar.url) as resp:
                avatar_bytes = BytesIO(await resp.read())

        image = await generate_rps_progress_image(session, avatar_bytes, message.author.display_name)
        buf = BytesIO()
        image.save(buf, format="PNG")
        buf.seek(0)
        file = discord.File(buf, filename="rps_result.png")

        embed = create_embed(f"{CURRENCY_NAME}じゃんけん", "じゃんけんぽん！", discord.Color(RPS_COLOR))
        embed.set_image(url="attachment://rps_result.png")
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1219916908485283880/1387141204604620918/ChatGPT_Image_2025625_03_43_31.png")
        embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)

        await message.channel.send(embed=embed, view=RPSPlayView(session), file=file)

    except Exception as e:
        traceback.print_exc() 
        await message.channel.send(f"内部エラーが発生しました: `{type(e).__name__}: {str(e)}`")


class RPSResultView(discord.ui.View):
    def __init__(self, session, player_choice, opponent_choice, result):
        super().__init__(timeout=60)
        self.session = session

    @discord.ui.button(label="継続", style=discord.ButtonStyle.success)
    async def continue_button(self, interaction, button):
        self.session.next_round(True)
        await send_rps_prompt(interaction, self.session)

    @discord.ui.button(label="キャッシュアウト", style=discord.ButtonStyle.secondary)
    async def cashout_button(self, interaction, button):
        amount = self.session.calc_win_amount()
        if self.session.round == 0:
            amount = self.session.bet_amount 
        profit = amount - self.session.bet_amount  

        update_user_balance(self.session.user_id, amount)
        embed = create_embed(
            "キャッシュアウト成功！",
            f"{PNC_EMOJI_STR}`{amount}` **WIN**\n＋{PNC_EMOJI_STR}`{profit}`",
            color=discord.Color(SUCCESS_COLOR)
        )
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1219916908485283880/1387141204604620918/ChatGPT_Image_2025625_03_43_31.png")
       
        await interaction.response.send_message(embed=embed)
        if profit > 0:
            await send_casino_log(  
                interaction,
                "WIN",
                WIN_EMOJI,
                profit,
                "",
                color=discord.Color(SUCCESS_COLOR)
            )
        game_sessions.pop(self.session.user_id, None)


async def send_rps_prompt(interaction, session):
    view = RPSPlayView(session)
    await interaction.edit_original_response(view=view)

class RPSPlayView(discord.ui.View):
    def __init__(self, session):
        super().__init__(timeout=None) 
        self.session = session

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.session.user_id:
            await interaction.response.send_message("これはあなたのゲームではありません。", ephemeral=True)
            return False
        return True

    @discord.ui.button(emoji=ROCK_HAND_EMOJI, style=discord.ButtonStyle.success)
    async def rock(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.resolve(interaction, "rock")

    @discord.ui.button(emoji=SCISSOR_HAND_EMOJI, style=discord.ButtonStyle.success)
    async def scissors(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.resolve(interaction, "scissors")

    @discord.ui.button(emoji=PAPER_HAND_EMOJI, style=discord.ButtonStyle.success)
    async def paper(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.resolve(interaction, "paper")


    @discord.ui.button(label="キャッシュアウト", style=discord.ButtonStyle.secondary, row=1)
    async def cashout(self, interaction: discord.Interaction, button: discord.ui.Button):
        amount = self.session.calc_win_amount()
        profit = amount - self.session.bet_amount
        if self.session.round == 0:
            amount = self.session.bet_amount
            profit = 0

        update_user_balance(self.session.user_id, amount)

        async with aiohttp.ClientSession() as session_http:
            async with session_http.get(interaction.user.display_avatar.url) as resp:
                avatar_bytes = BytesIO(await resp.read())

        image = await generate_rps_progress_image(self.session, avatar_bytes, interaction.user.display_name)
        buf = BytesIO()
        image.save(buf, format="PNG")
        buf.seek(0)
        file = discord.File(buf, filename="rps_result.png")

        embed = create_embed(
            "キャッシュアウト成功！",
            f"{PNC_EMOJI_STR}`{amount}` **WIN**\n＋{PNC_EMOJI_STR}`{profit}`",
            color=discord.Color(SUCCESS_COLOR)
        )
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1219916908485283880/1387141204604620918/ChatGPT_Image_2025625_03_43_31.png")
        embed.set_image(url="attachment://rps_result.png")

        disabled_view = RPSPlayView(self.session)
        for item in disabled_view.children:
            item.disabled = True

        await interaction.response.edit_message(embed=embed, attachments=[file], view=disabled_view)
        if profit > 0:
            await send_casino_log(
                interaction,
                "WIN",
                WIN_EMOJI,
                profit,
                "",
                color=discord.Color(SUCCESS_COLOR)
            )

        game_sessions.pop(self.session.user_id, None)
        self.stop()

    async def resolve(self, interaction, player_choice):
        try:
            session = self.session
            pf = session.pf
            opponent_choice = pf.get_opponent_hand()
            result = determine_result(player_choice, opponent_choice)

            session.history.append({
                "player": player_choice,
                "opponent": opponent_choice,
                "result": result
            })

            async with aiohttp.ClientSession() as session_http:
                async with session_http.get(interaction.user.display_avatar.url) as resp:
                    avatar_bytes = BytesIO(await resp.read())

            image = await generate_rps_progress_image(session, avatar_bytes, interaction.user.display_name)
            buf = BytesIO()
            image.save(buf, format="PNG")
            buf.seek(0)
            file = discord.File(buf, filename="rps_result.png")

            result_str = {"win": "WIN", "lose": "LOSE", "draw": "DRAW"}[result]
            color = discord.Color.green() if result == "win" else discord.Color.red() if result == "lose" else discord.Color(DRAW_COLOR)

            embed = create_embed(f"{CURRENCY_NAME}じゃんけん", f"### {PNC_EMOJI_STR}`{session.calc_win_amount()}` **{result_str}**", color)
            embed.set_image(url="attachment://rps_result.png")
            embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1219916908485283880/1387141204604620918/ChatGPT_Image_2025625_03_43_31.png?ex=685c436b&is=685af1eb&hm=ee447640b7d37905669af4ea5364e84788e9a0874a010b2fb5a13205968b4154&")
            embed.add_field(name="🔐 Provably Fair", value=pf.get_pf_info(), inline=False)
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)

            if result == "lose":
                game_sessions.pop(session.user_id, None)
                await interaction.response.edit_message(embed=embed, attachments=[file], view=None)
                self.stop()
            elif result == "win":
                if len(session.history) >= 20:
                    amount = session.calc_win_amount()
                    profit = amount - session.bet_amount
                    update_user_balance(session.user_id, amount)

                    await interaction.followup.send(
                        f"20連勝達成！自動キャッシュアウトで {PNC_EMOJI_STR}`{amount}`n＋{PNC_EMOJI_STR}`{profit}`",
                        ephemeral=True
                    )
                    await send_casino_log(
                        interaction,
                        "MAX WIN",
                        WIN_EMOJI,
                        profit,
                        f"",
                        color=discord.Color(SUCCESS_COLOR)
                    )
                    game_sessions.pop(session.user_id, None)
                    self.stop()
                    return
                session.next_round()
                await interaction.response.edit_message(embed=embed, attachments=[file], view=self)
            else:
                await interaction.response.edit_message(embed=embed, attachments=[file], view=self)

        except Exception as e:
            print("[ERROR] resolve 内で例外が発生:", e)
            traceback.print_exc()
            try:
                await interaction.response.send_message("⚠️ 内部エラーが発生しました。", ephemeral=True)
            except discord.InteractionResponded:
                pass