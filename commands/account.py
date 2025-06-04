import discord
import re
from discord import app_commands
from discord.ext import commands
from bot import bot
from config import PAYPAY_LINK_REGEX, MIN_INITIAL_DEPOSIT,PAYPAY_ICON_URL
from database.db import update_user_balance, get_user_balance, register_user, users_collection, user_transactions_collection
from utils.embed import create_embed
from utils.logs import send_paypay_log
from utils.stats import log_transaction
from PayPaython_mobile.main import PayPayError
from paypay_session import paypay_session
from decimal import Decimal, ROUND_HALF_UP

class RegisterModal(discord.ui.Modal, title="口座開設"):
    def __init__(self):
        super().__init__()
        self.username = discord.ui.TextInput(label="名前(適当でいい)", placeholder="例: べるざべす")
        self.deposit_link = discord.ui.TextInput(label="入金リンク（最低 116 pay 必須）", placeholder="PayPay送金リンクを入力")
        self.add_item(self.username)
        self.add_item(self.deposit_link)

    async def on_submit(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        discord_user = interaction.user
        await interaction.response.defer(ephemeral=True)

        # PayPayリンクだけを抽出
        link_match = re.search(PAYPAY_LINK_REGEX, self.deposit_link.value)
        if not link_match:
            embed = create_embed("", "無効なリンクです。有効な PayPay リンクを入力してください。", discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        paypay_link = link_match.group(0).strip()

        if users_collection.find_one({"user_id": user_id}):
            embed = create_embed("", "あなたはすでに口座を開設しています。", discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        try:
            deposit_info = paypay_session.paypay.link_check(paypay_link)
            amount = Decimal(deposit_info.amount)
        except PayPayError as e:
            error_code = e.args[0].get("error", {}).get("backendResultCode", "不明")
            error_msg = "このリンクはすでに使用済みです。" if error_code == "02100029" else f"エラーコード: `{error_code}`"
            embed = create_embed("", f"PayPayリンクの確認中にエラーが発生しました。\n{error_msg}", discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        fee = max((amount * Decimal(0.14)).quantize(Decimal("1"), rounding=ROUND_HALF_UP), Decimal(10))
        net_amount = amount - fee

        if amount < (Decimal(MIN_INITIAL_DEPOSIT) + fee):
            embed = create_embed("", f"最低 `{int(MIN_INITIAL_DEPOSIT + fee):,} PNC` が必要です。", discord.Color.yellow())
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        user = paypay_session.paypay.link_receive(paypay_link)
        user_transactions_collection.insert_one({
            "user_id": user_id,
            "transactions": []
        })
        register_user(user_id, self.username.value, deposit_info.sender_external_id)
        update_user_balance(user_id, int(net_amount))
        log_transaction(
            user_id=user_id,
            game_type="payin",
            amount=int(amount),
            payout=int(net_amount)
        )
        embed = discord.Embed(title="口座開設完了", color=discord.Color.green())
        embed.set_author(name="PayPay", icon_url=PAYPAY_ICON_URL)
        embed.add_field(name="入金額", value=f"`{int(amount):,}円`", inline=False)
        embed.add_field(name="手数料", value=f"`{int(fee):,}円`", inline=False)
        embed.add_field(name="初期残高", value=f"`{int(net_amount):,} PNC`", inline=False)
        embed.add_field(name="決済番号", value=f"`{deposit_info.order_id}`")
        embed.set_footer(text=f"{deposit_info.sender_name} 様", icon_url=deposit_info.sender_icon)
        await interaction.followup.send(embed=embed, ephemeral=True)
        await send_paypay_log(discord_user, amount, fee, net_amount, deposit_info, is_register=True)

class PayinModal(discord.ui.Modal, title="PNC入金"):
    def __init__(self):
        super().__init__()
        self.link = discord.ui.TextInput(label="PayPayリンク", placeholder="PayPay送金リンクを入力")
        self.add_item(self.link)

    async def on_submit(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        user = interaction.user
        await interaction.response.defer(ephemeral=True)

        user_info = users_collection.find_one({"user_id": user_id})
        if not user_info:
            embed = create_embed("", "あなたの口座が見つかりません。\n `/kouza` で口座を開設してください。", discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        link_match = re.search(PAYPAY_LINK_REGEX, self.link.value)
        if not link_match:
            embed = create_embed("", "無効なリンクです。有効な PayPay リンクを入力してください。", discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        paypay_link = link_match.group(0).strip()

        try:
            link_info = paypay_session.paypay.link_check(paypay_link)
            if link_info.status in ["COMPLETED", "REJECTED", "FAILED"]:
                embed = create_embed("", "このリンクはすでに使用済み、または無効です。", discord.Color.red())
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            amount = Decimal(link_info.amount)
        except PayPayError as e:
            error_code = e.args[0].get("error", {}).get("backendResultCode", "不明")
            embed = create_embed("", f"PayPayリンクの確認中にエラーが発生しました。\nエラーコード: `{error_code}`", discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        fee = max((amount * Decimal(0.14)).quantize(Decimal("1"), rounding=ROUND_HALF_UP), Decimal(10))
        net_amount = amount - fee

        if amount < (Decimal(MIN_INITIAL_DEPOSIT) + fee):
            embed = create_embed("", f"最低入金額は `{int(MIN_INITIAL_DEPOSIT + fee):,} PNC` です。", discord.Color.yellow())
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        try:
            paypay_session.paypay.link_receive(paypay_link)
            update_user_balance(user_id, int(net_amount))
            log_transaction(user_id=user_id, game_type="payin", amount=int(amount), payout=int(net_amount))

            embed = discord.Embed(title="入金完了", color=discord.Color.green())
            embed.add_field(name="入金額", value=f"`{int(amount):,}円`", inline=True)
            embed.add_field(name="手数料", value=f"`{int(fee):,}円`", inline=True)
            embed.add_field(name="現在の残高", value=f"`{get_user_balance(user_id):,} PNC`", inline=False)

            await interaction.followup.send(embed=embed, ephemeral=True)
            await send_paypay_log(user, amount, fee, net_amount, link_info)
        except PayPayError:
            embed = create_embed("", "入金処理中にエラーが発生しました。\nこのリンクはすでに使用済み、または無効です。", discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)
            
class AccountView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # 永続化のため timeout=None
        self.add_item(RegisterButton())
        self.add_item(PayinButton())

class RegisterButton(discord.ui.Button):
    def __init__(self):
        emoji = discord.PartialEmoji(name="register", id=1379757690854707350)
        super().__init__(style=discord.ButtonStyle.success, emoji="🔑", label="口座開設")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(RegisterModal())

class PayinButton(discord.ui.Button):
    def __init__(self):
        emoji = discord.PartialEmoji(name="payin", id=1379758352564883557)
        super().__init__(style=discord.ButtonStyle.primary, emoji="⏰", label="入金")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(PayinModal())


@bot.tree.command(name="account", description="口座登録/入金フォームをチャンネルに設置")
@app_commands.checks.has_permissions(administrator=True)
async def accout(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📋 チェックイン",
        description="以下のボタンから登録または入金を行えます。",
        color=discord.Color.blurple()
    )
    embed.add_field(name="🔑 鍵受取", value="初めての方はこちらから口座を作成します。", inline=False)
    embed.add_field(name="⏰ 延長", value="すでに口座をお持ちの方は、こちらから残高を追加できます。", inline=False)

    # view = discord.ui.View()
    # view.add_item(RegisterButton())
    # view.add_item(PayinButton())

    await interaction.response.send_message(embed=embed, view=AccountView())