"""
景品交換コマンド
PNC残高を景品に交換します（直接換金ではなく景品交換方式）
"""
import discord

from database.db import (
    get_user_balance,
    update_user_balance,
    users_collection,
    get_prize_pocket,
    add_prizes_to_pocket,
    get_carry_over_points,
    clear_carry_over_points,
    add_carry_over_points
)
from utils.embed_factory import EmbedFactory
from utils.pnc import calculate_prize_pnc, calculate_prizes_from_balance, calculate_account_exchange_pnc
from utils.emojis import PNC_EMOJI_STR, CLOSED_EMOJI
from utils.logs import send_exchange_log, log_financial_transaction
from config import (
    EXCHANGE_ENABLED,
    PRIZE_LARGE_JPY,
    PRIZE_MEDIUM_JPY,
    PRIZE_SMALL_JPY,
    ACCOUNT_EXCHANGE_JPY
)


async def on_exchange_command(message: discord.Message) -> None:
    """
    景品交換コマンドハンドラー
    
    Args:
        message: Discordメッセージオブジェクト
    """
    # 機能が有効かチェック
    if not EXCHANGE_ENABLED:
        embed = discord.Embed(
            title=f"{CLOSED_EMOJI} 景品交換所",
            description=(
                "**本日は定休日となっております**\n\n"
                "景品交換機能は現在ご利用いただけません。\n"
                "ご不便をおかけして申し訳ございません。"
            ),
            color=discord.Color.from_rgb(150, 150, 150)
        )
        
        embed.add_field(
            name="ご利用可能なサービス",
            value=(
                "• 残高確認（`?残高`）\n"
                "• ゲームプレイ（`?フリップ`, `?ダイス`等）\n"
                "• 送金（`?送金`）\n"
                "• ポケット確認（`?ポケット`）"
            ),
            inline=False
        )
        
        embed.set_footer(text="営業再開までお待ちください")
        
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
        
        # 現在の残高を取得
        balance = get_user_balance(user_id)
        
        # 繰越ポイントを取得して加算
        carry_over = get_carry_over_points(user_id)
        total_balance = balance + carry_over
        
        if total_balance <= 0:
            embed = discord.Embed(
                title="残高不足",
                description="交換可能な残高がありません。",
                color=discord.Color.red()
            )
            await message.channel.send(embed=embed)
            return
        
        # 景品の内訳を計算（繰越含む）
        prizes = calculate_prizes_from_balance(total_balance)
        
        # 最小景品を計算
        small_pnc = calculate_prize_pnc(PRIZE_SMALL_JPY)
        
        # 交換可能な景品が何もない場合
        if prizes["large"] == 0 and prizes["medium"] == 0 and prizes["small"] == 0:
            embed = discord.Embed(
                title="交換不可",
                description=(
                    f"残高が不足しています。\n\n"
                    f"**現在の残高:** {PNC_EMOJI_STR}`{balance:,}`\n"
                    f"**繰越ポイント:** {PNC_EMOJI_STR}`{carry_over:,}`\n"
                    f"**合計:** {PNC_EMOJI_STR}`{total_balance:,}`\n\n"
                    f"最小の景品（小景品）には {PNC_EMOJI_STR}`{small_pnc:,}` が必要です。\n"
                    f"あと {PNC_EMOJI_STR}`{small_pnc - total_balance:,}` 必要です。"
                ),
                color=discord.Color.orange()
            )
            embed.set_footer(text="ゲームで残高を増やしてから再度お試しください")
            await message.channel.send(embed=embed)
            return
        
        # 交換前の確認メッセージ
        large_pnc = calculate_prize_pnc(PRIZE_LARGE_JPY)
        medium_pnc = calculate_prize_pnc(PRIZE_MEDIUM_JPY)
        small_pnc = calculate_prize_pnc(PRIZE_SMALL_JPY)
        
        total_used = (
            prizes["large"] * large_pnc +
            prizes["medium"] * medium_pnc +
            prizes["small"] * small_pnc
        )
        
        # アカウント交換が可能か確認（余りが800PNC以上）
        account_exchange_pnc = calculate_account_exchange_pnc()
        can_exchange_account = prizes["remainder"] >= account_exchange_pnc
        
        # 確認Embed作成
        embed = discord.Embed(
            title="景品交換確認",
            description=(
                f"現在の残高: {PNC_EMOJI_STR}`{balance:,}`\n"
                f"繰越ポイント: {PNC_EMOJI_STR}`{carry_over:,}`\n"
                f"**合計: {PNC_EMOJI_STR}`{total_balance:,}`**"
            ) if carry_over > 0 else f"現在の残高: {PNC_EMOJI_STR}`{balance:,}`",
            color=discord.Color.gold()
        )
        
        if prizes["large"] > 0:
            embed.add_field(
                name="🟡 大景品",
                value=f"`{prizes['large']}個` （{PRIZE_LARGE_JPY:,}円相当 × {prizes['large']}）",
                inline=False
            )
        
        if prizes["medium"] > 0:
            embed.add_field(
                name="🔵 中景品",
                value=f"`{prizes['medium']}個` （{PRIZE_MEDIUM_JPY:,}円相当 × {prizes['medium']}）",
                inline=False
            )
        
        if prizes["small"] > 0:
            embed.add_field(
                name="🟢 小景品",
                value=f"`{prizes['small']}個` （{PRIZE_SMALL_JPY:,}円相当 × {prizes['small']}）",
                inline=False
            )
        
        if prizes["remainder"] > 0:
            remainder_text = f"{PNC_EMOJI_STR}`{prizes['remainder']:,}`"
            if can_exchange_account:
                account_count = prizes["remainder"] // account_exchange_pnc
                remainder_after_account = prizes["remainder"] % account_exchange_pnc
                remainder_text += f"\n\n**🎫 アカウント交換可能:**\n"
                remainder_text += f"`{account_count}個` 交換可能（{PNC_EMOJI_STR}`{account_exchange_pnc:,}` / 個）\n"
                remainder_text += f"交換後の余り: {PNC_EMOJI_STR}`{remainder_after_account:,}`"
            
            embed.add_field(
                name="📝 余りPNC",
                value=remainder_text,
                inline=False
            )
        
        embed.add_field(
            name="使用PNC",
            value=f"{PNC_EMOJI_STR}`{total_used:,}`",
            inline=True
        )
        
        embed.add_field(
            name="交換後の残高",
            value=f"{PNC_EMOJI_STR}`0`",
            inline=True
        )
        
        # アカウント交換可能な場合は追加情報を表示
        if can_exchange_account:
            embed.set_footer(text="以下のボタンで交換を確定してください。アカウント交換の確認は次のステップで行います。")
        else:
            embed.set_footer(text="以下のボタンで交換を確定してください")
        
        # 確認ビュー作成
        view = ExchangeConfirmView(
            user=message.author,
            balance=balance,
            carry_over=carry_over,
            total_balance=total_balance,
            prizes=prizes,
            total_used=total_used,
            can_exchange_account=can_exchange_account
        )
        await message.channel.send(embed=embed, view=view)
        
    except Exception as e:
        print(f"[ERROR] on_exchange_command: {e}")
        embed = EmbedFactory.error("景品交換中にエラーが発生しました。")
        await message.channel.send(embed=embed)


