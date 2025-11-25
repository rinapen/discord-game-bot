import discord
import random
import os
import hmac
import hashlib
import aiohttp
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

from database.db import update_user_balance

from ui.pf import ProvablyFairParams
from utils.emojis import PNC_EMOJI_STR, WIN_EMOJI
from utils.embed import create_embed
from utils.logs import send_casino_log
from utils.color import BLACKJACK_COLOR

CARD_PATH = "assets/bj/cards/"
TABLE_IMAGE_PATH = f"assets/bj/table.png"
FONT_PATH = "assets/font/NotoSansJP-VariableFont_wght.ttf"

blackjack_games = {}

def calculate_hand(hand):
    total = 0
    aces = 0
    for _, rank in hand:
        if rank in ["J", "Q", "K"]:
            total += 10
        elif rank == "A":
            aces += 1
            total += 11
        else:
            total += int(rank)
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total

def get_card_index(server_seed, client_seed, nonce, cursor):
    message = f"{client_seed}:{nonce}:{cursor}".encode()
    digest = hmac.new(server_seed.encode(), message, hashlib.sha256).digest()
    number = int.from_bytes(digest, 'big') / 2**256
    return int(number * 52)

def get_card():
    suits = ["S", "H", "D", "C"]
    ranks = ["A"] + [str(n) for n in range(2, 11)] + ["J", "Q", "K"]
    suit = random.choice(suits)
    rank = random.choice(ranks)
    return f"{rank}{suit}", rank

