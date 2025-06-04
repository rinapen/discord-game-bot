import discord
import random
from discord import app_commands
from bot import bot
from database.db import get_user_balance, update_user_balance
from utils.logs import b_send_casino_log
from utils.stats import get_user_net_profit, log_transaction
from utils.stake_mines import get_stake_multiplier, get_stake_win_rate  # 追加
from utils.pnc import get_total_pnc
from paypay_session import paypay_session

BASE_COLOR_CODE = 0x2b2d31
VALID_BETS = [100, 500, 1000]
GRID_SIZE = 5
MINE_OPTIONS = list(range(1, 25))

games = {}

def compute_fair_multiplier(mine_count, revealed_count):
    probability = 1.0
    for n in range(revealed_count):
        numerator = 25 - mine_count - n
        denominator = 25 - n
        if denominator == 0:
            return float('inf')
        probability *= numerator / denominator
    if probability == 0:
        return float('inf')
    return round(1 / probability, 4)

def biased_mine_placement(mine_count):
    all_cells = [(x, y) for x in range(GRID_SIZE) for y in range(GRID_SIZE)]

    def get_weight(pos):
        center_x, center_y = GRID_SIZE // 2, GRID_SIZE // 2
        dx = abs(pos[0] - center_x)
        dy = abs(pos[1] - center_y)
        distance = (dx**2 + dy**2)**0.5
        return 1 / (1 + distance)**1.5  # ← 指数を上げて偏りを緩める


    weighted_cells = [(cell, get_weight(cell)) for cell in all_cells]
    weighted_cells_dict = dict(weighted_cells)

    # シャッフルして一意に選ぶ
    sorted_cells = sorted(all_cells, key=lambda cell: weighted_cells_dict[cell], reverse=True)

    bias_count = int(mine_count * 0.8)
    pure_count = mine_count - bias_count

    biased_cells = sorted_cells[:bias_count]
    remaining_cells = list(set(all_cells) - set(biased_cells))
    pure_cells = random.sample(remaining_cells, pure_count)

    all_mines = set(biased_cells + pure_cells)
    assert len(all_mines) == mine_count, f"[BUG] 地雷数が一致しない: {len(all_mines)} != {mine_count}"
    return all_mines


