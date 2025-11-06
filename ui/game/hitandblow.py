import discord
from discord.ui import View, Button
import re
from PIL import Image, ImageDraw, ImageFont
import os
import random


from database.db import get_user_balance
from utils.embed import create_embed
from utils.embed_factory import EmbedFactory
from utils.emojis import PNC_EMOJI_STR
from utils.color import BASE_COLOR_CODE
from config import HITANDBLOW_CATEGORY_ID

class HitAndBlowAcceptButton(discord.ui.View):
    def __init__(self, challenger: discord.Member, opponent: discord.Member, amount: int, timeout=60):
        super().__init__(timeout=timeout)
        self.challenger = challenger
        self.opponent = opponent
        self.amount = amount
        self.accepted = False

    @discord.ui.button(label="承諾する", style=discord.ButtonStyle.success)
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message("このボタンはあなた用ではありません。", ephemeral=True)
            return

        self.accepted = True
        await interaction.response.send_message("✅ 勝負を受けました！", ephemeral=True)
        self.stop()

class DigitInputView(discord.ui.View):
    def __init__(self, user: discord.User, timeout=50):
        super().__init__(timeout=timeout)
        self.user = user
        self.digits = ""
        self.confirmed = False
        self.message = None
        self.opponent_ready = False  # ← 相手の状態を管理するフラグ（後で拡張）
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        is_full = len(self.digits) >= 3

        for i in range(0, 5):
            digit = str(i)
            self.add_item(DigitButton(label=digit, parent_view=self, disabled=is_full or (digit in self.digits)))

        for i in range(5, 10):
            digit = str(i)
            self.add_item(DigitButton(label=digit, parent_view=self, disabled=is_full or (digit in self.digits)))

        self.add_item(ClearButton(parent_view=self, disabled=(len(self.digits) == 0)))
        self.add_item(ConfirmButton(parent_view=self, disabled=not is_full))

    async def update_message(self):
        embed = discord.Embed(
            title="数字を入力してください",
            description=f"現在の入力: `{self.digits}`",
            color=0x2980b9
        )
        if self.message:
            self.update_buttons()
            await self.message.edit(embed=embed, view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("この操作はあなたにはできません。", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        if self.message:
            await self.message.edit(view=None)

class DigitButton(discord.ui.Button):
    def __init__(self, label: str, parent_view: DigitInputView, disabled: bool):
        super().__init__(
            label=label,
            style=discord.ButtonStyle.secondary,
            row=0 if int(label) < 5 else 1,
            disabled=disabled
        )
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.digits += self.label
        await self.parent_view.update_message()
        await interaction.response.defer()

class ClearButton(discord.ui.Button):
    def __init__(self, parent_view: DigitInputView, disabled: bool):
        super().__init__(label="削除", style=discord.ButtonStyle.danger, row=2, disabled=disabled)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.digits = ""
        await self.parent_view.update_message()
        await interaction.response.defer()

class ConfirmButton(discord.ui.Button):
    def __init__(self, parent_view: DigitInputView, disabled: bool):
        super().__init__(label="決定", style=discord.ButtonStyle.primary, row=2, disabled=disabled)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.confirmed = True
        self.parent_view.clear_items()

        embed = discord.Embed(
            title="✅ 数字が決定されました",
            description=f"あなたの選んだ数字: `{self.parent_view.digits}`\n\n対戦相手の入力を待っています...",
            color=BASE_COLOR_CODE
        )
        if self.parent_view.message:
            await self.parent_view.message.edit(embed=embed, view=None)

        await interaction.response.defer()
        self.parent_view.stop()

class GuessInputView(discord.ui.View):
    def __init__(self, user: discord.User, timeout=60):
        super().__init__(timeout=timeout)
        self.user = user
        self.guess = ""
        self.confirmed = False
        self.message = None
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        is_full = len(self.guess) >= 3

        for i in range(10):
            digit = str(i)
            self.add_item(Button(label=digit, style=discord.ButtonStyle.secondary,
                                 disabled=is_full or (digit in self.guess),
                                 custom_id=f"guess_digit_{digit}"))

        self.add_item(Button(label="削除", style=discord.ButtonStyle.danger, custom_id="guess_clear",
                             disabled=(len(self.guess) == 0)))
        self.add_item(Button(label="決定", style=discord.ButtonStyle.success, custom_id="guess_confirm",
                             disabled=not is_full))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user.id

    async def on_timeout(self):
        if self.message:
            await self.message.edit(view=None)

    async def interaction_handler(self, interaction: discord.Interaction):
        cid = interaction.data.get("custom_id")
        if cid.startswith("guess_digit_"):
            self.guess += cid.split("_")[-1]
        elif cid == "guess_clear":
            self.guess = ""
        elif cid == "guess_confirm":
            self.confirmed = True
            await interaction.response.defer()
            self.stop()
            return

        await interaction.response.defer()
        self.update_buttons()
        await self.message.edit(view=self)


class GameSession:
    def __init__(self, player1: discord.Member, player2: discord.Member, digits1: str, digits2: str):
        self.players = {
            player1.id: {
                "member": player1,
                "digits": digits1,
                "guesses": []
            },
            player2.id: {
                "member": player2,
                "digits": digits2,
                "guesses": []
            }
        }
        self.turn_order = [player1.id, player2.id]
        random.shuffle(self.turn_order)
        self.turn_index = 0

    def current_player_id(self):
        return self.turn_order[self.turn_index % 2]

    def opponent_id(self):
        return self.turn_order[(self.turn_index + 1) % 2]

    def advance_turn(self):
        self.turn_index += 1

    def add_guess(self, user_id: int, guess: str):
        self.players[user_id]["guesses"].append(guess)

    def is_correct(self, user_id: int, guess: str):
        target = self.players[self.opponent_id()]["digits"]
        return guess == target

    def evaluate_hit_and_blow(self, guess: str, target: str):
        hit = sum(g == t for g, t in zip(guess, target))
        blow = sum((min(guess.count(x), target.count(x)) for x in set(guess))) - hit
        return hit, blow
    
DIGIT_POSITIONS = [(55, 145), (145, 145), (235, 145)]  # 適宜微調整

def generate_board_image(
    digits: str,
    user_id: int,
    user_icon_path: str,
    user_name: str,
    opponent_icon_path: str,
    opponent_name: str,
    my_guesses: list[str] = [],
    opponent_guesses: list[str] = []
) -> str:
    from PIL import Image, ImageDraw, ImageFont
    base_path = "assets/hab/base.png"
    num_path = "assets/hab/digits/"
    output_path = f"./tmp/board_{user_id}.png"
    os.makedirs("./tmp", exist_ok=True)

    ICON_SIZE = (60, 60)
    DIGIT_POSITIONS = [(36, 95), (107, 95), (176, 95)]
    USER_ICON_POS = (10, 19)
    OPPONENT_ICON_POS = (455, 19)
    USER_NAME_POS = (80, 35)
    OPPONENT_NAME_POS = (350, 35)
    GUESS_FONT_POS_SELF = [(70, 195 + 25 * i) for i in range(6)]
    GUESS_FONT_POS_OPP = [(310, 195 + 25 * i) for i in range(6)]

    base_img = Image.open(base_path).convert("RGBA")
    draw = ImageDraw.Draw(base_img)
    try:
        font = ImageFont.truetype("assets/font/NotoSansJP-VariableFont_wght.ttf", 16)
    except:
        font = ImageFont.load_default()

    # 中央数字
    for i, d in enumerate(digits):
        digit_img = Image.open(os.path.join(num_path, f"{d}.png")).convert("RGBA").resize((50, 70))
        base_img.paste(digit_img, DIGIT_POSITIONS[i], digit_img)

    # 丸アイコン
    def paste_circle_icon(img_path, pos):
        icon = Image.open(img_path).convert("RGBA").resize(ICON_SIZE)
        mask = Image.new("L", ICON_SIZE, 0)
        ImageDraw.Draw(mask).ellipse((0, 0) + ICON_SIZE, fill=255)
        base_img.paste(icon, pos, mask)

    paste_circle_icon(user_icon_path, USER_ICON_POS)
    paste_circle_icon(opponent_icon_path, OPPONENT_ICON_POS)

    # 名前
    draw.text(USER_NAME_POS, user_name, fill="white", font=font)
    draw.text(OPPONENT_NAME_POS, opponent_name, fill="white", font=font)

    # 推理履歴
    for i, guess in enumerate(my_guesses[:6]):
        draw.text(GUESS_FONT_POS_SELF[i], guess, fill="white", font=font)
    for i, guess in enumerate(opponent_guesses[:6]):
        draw.text(GUESS_FONT_POS_OPP[i], guess, fill="white", font=font)

    base_img.save(output_path)
    return output_path

async def send_initial_board(channel: discord.TextChannel, user: discord.User, digits: str):
    from discord import File

    image_path = generate_board_image(digits, user.id)
    file = File(image_path, filename="board.png")

    embed = discord.Embed(
        title="ゲーム開始！",
        description="あなたが選んだ数字がこちらです。\n対戦相手のターンを待ちましょう。",
        color=BASE_COLOR_CODE
    )
    embed.set_image(url="attachment://board.png")

    await channel.send(embed=embed, file=file)

import aiohttp

async def download_avatar(avatar_url: str, user_id: int) -> str:
    os.makedirs("./tmp", exist_ok=True)
    path = f"./tmp/avatar_{user_id}.png"
    async with aiohttp.ClientSession() as session:
        async with session.get(avatar_url) as resp:
            if resp.status == 200:
                with open(path, "wb") as f:
                    f.write(await resp.read())
    return path