class BlackjackView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id

    @discord.ui.button(label="ヒット", style=discord.ButtonStyle.primary)
    async def hit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = self.user_id
        game = blackjack_games.get(user_id)
        if not game:
            await interaction.response.send_message("ゲームが見つかりません。", ephemeral=True)
            return

        game.hit()
        if game.is_busted(game.player_hand):
            game.finished = True
            game.dealer_play()
            result = game.get_result()
            del blackjack_games[user_id]

            async with aiohttp.ClientSession() as session:
                async with session.get(interaction.user.display_avatar.url) as resp:
                    avatar_bytes = BytesIO(await resp.read())

            if result == "負け":
                outcome_text = f"### {PNC_EMOJI_STR}`{game.bet:,}` **LOSE**"
                color = discord.Color.from_str("#ff3d74") 
            else:
                outcome_text = f"### {PNC_EMOJI_STR}`{game.bet:,}` **WIN**"
                color = discord.Color.from_str("#26ffd4") 
                update_user_balance(user_id, game.bet * 2)
                await send_casino_log(
                    interaction, winorlose="WIN", emoji=WIN_EMOJI, price=game.bet * 2,
                    description="",
                    color=discord.Color.from_str("#26ffd4"),
                )
            img = game.render_image(
                reveal_dealer=True,
                user_displayname=interaction.user.display_name,
                user_avatar_data=avatar_bytes
            )
            buf = BytesIO()
            img.save(buf, format='PNG')
            buf.seek(0)
            file = discord.File(buf, filename="blackjack.png")
            embed = create_embed("バースト", outcome_text, color=color)
            embed.set_image(url="attachment://blackjack.png")
            embed.add_field(name="[🔐] Provably Fair", value=game.get_pf_embed_field(), inline=False)
            embed.set_footer(text="検証方法：HMAC-SHA256(client:nonce:cursor)でカード順を再計算可能")
            embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1219916908485283880/1386317663231414272/ChatGPT_Image_2025622_21_11_08.png?ex=6859446f&is=6857f2ef&hm=19507da3f6ae2ea49377b1112e687a6690cd37bb229cc4ebcd5a1fef2c5965e6&")
            await interaction.response.edit_message(embed=embed, attachments=[file], view=None)
            return

        async with aiohttp.ClientSession() as session:
            async with session.get(interaction.user.display_avatar.url) as resp:
                avatar_bytes = BytesIO(await resp.read())

        img = game.render_image(
            user_displayname=interaction.user.display_name,
            user_avatar_data=avatar_bytes
        )
        buf = BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        file = discord.File(buf, filename="blackjack.png")
        embed = create_embed("ヒット", f"{interaction.user.mention} の現在の手札です。", BLACKJACK_COLOR)
        embed.set_image(url="attachment://blackjack.png")
        await interaction.response.edit_message(embed=embed, attachments=[file], view=self)
    
    @discord.ui.button(label="スタンド", style=discord.ButtonStyle.secondary)
    async def stand_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = self.user_id
        game = blackjack_games.get(user_id)
        if not game:
            await interaction.response.send_message("ゲームが見つかりません。", ephemeral=True)
            return

        game.dealer_play()
        result = game.get_result()
        del blackjack_games[user_id]

        if result == "勝ち":
            if game.is_blackjack(game.player_hand):
                reward = int(game.bet * 2.5)  # 3:2 の配当
                result_text = f"### {PNC_EMOJI_STR}`{reward - game.bet:,}` **WIN**"
            else:
                reward = game.bet * 2
                result_text = f"### {PNC_EMOJI_STR}`{game.bet:,}` **WIN**"
            update_user_balance(user_id, reward)
            color = discord.Color.from_str("#26ffd4")

            await send_casino_log(
                interaction, winorlose="WIN", emoji=WIN_EMOJI, price=reward,
                description="",
                color=discord.Color.from_str("#26ffd4"),
            )
        elif result == "引き分け":
            update_user_balance(user_id, game.bet)
            result_text = f"### {PNC_EMOJI_STR}`{game.bet:,}` **DRAW**"
            color = discord.Color.from_str("#aaaaaa")  # ← これを追加
        else:
            result_text = f"### {PNC_EMOJI_STR}`{game.bet:,}` **LOSE**"
            color = discord.Color.from_str("#ff3d74") 

        async with aiohttp.ClientSession() as session:
            async with session.get(interaction.user.display_avatar.url) as resp:
                avatar_bytes = BytesIO(await resp.read())

        img = game.render_image(
            reveal_dealer=True,
            user_displayname=interaction.user.display_name,
            user_avatar_data=avatar_bytes
        )
        buf = BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        file = discord.File(buf, filename="blackjack.png")
        embed = create_embed("結果", result_text, color=color)
        embed.set_image(url="attachment://blackjack.png")
        embed.add_field(name="[🔐] Provably Fair", value=game.get_pf_embed_field(), inline=False)
        embed.set_footer(text="検証方法：HMAC-SHA256(client:nonce:cursor)でカード順を再計算可能")
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1219916908485283880/1386317663231414272/ChatGPT_Image_2025622_21_11_08.png?ex=6859446f&is=6857f2ef&hm=19507da3f6ae2ea49377b1112e687a6690cd37bb229cc4ebcd5a1fef2c5965e6&")
        await interaction.response.edit_message(embed=embed, attachments=[file], view=None)

