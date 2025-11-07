"""
サーバー情報パネルUI
カテゴリ別の情報表示とナビゲーションシステム
"""
import os
import discord
from discord.ui import Button, Select, View

import config
from utils.emojis import TIP1_EMOJI, TIP2_EMOJI, TIP3_EMOJI, TIP4_EMOJI
from utils.color import BASE_COLOR_CODE

# 画像ディレクトリ
INFO_IMAGE_DIR = "assets/info"


# ========================================
# 情報データ定義
# ========================================
SERVER_INFO = {
    "利用規約": {
        "title": "利用規約",
        "description": (
            "当サーバーをご利用いただく際は、以下の規約に同意したものとみなします。\n\n"
            "**1. 禁止事項**\n"
            "・不正行為、チート行為\n"
            "・複数アカウントの使用\n"
            "・サーバーの秩序を乱す行為\n"
            "・他ユーザーへの嫌がらせ\n\n"
            "**2. 免責事項**\n"
            "・ボットの不具合による損失の補償は行いません\n"
            "・予告なく仕様変更する場合があります\n\n"
            "**3. アカウント停止**\n"
            "・規約違反者はアカウントBANとなる場合があります"
        ),
        "color": BASE_COLOR_CODE,
        "image": None
    },
    "運営": {
        "title": "運営",
        "description": (
            "**運営チーム**\n"
            "運営チームは、Discord代行協会(daikou.com)が代行で運営しています。\n\n"
            "**Bot開発**\n"
            "Botの開発はりなぺんですが、サーバーには直接的に関わっていません。\n\n"
            "**サポート**\n"
            "お問い合わせは <@1324832394079109301> までお願いします。"
        ),
        "color": discord.Color.green(),
        "image": None
    },
    "お問い合わせ": {
        "title": "お問い合わせ",
        "description": (
            "ご不明な点やお困りのことがございましたら、お気軽にお問い合わせください。\n\n"
            "**お問い合わせ先**\n"
            "<@1324832394079109301> までDMまたはメンションでお願いします。\n\n"
            "**対応時間**\n"
            "基本的に24時間以内に返信いたします。"
        ),
        "color": discord.Color.purple(),
        "image": None
    }
}

GAME_INFO = {
    "フリップ": {
        "title": "フリップ",
        "description": (
            "コインの表か裏を当てるシンプルなゲームです。\n\n"
            "**遊び方**\n"
            "`?フリップ [賭け金]`\n\n"
            "**配当**\n"
            "・的中: 賭け金の2倍\n\n"
            "**最小/最大ベット**\n"
            "・最小: 100 PNC\n"
            "・最大: 100,000 PNC\n\n"
            "**例**\n"
            "`?フリップ 1000`"
        ),
        "color": discord.Color.gold(),
        "image": "flip.png"
    },
    "ダイス": {
        "title": "ダイス",
        "description": (
            "サイコロの出目を予想するゲームです。\n\n"
            "**遊び方**\n"
            "`?ダイス [賭け金]`\n\n"
            "**配当**\n"
            "・的中: 賭け金の6倍\n\n"
            "**最小/最大ベット**\n"
            "・最小: 100 PNC\n"
            "・最大: 100,000 PNC\n\n"
            "**例**\n"
            "`?ダイス 1000`"
        ),
        "color": discord.Color.red(),
        "image": "dice.png"
    },
    "ブラックジャック": {
        "title": "ブラックジャック",
        "description": (
            "ディーラーと対戦するカードゲームです。\n\n"
            "**遊び方**\n"
            "`?bj [賭け金]`\n\n"
            "**ルール**\n"
            "・21に近い方が勝ち\n"
            "・21を超えたら負け（バースト）\n"
            "・Aは1または11として数える\n\n"
            "**配当**\n"
            "・勝利: 賭け金の2倍\n"
            "・ブラックジャック: 賭け金の2.5倍\n"
            "・引き分け: 賭け金返却\n\n"
            "**最小/最大ベット**\n"
            "・最小: 1,000 PNC\n"
            "・最大: 100,000 PNC"
        ),
        "color": discord.Color.dark_blue(),
        "image": "blackjack.png"
    },
    "マインズ": {
        "title": "マインズ",
        "description": (
            "地雷を避けながら宝石を集めるゲームです。\n\n"
            "**遊び方**\n"
            "`?マインズ [賭け金] [地雷数]`\n\n"
            "**ルール**\n"
            "・5×5のグリッドから安全なマスを選択\n"
            "・地雷を踏むとゲームオーバー\n"
            "・キャッシュアウトで配当確定\n\n"
            "**配当**\n"
            "・開けたマスの数に応じて増加\n"
            "・地雷の数が多いほど倍率上昇\n\n"
            "**最小/最大ベット**\n"
            "・最小: 100 PNC\n"
            "・最大: 100,000 PNC"
        ),
        "color": discord.Color.orange(),
        "image": "mines.png"
    },
    "じゃんけん": {
        "title": "じゃんけん(現在停止中)",
        "description": (
            "ボットとじゃんけん勝負！\n\n"
            "**遊び方**\n"
            "`?じゃんけん [賭け金]`\n\n"
            "**配当**\n"
            "・勝利: 賭け金の2倍\n"
            "・引き分け: 賭け金返却\n\n"
            "**最小/最大ベット**\n"
            "・最小: 100 PNC\n"
            "・最大: 100,000 PNC\n\n"
            "**例**\n"
            "`?じゃんけん 1000`"
        ),
        "color": discord.Color.teal(),
        "image": "rps.png"
    }
}

