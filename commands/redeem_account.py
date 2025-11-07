"""
アカウント引き換えコマンド
景品ポケットのアカウント交換券を実際のアカウントに交換します
"""
import discord

from database.db import (
    users_collection,
    get_prize_pocket,
    add_prizes_to_pocket,
    get_random_unused_account,
    mark_accounts_as_exchanged,
    get_available_account_count
)
from utils.embed_factory import EmbedFactory
from utils.emojis import PNC_EMOJI_STR
from config import ACCOUNT_EXCHANGE_JPY, EXCHANGE_ENABLED


async def on_redeem_account_command(message: discord.Message) -> None:
    """
    アカウント引き換えコマンドハンドラー
    
    Args:
        message: Discordメッセージオブジェクト
    """
    # 機能が有効かチェック
    if not EXCHANGE_ENABLED:
        from utils.emojis import CLOSED_EMOJI
        embed = discord.Embed(
            title=f"{CLOSED_EMOJI} 景品交換所",
            description="景品交換機能は現在ご利用いただけません。",
            color=discord.Color.grey()
        )
        await message.channel.send(embed=embed)
        return
    
    user_id = message.author.id
    
    try:
        # ユーザー登録確認
        user_info = users_collection.find_one({"user_id": user_id})
        if not user_info:
            embed = EmbedFactory.require_registration_prompt()
            await message.channel.send(embed=embed)
            return
        
        # 景品ポケットを取得
        pocket = get_prize_pocket(user_id)
        account_tickets = pocket["accounts"]
        
        if account_tickets <= 0:
            embed = discord.Embed(
                title="アカウント交換券なし",
                description=(
                    "アカウント交換券を持っていません。\n\n"
                    "`?交換` コマンドで景品交換を行うと、\n"
                    "余りが912 PNC以上の場合にアカウント交換券を獲得できます。"
                ),
                color=discord.Color.orange()
            )
            await message.channel.send(embed=embed)
            return
        
        # 利用可能なアカウント数を確認
        available_count = get_available_account_count()
        
        if available_count <= 0:
            embed = discord.Embed(
                title="在庫切れ",
                description=(
                    "申し訳ございません。現在交換可能なアカウントの在庫がありません。\n"
                    "在庫補充までお待ちください。"
                ),
                color=discord.Color.red()
            )
            embed.set_footer(text="アカウント交換券は保持されます")
            await message.channel.send(embed=embed)
            return
        
        # 引き換え可能な個数（在庫と所持券の少ない方）
        exchange_count = min(account_tickets, available_count)
        
        # 確認メッセージ
        embed = discord.Embed(
            title="🎫 アカウント引き換え確認",
            description=(
                f"**所持アカウント交換券:** `{account_tickets}個`\n"
                f"**利用可能在庫:** `{available_count}個`\n\n"
                f"**引き換え可能:** `{exchange_count}個`"
            ),
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="注意事項",
            value=(
                "• アカウント情報は**あなたにのみ**表示されます（ephemeral）\n"
                "• 一度引き換えたアカウントは再取得できません\n"
                "• スクリーンショット等で保存してください\n"
                "• 引き換え後、交換券は消費されます"
            ),
            inline=False
        )
        
        embed.set_footer(text="以下のボタンで引き換えを確定してください")
        
        view = RedeemAccountView(message.author, exchange_count)
        await message.channel.send(embed=embed, view=view)
        
    except Exception as e:
        print(f"[ERROR] on_redeem_account_command: {e}")
        import traceback
        traceback.print_exc()
        embed = EmbedFactory.error("アカウント引き換え中にエラーが発生しました。")
        await message.channel.send(embed=embed)


class RedeemAccountView(discord.ui.View):
    """アカウント引き換え確認ビュー"""
    
    def __init__(self, user: discord.User, exchange_count: int):
        super().__init__(timeout=60)
        self.user = user
        self.exchange_count = exchange_count
    
    @discord.ui.button(label="引き換える", style=discord.ButtonStyle.green)
    async def confirm_redeem(self, interaction: discord.Interaction, button: discord.ui.Button):
        """引き換えを確定"""
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "これはあなたの引き換えではありません。",
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # ランダムにアカウントを取得
            accounts = get_random_unused_account(self.exchange_count)
            
            if not accounts:
                embed = discord.Embed(
                    title="エラー",
                    description="アカウントの取得に失敗しました。在庫切れの可能性があります。",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # アカウント交換券を消費
            add_prizes_to_pocket(
                user_id=self.user.id,
                large=0,
                medium=0,
                small=0,
                accounts=-len(accounts)  # マイナスで減らす
            )
            
            # アカウントを交換済みとしてマーク
            account_ids = [acc["_id"] for acc in accounts]
            mark_accounts_as_exchanged(account_ids, self.user.id)
            
            # アカウント情報をユーザーにのみ表示（ephemeral）
            embed = discord.Embed(
                title="✅ アカウント引き換え完了",
                description=(
                    f"**{len(accounts)}個**のアカウントを引き換えました。\n\n"
                    "⚠️ **重要:** 以下の情報は再表示できません。\n"
                    "必ずスクリーンショット等で保存してください。"
                ),
                color=discord.Color.green()
            )
            
            # アカウント情報を追加（最大25個まで）
            for idx, account in enumerate(accounts[:25], 1):
                email = account.get("email", "不明")
                password = account.get("password", "不明")
                
                embed.add_field(
                    name=f"🎫 アカウント #{idx}",
                    value=(
                        f"**Email:** `{email}`\n"
                        f"**Password:** `{password}`"
                    ),
                    inline=False
                )
            
            if len(accounts) > 25:
                embed.add_field(
                    name="⚠️ 表示制限",
                    value=f"Embedの制限により、最初の25個のみ表示しています。\n残り {len(accounts) - 25}個は管理者にお問い合わせください。",
                    inline=False
                )
            
            embed.set_footer(text="※ このメッセージはあなたにのみ表示されています")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # 元のメッセージを更新
            confirm_embed = discord.Embed(
                title="✅ 引き換え完了",
                description=f"{self.user.mention} が{len(accounts)}個のアカウント交換券を引き換えました。",
                color=discord.Color.green()
            )
            confirm_embed.set_footer(text="アカウント情報は本人にのみ送信されました")
            
            self.clear_items()
            await interaction.message.edit(embed=confirm_embed, view=self)
            
        except Exception as e:
            print(f"[ERROR] confirm_redeem: {e}")
            import traceback
            traceback.print_exc()
            
            embed = discord.Embed(
                title="エラー",
                description=f"引き換え処理中にエラーが発生しました。\n```{type(e).__name__}: {str(e)}```",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="キャンセル", style=discord.ButtonStyle.grey)
    async def cancel_redeem(self, interaction: discord.Interaction, button: discord.ui.Button):
        """引き換えをキャンセル"""
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "これはあなたの引き換えではありません。",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="キャンセル",
            description="アカウント引き換えをキャンセルしました。",
            color=discord.Color.grey()
        )
        
        self.clear_items()
        await interaction.response.edit_message(embed=embed, view=self)