class BlackjackGame:
    def __init__(self, bet, client_seed=None, server_seed=None, nonce=0):
        self.bet = bet
        self.player_hand = []
        self.dealer_hand = []
        self.finished = False
        self.cursor = 0
        self.pf = ProvablyFairParams(client_seed, server_seed, nonce)
        dealer_files = [f for f in os.listdir("assets/bj/dealer") if f.endswith(".png")]
        dealer_file = random.choice(dealer_files)
        self.dealer_file = dealer_file
        self.dealer_name = os.path.splitext(dealer_file)[0]

    def draw_card(self):
        card = self.pf.get_card(self.cursor)
        self.cursor += 1
        return card

    def deal_initial(self):
        for _ in range(2):
            self.player_hand.append(self.draw_card())
            self.dealer_hand.append(self.draw_card())

    def hit(self, to_player=True):
        card = self.draw_card()
        if to_player:
            self.player_hand.append(card)
        else:
            self.dealer_hand.append(card)

    def is_busted(self, hand):
        return calculate_hand(hand) > 21

    def is_blackjack(self, hand):
        return len(hand) == 2 and calculate_hand(hand) == 21

    def dealer_play(self):
        while calculate_hand(self.dealer_hand) < 17:
            self.hit(to_player=False)

    def get_result(self):
        if self.is_busted(self.player_hand):
            return "負け"
        elif self.is_busted(self.dealer_hand):
            return "勝ち"
        else:
            player_total = calculate_hand(self.player_hand)
            dealer_total = calculate_hand(self.dealer_hand)
            if player_total > dealer_total:
                return "勝ち"
            elif player_total < dealer_total:
                return "負け"
            else:
                return "引き分け"

    def get_pf_embed_field(self):
        return self.pf.get_pf_embed_field()
    
    def render_image(self, reveal_dealer=False, user_displayname="", user_avatar_data: BytesIO = None):
        table = Image.open(TABLE_IMAGE_PATH).convert("RGBA")
        draw = ImageDraw.Draw(table)
        font = ImageFont.truetype(FONT_PATH, 40)

        card_width, card_height = 140, 200
        spacing = 150
        x_offset = -40

        def paste_cards(cards, y):
            start_x = 320

            for i, (code, _) in enumerate(cards):
                card_img = Image.open(f"{CARD_PATH}{code}.png").convert("RGBA").resize((card_width, card_height))
                shadow = Image.new("RGBA", card_img.size, (0, 0, 0, 100))
                shadow_offset = (6, 6)
                x = start_x + i * spacing
                table.paste(shadow, (x + shadow_offset[0], y + shadow_offset[1]), shadow)
                table.paste(card_img, (x, y), card_img)
            return calculate_hand(cards)


        player_total = paste_cards(self.player_hand, y=400)

        if reveal_dealer:
            dealer_total = paste_cards(self.dealer_hand, y=120)
        else:
            dealer_total = calculate_hand([self.dealer_hand[0]])
            first_card = Image.open(f"{CARD_PATH}{self.dealer_hand[0][0]}.png").convert("RGBA").resize((card_width, card_height))
            back_card = Image.open(f"{CARD_PATH}back.png").convert("RGBA").resize((card_width, card_height))
            
            start_x = 320  
            shadow = Image.new("RGBA", first_card.size, (0, 0, 0, 100))
            table.paste(shadow, (start_x + 6, 120 + 6), shadow)
            table.paste(first_card, (start_x, 120), first_card)
            table.paste(shadow, (start_x + spacing + 6, 120 + 6), shadow)
            table.paste(back_card, (start_x + spacing, 120), back_card)

        text_color = (255, 255, 255)
        shadow_color = (0, 0, 0)
        px, py = table.width - 250, 420
        dx, dy = table.width - 250, 140

        def draw_score(draw, x, y, label, value):
            text = f"{label}: {value}"
            draw.text((x + 2, y + 2), text, font=font, fill=shadow_color)
            draw.text((x, y), text, font=font, fill=text_color)

        draw_score(draw, dx, dy, "Dealer", dealer_total)
        draw_score(draw, px, py, "You", player_total)

        icon_font = ImageFont.truetype(FONT_PATH, 36)
        dealer_icon = Image.open(f"assets/bj/dealer/{self.dealer_file}").convert("RGBA").resize((120, 120))
        dealer_name = self.dealer_name

        user_icon = Image.open(user_avatar_data).convert("RGBA").resize((120, 120))

        def crop_circle(im):
            mask = Image.new("L", im.size, 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, im.size[0], im.size[1]), fill=255)
            result = Image.new("RGBA", im.size)
            result.paste(im, (0, 0), mask)
            return result

        icon_x = 130
        dealer_icon_y = 150
        player_icon_y = 420

        table.paste(crop_circle(dealer_icon), (icon_x, dealer_icon_y), crop_circle(dealer_icon))
        draw.text((icon_x, dealer_icon_y + 130), dealer_name, font=icon_font, fill=text_color)

        table.paste(crop_circle(user_icon), (icon_x, player_icon_y), crop_circle(user_icon))
        draw.text((icon_x + 3, player_icon_y + 130), "あなた" or "You", font=icon_font, fill=text_color)

        return table
    
    def get_provably_fair_fields(self):
        return (
            f"検証用:\n"
            f"ServerSeedHash: `{self.pf.server_seed_hash}`\n"
            f"ClientSeed: `{self.pf.client_seed}`\n"
            f"Nonce: `{self.pf.nonce}`"
        )