COMMAND_INFO = {
    "基本コマンド": {
        "title": "基本コマンド",
        "description": (
            "**残高確認**\n"
            "`?残高` - 現在の残高を確認\n\n"
            "**送金**\n"
            "`?送金 @ユーザー [金額]` - 他のユーザーに送金\n\n"
            "**景品**\n"
            "`?交換` - PNC残高を景品に交換\n"
            "`?ポケット` - 景品ポケットの中身を確認\n"
            "`?引換` - アカウント交換券を実際のアカウントに引き換え"
        ),
        "color": BASE_COLOR_CODE,
        "image": None
    },
    "ゲームコマンド": {
        "title": "ゲームコマンド",
        "description": (
            "**フリップ（コインフリップ）**\n"
            "`?フリップ [賭け金]`\n"
            "最小: 100 PNC / 配当: 2倍\n\n"
            "**ダイス**\n"
            "`?ダイス [賭け金]`\n"
            "最小: 100 PNC / 配当: 6倍\n\n"
            "**ブラックジャック**\n"
            "`?bj [賭け金]`\n"
            "最小: 1,000 PNC / 配当: 2倍〜2.5倍\n\n"
            "**マインズ**\n"
            "`?マインズ [賭け金] [地雷数]`\n"
            "最小: 100 PNC / 配当: 変動"
        ),
        "color": BASE_COLOR_CODE,
        "image": None
    }
}