class MinesGame:
    def __init__(self, user_id, bet, mine_count):
        self.user_id = user_id
        self.bet = bet
        self.mine_count = mine_count
        self.grid = [["⬜" for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        self.revealed = set()
        self.mines = set()  
        self.finished = False
        self.current_reward = 0
        self.payout_multiplier = 1.0
        self.consecutive_wins = 0

    def reveal(self, x, y):
        if self.finished or (x, y) in self.revealed:
            return None

        self.revealed.add((x, y))

        # 勝率から外れる場合は、そのマスを💣にして終了
        win_rate = get_stake_win_rate(self.mine_count, len(self.revealed))
        print(win_rate)
        if random.random() > win_rate:
            self.grid[x][y] = "💣"
            self.mines = {(x, y)}  # ← 実際の爆弾の位置はここだけ
            self.finished = True
            return "lose"

        self.grid[x][y] = "💎"
        self.consecutive_wins += 1
        self.payout_multiplier = get_stake_multiplier(self.mine_count, self.consecutive_wins)
        self.current_reward = round(self.bet * self.payout_multiplier)
        return "win"



    def cashout(self):
        if self.finished:
            return None
        self.finished = True
        return round(self.current_reward)


def create_mines_embed(game, reveal_all=False, result=None, payout=None):
    grid_display = ""
    for x in range(GRID_SIZE):
        row = []
        for y in range(GRID_SIZE):
            if reveal_all:
                row.append("💎" if (x, y) not in game.mines else "💣")
            elif (x, y) in game.revealed:
                row.append("💎" if (x, y) not in game.mines else "💣")
            else:
                row.append("⬜")

        grid_display += " ".join(row) + "\n"

    embed = discord.Embed(title="💣 マインズ - Mines", color=BASE_COLOR_CODE)
    embed.add_field(name="**ゲーム盤**", value=f"```\n{grid_display}\n```", inline=False)
    embed.add_field(name="**現在の倍率**", value=f"`x{game.payout_multiplier:.4f}`", inline=True)
    embed.add_field(name="💰 **現在の獲得額**", value=f"`{round(game.current_reward)} PNC`", inline=False)
    embed.add_field(name="**地雷の数**", value=f"`{game.mine_count}個`", inline=True)
    if result:
        embed.add_field(name="**結果**", value=f"`{result}`", inline=False)
        if payout is not None:
            embed.add_field(name="💰 **最終獲得PNC**", value=f"`{payout} PNC`", inline=False)
    return embed

class MinesView(discord.ui.View):
    def __init__(self, user_id, game):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.game = game

        for row in range(GRID_SIZE):
            for col in range(GRID_SIZE):
                self.add_item(MinesButton(user_id, game, row, col))

class MinesButton(discord.ui.Button):
    def __init__(self, user_id, game, x, y):
        super().__init__(style=discord.ButtonStyle.secondary, label="⬜", row=x)
        self.user_id = user_id
        self.game = game
        self.x = x
        self.y = y

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ **このゲームの参加者ではありません！**", ephemeral=True)
            return

        if self.game.finished:
            await interaction.response.send_message("❌ **ゲームはすでに終了しています！**", ephemeral=True)
            return

        result = self.game.reveal(self.x, self.y)

        if result == "lose":
            payout = 0
            log_transaction(self.user_id, "mines", self.game.bet, payout)
            await b_send_casino_log(interaction, bet=self.game.bet, payout=payout, description="", game="Mines", revealed=len(self.game.revealed), mines=self.game.mine_count, max_reward=self.game.current_reward)
            await end_mines_game(interaction, self.game, "💥 ハズレを引いた！", payout)
        elif result == "win":
            await update_mines_board(interaction, self.game)
        else:
            await interaction.response.send_message("❌ **無効な操作です！**", ephemeral=True)

class CashoutButton(discord.ui.Button):
    def __init__(self, user_id, game, disabled=False):
        super().__init__(style=discord.ButtonStyle.success, label="💰 出金", disabled=disabled)
        self.user_id = user_id
        self.game = game

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ **この出金ボタンはあなたのものではありません！**", ephemeral=True)
            return

        if self.game.finished:
            await interaction.response.send_message(embed=discord.Embed(title="❌ 出金不可", description="**すでにゲームが終了しています！**", color=discord.Color.red()), ephemeral=True)
            return

        payout = self.game.cashout()
        update_user_balance(self.user_id, payout)
        log_transaction(self.user_id, "mines", self.game.bet, payout)
        await b_send_casino_log(interaction, bet=self.game.bet, payout=payout, description="", game="Mines", revealed=len(self.game.revealed), mines=self.game.mine_count, max_reward=self.game.current_reward)
        new_balance = get_user_balance(self.user_id)
        await interaction.response.send_message(
            embed=discord.Embed(
                title="✅ 出金成功！",
                description=f"**{payout} PNC を出金しました！**\n\n💰 **現在の残高**: `{new_balance} PNC`",
                color=discord.Color.green()
            ), ephemeral=True
        )
        await end_mines_game(interaction, self.game, "✅ 出金成功！", payout)


async def update_mines_board(interaction, game):
    embed = create_mines_embed(game)
    view = MinesView(game.user_id, game)

    for child in view.children:
        if isinstance(child, MinesButton):
            if (child.x, child.y) in game.revealed:
                if (child.x, child.y) in game.mines:
                    child.style = discord.ButtonStyle.danger
                    child.label = "💣"
                else:
                    child.style = discord.ButtonStyle.success
                    child.label = "💎"
                child.disabled = True

    try:
        await interaction.response.edit_message(embed=embed, view=view)
    except discord.errors.InteractionResponded:
        await interaction.message.edit(embed=embed, view=view)

async def end_mines_game(interaction, game, result, payout):
    """ゲーム終了処理（開けたマスだけ表示 + 全ボタン無効化）"""
    embed = create_mines_embed(game, reveal_all=False, result=result, payout=payout)
    view = MinesView(game.user_id, game)

    for child in view.children:
        if isinstance(child, MinesButton):
            pos = (child.x, child.y)
            child.disabled = True
            if pos in game.revealed:
                if pos in game.mines:
                    child.style = discord.ButtonStyle.danger
                    child.label = "💣"
                else:
                    child.style = discord.ButtonStyle.success
                    child.label = "💎"
            else:
                child.label = "⬜"
                child.style = discord.ButtonStyle.secondary

    try:
        await interaction.response.edit_message(embed=embed, view=view)
    except discord.errors.InteractionResponded:
        await interaction.message.edit(embed=embed, view=view)

    # 出金ボタン無効化
    if hasattr(game, "cashout_message_id"):
        cashout_embed = discord.Embed(
            title="💰 PNC 出金",
            description="ゲームが終了しました。",
            color=discord.Color.red(),
        )
        cashout_view = discord.ui.View()
        cashout_view.add_item(CashoutButton(game.user_id, game, disabled=True))
        try:
            await interaction.followup.edit_message(game.cashout_message_id, embed=cashout_embed, view=cashout_view)
        except discord.errors.NotFound:
            pass


@bot.tree.command(name="mines", description="💣 マインズをプレイ！")
@app_commands.describe(amount="ベット額", mines="地雷の数（選択肢から選択）")
@app_commands.choices(amount=[app_commands.Choice(name=f"{b} PNC", value=b) for b in VALID_BETS], mines=[app_commands.Choice(name=f"{m}個", value=m) for m in MINE_OPTIONS])
async def mines(interaction: discord.Interaction, amount: int, mines: int):
    user_id = interaction.user.id
    balance = get_user_balance(user_id)
    if balance < amount:
        await interaction.response.send_message("❌ **残高不足！**", ephemeral=True)
        return
    update_user_balance(user_id, -amount)
    games[user_id] = MinesGame(user_id, amount, mines)
    game = games[user_id]
    embed = create_mines_embed(game)
    view = MinesView(user_id, game)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    cashout_embed = discord.Embed(title="PNC 出金", description="現在のPNCを引き出す場合はボタンを押してください。", color=discord.Color.gold())
    cashout_view = discord.ui.View()
    cashout_view.add_item(CashoutButton(user_id, game, disabled=False))
    cashout_message = await interaction.followup.send(embed=cashout_embed, view=cashout_view, ephemeral=True)
    game.cashout_message_id = cashout_message.id