class ExchangeConfirmView(discord.ui.View):
    """景品交換確認ビュー"""
    
    def __init__(
        self,
        user: discord.User,
        balance: int,
        carry_over: int,
        total_balance: int,
        prizes: dict[str, int],
        total_used: int,
        can_exchange_account: bool
    ):
        super().__init__(timeout=60)
        self.user = user
        self.balance = balance
        self.carry_over = carry_over
        self.total_balance = total_balance
        self.prizes = prizes
        self.total_used = total_used
        self.can_exchange_account = can_exchange_account
    
    @discord.ui.button(label="交換する", style=discord.ButtonStyle.green)
    async def confirm_exchange(self, interaction: discord.Interaction, button: discord.ui.Button):
        """交換を確定"""
        if interaction.user.id != self.user.id:
            embed = discord.Embed(
                description="これはあなたの交換ではありません。",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # アカウント交換可能な場合は、次のステップへ
        if self.can_exchange_account:
            # アカウント交換確認ビューを表示
            account_exchange_pnc = calculate_account_exchange_pnc()
            account_count = self.prizes["remainder"] // account_exchange_pnc
            remainder_after = self.prizes["remainder"] % account_exchange_pnc
            
            embed = discord.Embed(
                title="🎫 アカウント交換確認",
                description=(
                    f"余りPNC {PNC_EMOJI_STR}`{self.prizes['remainder']:,}` から\n"
                    f"**{account_count}個のアカウント**と交換できます。\n\n"
                    f"交換後の余り: {PNC_EMOJI_STR}`{remainder_after:,}`"
                ),
                color=discord.Color.blue()
            )
            embed.add_field(
                name="オプション1: アカウントと交換する",
                value=f"🎫 アカウント `{account_count}個` をポケットに追加\n余り {PNC_EMOJI_STR}`{remainder_after:,}` は繰越ポイントへ",
                inline=False
            )
            embed.add_field(
                name="オプション2: 繰越ポイントにする",
                value=f"📌 全額 {PNC_EMOJI_STR}`{self.prizes['remainder']:,}` を繰越ポイントへ\n次回の景品交換時に使用できます",
                inline=False
            )
            embed.set_footer(text="※ 繰越ポイントはアカウント交換には使えません（景品のみ）")
            
            view = AccountExchangeView(
                user=self.user,
                balance=self.balance,
                carry_over=self.carry_over,
                prizes=self.prizes,
                total_used=self.total_used,
                remainder=self.prizes["remainder"],
                account_count=account_count,
                remainder_after=remainder_after
            )
            
            # 元のビューを無効化
            self.clear_items()
            await interaction.response.edit_message(embed=embed, view=view)
            return
        
        # アカウント交換不可の場合は通常の景品交換
        await self._complete_exchange(interaction, account_exchange_count=0, carry_over_amount=self.prizes["remainder"])
    
    async def _complete_exchange(
        self,
        interaction: discord.Interaction,
        account_exchange_count: int,
        carry_over_amount: int
    ):
        """
        景品交換を完了
        
        Args:
            interaction: Discord Interaction
            account_exchange_count: 交換するアカウント数
            carry_over_amount: 繰越ポイント額
        """
        # 残高を減らす（元の残高のみ、繰越ポイント分も含めて）
        update_user_balance(self.user.id, -self.balance)
        
        # 繰越ポイントをクリア
        if self.carry_over > 0:
            clear_carry_over_points(self.user.id)
        
        # 景品をポケットに追加
        add_prizes_to_pocket(
            user_id=self.user.id,
            large=self.prizes["large"],
            medium=self.prizes["medium"],
            small=self.prizes["small"],
            accounts=account_exchange_count  # アカウント交換券
        )
        
        # 繰越ポイントを追加
        if carry_over_amount > 0:
            add_carry_over_points(self.user.id, carry_over_amount)
        
        # 金銭トランザクションとして記録
        log_financial_transaction(
            user_id=self.user.id,
            transaction_type="exchange",
            amount=self.balance + self.carry_over,
            net_amount=0  # 景品に変換されるため残高は0
        )
        
        # 交換ログを送信
        try:
            await send_exchange_log(
                user=self.user,
                used_pnc=self.balance,
                large_count=self.prizes["large"],
                medium_count=self.prizes["medium"],
                small_count=self.prizes["small"],
                account_count=account_exchange_count,
                carry_over_amount=carry_over_amount,
                had_carry_over=self.carry_over
            )
        except Exception as e:
            print(f"[ERROR] Failed to send exchange log: {e}")
        
        # 完了メッセージ
        embed = discord.Embed(
            title="✅ 景品交換完了",
            description="景品があなたのポケットに追加されました！",
            color=discord.Color.green()
        )
        
        if self.prizes["large"] > 0:
            embed.add_field(
                name="🟡 大景品",
                value=f"`{self.prizes['large']}個` 追加",
                inline=True
            )
        
        if self.prizes["medium"] > 0:
            embed.add_field(
                name="🔵 中景品",
                value=f"`{self.prizes['medium']}個` 追加",
                inline=True
            )
        
        if self.prizes["small"] > 0:
            embed.add_field(
                name="🟢 小景品",
                value=f"`{self.prizes['small']}個` 追加",
                inline=True
            )
        
        if account_exchange_count > 0:
            embed.add_field(
                name="🎫 アカウント交換",
                value=f"`{account_exchange_count}個` 追加",
                inline=False
            )
        
        if carry_over_amount > 0:
            embed.add_field(
                name="📌 繰越ポイント",
                value=f"{PNC_EMOJI_STR}`{carry_over_amount:,}` を繰越（次回の景品交換時に使用可能）",
                inline=False
            )
        
        current_balance = get_user_balance(self.user.id)
        embed.add_field(
            name="現在の残高",
            value=f"{PNC_EMOJI_STR}`{current_balance:,}`",
            inline=False
        )
        
        embed.set_footer(text="?ポケット コマンドで景品を確認できます")
        
        # ボタンを無効化
        self.clear_items()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="キャンセル", style=discord.ButtonStyle.grey)
    async def cancel_exchange(self, interaction: discord.Interaction, button: discord.ui.Button):
        """交換をキャンセル"""
        if interaction.user.id != self.user.id:
            embed = discord.Embed(
                description="これはあなたの交換ではありません。",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        embed = discord.Embed(
            title="キャンセル",
            description="景品交換をキャンセルしました。",
            color=discord.Color.grey()
        )
        
        # ボタンを無効化
        self.clear_items()
        await interaction.response.edit_message(embed=embed, view=self)


class AccountExchangeView(discord.ui.View):
    """アカウント交換確認ビュー"""
    
    def __init__(
        self,
        user: discord.User,
        balance: int,
        carry_over: int,
        prizes: dict[str, int],
        total_used: int,
        remainder: int,
        account_count: int,
        remainder_after: int
    ):
        super().__init__(timeout=60)
        self.user = user
        self.balance = balance
        self.carry_over = carry_over
        self.prizes = prizes
        self.total_used = total_used
        self.remainder = remainder
        self.account_count = account_count
        self.remainder_after = remainder_after
    
    @discord.ui.button(label="アカウントと交換する", style=discord.ButtonStyle.primary)
    async def exchange_account(self, interaction: discord.Interaction, button: discord.ui.Button):
        """アカウントと交換"""
        if interaction.user.id != self.user.id:
            embed = discord.Embed(
                description="これはあなたの交換ではありません。",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # 景品交換を完了（アカウント交換あり）
        await self._complete_with_account_exchange(interaction)
    
    @discord.ui.button(label="繰越ポイントにする", style=discord.ButtonStyle.secondary)
    async def carry_over_points(self, interaction: discord.Interaction, button: discord.ui.Button):
        """繰越ポイントにする"""
        if interaction.user.id != self.user.id:
            embed = discord.Embed(
                description="これはあなたの交換ではありません。",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # 景品交換を完了（アカウント交換なし、全額繰越）
        await self._complete_with_carry_over(interaction)
    
    async def _complete_with_account_exchange(self, interaction: discord.Interaction):
        """アカウント交換ありで完了"""
        # 残高を減らす
        update_user_balance(self.user.id, -self.balance)
        
        # 繰越ポイントをクリア
        if self.carry_over > 0:
            clear_carry_over_points(self.user.id)
        
        # 景品をポケットに追加
        add_prizes_to_pocket(
            user_id=self.user.id,
            large=self.prizes["large"],
            medium=self.prizes["medium"],
            small=self.prizes["small"],
            accounts=self.account_count  # アカウント交換券
        )
        
        # 余りを繰越ポイントに
        if self.remainder_after > 0:
            add_carry_over_points(self.user.id, self.remainder_after)
        
        # 金銭トランザクションとして記録
        log_financial_transaction(
            user_id=self.user.id,
            transaction_type="exchange",
            amount=self.balance + self.carry_over,
            net_amount=0  # 景品に変換されるため残高は0
        )
        
        # 完了メッセージ
        embed = discord.Embed(
            title="✅ 景品交換完了",
            description="景品とアカウントがポケットに追加されました！",
            color=discord.Color.green()
        )
        
        if self.prizes["large"] > 0:
            embed.add_field(
                name="🟡 大景品",
                value=f"`{self.prizes['large']}個` 追加",
                inline=True
            )
        
        if self.prizes["medium"] > 0:
            embed.add_field(
                name="🔵 中景品",
                value=f"`{self.prizes['medium']}個` 追加",
                inline=True
            )
        
        if self.prizes["small"] > 0:
            embed.add_field(
                name="🟢 小景品",
                value=f"`{self.prizes['small']}個` 追加",
                inline=True
            )
        
        embed.add_field(
            name="🎫 アカウント交換",
            value=f"`{self.account_count}個` 追加（¥{ACCOUNT_EXCHANGE_JPY:,}相当 × {self.account_count}）",
            inline=False
        )
        
        if self.remainder_after > 0:
            embed.add_field(
                name="📌 繰越ポイント",
                value=f"{PNC_EMOJI_STR}`{self.remainder_after:,}` を繰越",
                inline=False
            )
        
        current_balance = get_user_balance(self.user.id)
        carry_over_total = get_carry_over_points(self.user.id)
        
        embed.add_field(
            name="現在の状態",
            value=f"残高: {PNC_EMOJI_STR}`{current_balance:,}`\n繰越: {PNC_EMOJI_STR}`{carry_over_total:,}`",
            inline=False
        )
        
        embed.set_footer(text="?ポケット コマンドで景品を確認できます")
        
        self.clear_items()
        await interaction.response.edit_message(embed=embed, view=self)
        
        # 交換ログを送信
        try:
            await send_exchange_log(
                user=self.user,
                used_pnc=self.balance,
                large_count=self.prizes["large"],
                medium_count=self.prizes["medium"],
                small_count=self.prizes["small"],
                account_count=self.account_count,
                carry_over_amount=self.remainder_after,
                had_carry_over=self.carry_over
            )
        except Exception as e:
            print(f"[ERROR] Failed to send exchange log: {e}")
    
    async def _complete_with_carry_over(self, interaction: discord.Interaction):
        """繰越ポイントありで完了（アカウント交換なし）"""
        # 残高を減らす
        update_user_balance(self.user.id, -self.balance)
        
        # 繰越ポイントをクリア
        if self.carry_over > 0:
            clear_carry_over_points(self.user.id)
        
        # 景品をポケットに追加（アカウント交換なし）
        add_prizes_to_pocket(
            user_id=self.user.id,
            large=self.prizes["large"],
            medium=self.prizes["medium"],
            small=self.prizes["small"],
            accounts=0  # アカウント交換しない
        )
        
        # 全額を繰越ポイントに
        add_carry_over_points(self.user.id, self.remainder)
        
        # 金銭トランザクションとして記録
        log_financial_transaction(
            user_id=self.user.id,
            transaction_type="exchange",
            amount=self.balance + self.carry_over,
            net_amount=0  # 景品に変換されるため残高は0
        )
        
        # 完了メッセージ
        embed = discord.Embed(
            title="✅ 景品交換完了",
            description="景品がポケットに追加され、余りは繰越ポイントになりました！",
            color=discord.Color.green()
        )
        
        if self.prizes["large"] > 0:
            embed.add_field(
                name="🟡 大景品",
                value=f"`{self.prizes['large']}個` 追加",
                inline=True
            )
        
        if self.prizes["medium"] > 0:
            embed.add_field(
                name="🔵 中景品",
                value=f"`{self.prizes['medium']}個` 追加",
                inline=True
            )
        
        if self.prizes["small"] > 0:
            embed.add_field(
                name="🟢 小景品",
                value=f"`{self.prizes['small']}個` 追加",
                inline=True
            )
        
        embed.add_field(
            name="📌 繰越ポイント",
            value=f"{PNC_EMOJI_STR}`{self.remainder:,}` を繰越（次回の景品交換時に使用可能）",
            inline=False
        )
        
        current_balance = get_user_balance(self.user.id)
        carry_over_total = get_carry_over_points(self.user.id)
        
        embed.add_field(
            name="現在の状態",
            value=f"残高: {PNC_EMOJI_STR}`{current_balance:,}`\n繰越: {PNC_EMOJI_STR}`{carry_over_total:,}`",
            inline=False
        )
        
        embed.set_footer(text="※ 繰越ポイントはアカウント交換には使えません（景品のみ）")
        
        self.clear_items()
        await interaction.response.edit_message(embed=embed, view=self)
        
        # 交換ログを送信
        try:
            await send_exchange_log(
                user=self.user,
                used_pnc=self.balance,
                large_count=self.prizes["large"],
                medium_count=self.prizes["medium"],
                small_count=self.prizes["small"],
                account_count=0,  # アカウント交換なし
                carry_over_amount=self.remainder,
                had_carry_over=self.carry_over
            )
        except Exception as e:
            print(f"[ERROR] Failed to send exchange log: {e}")