# ========================================
# ビューとコンポーネント
# ========================================
class InfoPanelView(View):
    """情報パネルのメインビュー"""
    
    def __init__(self):
        super().__init__(timeout=None)
        
        # 情報表示ボタン
        show_button = Button(
            label="情報",
            style=discord.ButtonStyle.secondary,
            custom_id="info_panel:show",
        )
        show_button.callback = self.show_info
        self.add_item(show_button)
    
    async def show_info(self, interaction: discord.Interaction):
        """情報パネルを表示"""
        embed = discord.Embed(
            title="情報パネル",
            description="下のメニューからカテゴリを選択してください",
            color=BASE_COLOR_CODE
        )
        
        view = InfoNavigationView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class InfoNavigationView(View):
    """情報ナビゲーション用ビュー"""
    
    def __init__(self, current_category: str = None, current_pages: list = None, current_page: int = 0):
        super().__init__(timeout=300)
        self.current_category = current_category
        self.current_pages = current_pages or []
        self.current_page = current_page
        
        # カテゴリ選択セレクトメニュー
        category_select = Select(
            placeholder="カテゴリを選択...",
            custom_id="category_select",
            options=[
                discord.SelectOption(
                    label="サーバー", 
                    value="server", 
                    emoji=TIP1_EMOJI,
                    default=(current_category == "server")
                ),
                discord.SelectOption(
                    label="ゲーム", 
                    value="games", 
                    emoji=TIP2_EMOJI,
                    default=(current_category == "games")
                ),
                discord.SelectOption(
                    label="景品", 
                    value="prizes", 
                    emoji=TIP3_EMOJI,
                    default=(current_category == "prizes")
                ),
                discord.SelectOption(
                    label="コマンド", 
                    value="commands", 
                    emoji=TIP4_EMOJI,
                    default=(current_category == "commands")
                )
            ]
        )
        category_select.callback = self.category_selected
        self.add_item(category_select)
        
        # 詳細選択セレクトメニュー（カテゴリ選択後に有効化）
        self.detail_select = Select(
            placeholder="まずカテゴリを選択してください",
            custom_id="detail_select",
            disabled=True,
            options=[discord.SelectOption(label="選択してください", value="none")]
        )
        self.detail_select.callback = self.detail_selected
        self.add_item(self.detail_select)
        
        # ページネーションボタン（複数ページがある場合のみ表示）
        if len(self.current_pages) > 1:
            prev_button = Button(
                label="前へ",
                style=discord.ButtonStyle.secondary,
                custom_id="prev_page",
                disabled=self.current_page == 0,
                emoji="◀️"
            )
            prev_button.callback = self.prev_page
            self.add_item(prev_button)
            
            next_button = Button(
                label="次へ",
                style=discord.ButtonStyle.secondary,
                custom_id="next_page",
                disabled=self.current_page >= len(self.current_pages) - 1,
                emoji="▶️"
            )
            next_button.callback = self.next_page
            self.add_item(next_button)
        
        # トップに戻るセレクトメニュー
        back_select = Select(
            placeholder="トップに戻る",
            custom_id="back_select",
            options=[
                discord.SelectOption(label="トップに戻る", value="back_to_top")
            ]
        )
        back_select.callback = self.back_to_top
        self.add_item(back_select)
    
    async def category_selected(self, interaction: discord.Interaction):
        """カテゴリが選択された"""
        category = interaction.data["values"][0]
        self.current_category = category
        
        # 詳細選択メニューを更新
        if category == "server":
            options = [
                discord.SelectOption(label="利用規約", value="利用規約"),
                discord.SelectOption(label="運営", value="運営"),
                discord.SelectOption(label="お問い合わせ", value="お問い合わせ")
            ]
            # サーバー情報の項目を表示
            server_items = "\n".join([f"・{item}" for item in SERVER_INFO.keys()])
            embed = discord.Embed(
                title=f"{TIP1_EMOJI} サーバー",
                description=f"詳細を選択してください\n\n{server_items}",
                color=BASE_COLOR_CODE
            )
            
        elif category == "games":
            options = [
                discord.SelectOption(label="フリップ", value="フリップ"),
                discord.SelectOption(label="ダイス", value="ダイス"),
                discord.SelectOption(label="ブラックジャック", value="ブラックジャック"),
                discord.SelectOption(label="マインズ", value="マインズ"),
                discord.SelectOption(label="じゃんけん", value="じゃんけん")
            ]
            # ゲーム情報の項目を表示
            game_items = "\n".join([f"・{item}" for item in GAME_INFO.keys()])
            embed = discord.Embed(
                title=f"{TIP2_EMOJI} ゲーム",
                description=f"詳細を選択してください\n\n{game_items}",
                color=BASE_COLOR_CODE
            )
            
        elif category == "prizes":
            # 景品についてを選択した場合は直接表示
            admin_user_id = config.ADMIN_USER_ID if config.ADMIN_USER_ID else "運営"
            embed = discord.Embed(
                title=f"{TIP3_EMOJI} 景品",
                description=f"皆さん景品に関するご質問は、<@{admin_user_id}>に聞いてます。\n\nPNCから景品への交換は `?交換` コマンドで行えます。",
                color=discord.Color.gold()
            )
            
            view = InfoNavigationView(self.current_category, self.current_pages, self.current_page)
            # 景品選択時も画像をクリア
            await interaction.response.edit_message(embed=embed, attachments=[], view=view)
            return
        
        elif category == "commands":
            options = [
                discord.SelectOption(label="基本コマンド", value="基本コマンド"),
                discord.SelectOption(label="ゲームコマンド", value="ゲームコマンド")
            ]
            # コマンド情報の項目を表示
            command_items = "\n".join([f"・{item}" for item in COMMAND_INFO.keys()])
            embed = discord.Embed(
                title=f"{TIP4_EMOJI} コマンド",
                description=f"詳細を選択してください\n\n{command_items}",
                color=BASE_COLOR_CODE
            )
            
        else:
            options = [discord.SelectOption(label="選択してください", value="none")]
            embed = discord.Embed(
                title="情報パネル",
                description="カテゴリを選択してください",
                color=BASE_COLOR_CODE
            )
        
        # 新しいビューを作成して更新
        view = InfoNavigationView(self.current_category, self.current_pages, self.current_page)
        view.detail_select.options = options
        view.detail_select.disabled = False
        view.detail_select.placeholder = "詳細を選択..."
        
        # カテゴリ選択時は画像をクリア
        await interaction.response.edit_message(embed=embed, attachments=[], view=view)
    
    async def detail_selected(self, interaction: discord.Interaction):
        """詳細が選択された"""
        detail = interaction.data["values"][0]
        
        # 情報を取得
        if self.current_category == "server":
            info = SERVER_INFO.get(detail)
            if info:
                embed = discord.Embed(
                    title=info["title"],
                    description=info["description"],
                    color=info["color"]
                )
                view = InfoNavigationView(self.current_category, [detail], 0)
                # 詳細選択メニューを再設定
                view.detail_select.options = [
                    discord.SelectOption(label="利用規約", value="利用規約"),
                    discord.SelectOption(label="運営", value="運営"),
                    discord.SelectOption(label="お問い合わせ", value="お問い合わせ")
                ]
                view.detail_select.disabled = False
                view.detail_select.placeholder = "詳細を選択..."
                # サーバー情報は画像なしなので、attachments を空にして画像をクリア
                await interaction.response.edit_message(embed=embed, attachments=[], view=view)
        
        elif self.current_category == "games":
            info = GAME_INFO.get(detail)
            if info:
                embed = discord.Embed(
                    title=info["title"],
                    description=info["description"],
                    color=info["color"]
                )
                
                # 画像ファイルがある場合は添付
                image_file = None
                if info.get("image"):
                    image_path = os.path.join(INFO_IMAGE_DIR, info["image"])
                    if os.path.exists(image_path):
                        image_file = discord.File(image_path, filename=info["image"])
                        embed.set_image(url=f"attachment://{info['image']}")
                
                view = InfoNavigationView(self.current_category, [detail], 0)
                # 詳細選択メニューを再設定
                view.detail_select.options = [
                    discord.SelectOption(label="フリップ", value="フリップ"),
                    discord.SelectOption(label="ダイス", value="ダイス"),
                    discord.SelectOption(label="ブラックジャック", value="ブラックジャック"),
                    discord.SelectOption(label="マインズ", value="マインズ"),
                    discord.SelectOption(label="じゃんけん", value="じゃんけん")
                ]
                view.detail_select.disabled = False
                view.detail_select.placeholder = "詳細を選択..."
                
                # 画像がある場合は attachments に含める
                if image_file:
                    await interaction.response.edit_message(embed=embed, attachments=[image_file], view=view)
                else:
                    await interaction.response.edit_message(embed=embed, view=view)
        
        elif self.current_category == "commands":
            info = COMMAND_INFO.get(detail)
            if info:
                embed = discord.Embed(
                    title=info["title"],
                    description=info["description"],
                    color=info["color"]
                )
                view = InfoNavigationView(self.current_category, [detail], 0)
                # 詳細選択メニューを再設定
                view.detail_select.options = [
                    discord.SelectOption(label="基本コマンド", value="基本コマンド"),
                    discord.SelectOption(label="ゲームコマンド", value="ゲームコマンド")
                ]
                view.detail_select.disabled = False
                view.detail_select.placeholder = "詳細を選択..."
                # コマンド情報は画像なしなので、attachments を空にして画像をクリア
                await interaction.response.edit_message(embed=embed, attachments=[], view=view)
    
    async def prev_page(self, interaction: discord.Interaction):
        """前のページへ"""
        if self.current_page > 0:
            self.current_page -= 1
            # ページの内容を更新
            # TODO: 実装
            await interaction.response.defer()
    
    async def next_page(self, interaction: discord.Interaction):
        """次のページへ"""
        if self.current_page < len(self.current_pages) - 1:
            self.current_page += 1
            # ページの内容を更新
            # TODO: 実装
            await interaction.response.defer()
    
    async def back_to_top(self, interaction: discord.Interaction):
        """トップページに戻る"""
        embed = discord.Embed(
            title="情報パネル",
            description="下のメニューからカテゴリを選択してください",
            color=BASE_COLOR_CODE
        )
        
        view = InfoNavigationView()
        # トップに戻る時も画像をクリア
        await interaction.response.edit_message(embed=embed, attachments=[], view=view)


# ========================================
# パネル送信関数
# ========================================
async def send_info_panel(bot):
    """情報パネルを指定チャンネルに送信"""
    if not config.INFO_PANEL_CHANNEL_ID:
        print("[INFO] INFO_PANEL_CHANNEL_ID が設定されていないため、情報パネルを送信しません。")
        return
    
    channel = bot.get_channel(config.INFO_PANEL_CHANNEL_ID)
    if not channel:
        print(f"[ERROR] チャンネル {config.INFO_PANEL_CHANNEL_ID} が見つかりません。")
        return
    
    # 既存のメッセージを削除（最新10件をチェック）
    async for message in channel.history(limit=10):
        if message.author == bot.user:
            try:
                await message.delete()
            except:
                pass
    
    view = InfoPanelView()
    await channel.send(view=view)
    print(f"[INFO] 情報パネルをチャンネル {config.INFO_PANEL_CHANNEL_ID} に送信しました。")

