import discord
from discord.ui import View, button
from database.db import (
    bot_state_collection,
    invites_collection,
    update_user_balance
)
import config
import datetime
from utils.emojis import PNC_EMOJI_STR, OK_EMOJI, NOTYET_EMOJI, GRAD_FACE, GERO_FACE
from utils.embed import create_embed
from database.db import get_user_balance

REWARD_PER_USER = 200

async def create_invite_for_user(guild: discord.Guild, user: discord.User):
    active_batch = invites_collection.find({
        "inviter_id": user.id,
        "used": False,
        "batch_active": True
    })

    active_list = list(active_batch)

    if len(active_list) >= 3:
        return None, "❌ 現在の発行枠を使い切るまで新しいリンクは作成できません。"

    if len(active_list) == 0:
        invites_collection.update_many(
            {"inviter_id": user.id, "batch_active": True},
            {"$set": {"batch_active": False}}
        )

    channel = guild.system_channel or guild.text_channels[0]
    invite = await channel.create_invite(max_uses=1, max_age=0, unique=True)

    invites_collection.insert_one({
        "invite_code": invite.code,
        "inviter_id": user.id,
        "used": False,
        "redeemed": False,
        "batch_active": True,
        "exists": True,
        "guild_id": guild.id,
        "timestamp": datetime.datetime.utcnow()
    })

    return invite.url, None

async def initialize_invite_cache(guild):
    invites = await guild.invites()
    invites_collection.update_many(
        {"guild_id": guild.id, "used": False},
        {"$set": {"exists": False}}
    )

    for inv in invites:
        invites_collection.update_one(
            {"invite_code": inv.code, "guild_id": guild.id},
            {
                "$set": {
                    "invite_code": inv.code,
                    "inviter_id": inv.inviter.id if inv.inviter else None,
                    "used": False,
                    "redeemed": False,
                    "exists": True,
                    "guild_id": guild.id,
                    "timestamp": datetime.datetime.utcnow()
                }
            },
            upsert=True
        )

async def check_invite_usage_diff(guild):
    current = await guild.invites()
    current_codes = {inv.code for inv in current}

    disappeared_invites = invites_collection.find({
        "guild_id": guild.id,
        "used": False,
        "exists": True,
        "invite_code": {"$nin": list(current_codes)}
    })

    for inv in disappeared_invites:
        invites_collection.update_one(
            {"_id": inv["_id"]},
            {"$set": {"used": True, "used_detected_at": datetime.datetime.utcnow()}}
        )
        if inv.get("inviter_id"):
            update_user_balance(inv["inviter_id"], REWARD_PER_USER)

class InvitePanelView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="🎟️ リンクを発行", style=discord.ButtonStyle.success)
    async def create_invite(self, interaction: discord.Interaction, button: discord.ui.Button):
        url, error = await create_invite_for_user(interaction.guild, interaction.user)

        if error:
            embed = create_embed("⚠️ 発行制限", error, discord.Color.orange())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # ✅ 発行成功時：ログを強制的に確認＆保存済みを明示
        invite_code = url.split("/")[-1]

        invites_collection.update_one(
            {"inviter_id": interaction.user.id, "invite_code": invite_code},
            {
                "$set": {
                    "guild_id": interaction.guild.id,
                    "log_registered": True,
                    "log_timestamp": datetime.datetime.utcnow()
                }
            }
        )

        embed = create_embed("✅ 招待リンクを発行しました", f"🔗 {url}", discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)


    @button(label="🔗 リンクを表示", style=discord.ButtonStyle.secondary)
    async def show_existing_invite(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        guild = interaction.guild

        # 🔄 使用済みリンクの強制チェック（差分更新）
        try:
            await check_invite_usage_diff(guild)
        except Exception as e:
            embed = create_embed("❌ 使用状況チェック失敗", f"`{type(e).__name__}: {e}`", discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # 📦 現在のバッチ（batch_active=True）のみ取得
        links = list(invites_collection.find({
            "inviter_id": user_id,
            "batch_active": True
        }))

        if not links:
            embed = create_embed("❌ 表示できるリンクがありません", "すでにすべてのリンクを使い切っているか、まだ発行していません。", discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        desc_lines = []
        for db_invite in links:
            code = db_invite["invite_code"]
            status_emoji = OK_EMOJI if db_invite.get("used") else NOTYET_EMOJI
            desc_lines.append(f"{status_emoji} https://discord.gg/{code}")

        desc = "\n".join(desc_lines)
        embed = create_embed("🔗 発行済みリンク一覧", desc, discord.Color.blurple())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @button(label="換金", style=discord.ButtonStyle.success)
    async def redeem_invites(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id

        # ⛔ 口座が存在しない場合は換金不可
        if get_user_balance(user_id) is None:
            embed = create_embed(
                "⛔ 口座未登録",
                "換金するにはまずPNC口座を開設してください。\n`$残高` コマンドで自動的に作成できます。",
                discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # ✅ 換金処理
        redeemed_total = 0
        for inv in invites_collection.find({"inviter_id": user_id, "used": True, "redeemed": {"$ne": True}}):
            update_user_balance(user_id, REWARD_PER_USER)
            invites_collection.update_one({"_id": inv["_id"]}, {"$set": {"redeemed": True}})
            redeemed_total += 1

        if redeemed_total == 0:
            embed = create_embed("💸 換金対象なし", "すでにすべての招待PNCを換金済みです。", discord.Color.dark_gray())
        else:
            reward = redeemed_total * REWARD_PER_USER
            embed = create_embed(
                "換金成功",
                f"新規招待 {redeemed_total}人 × {PNC_EMOJI_STR}`{REWARD_PER_USER}` = {PNC_EMOJI_STR}`{reward}` を付与しました。",
                discord.Color.gold()
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup_invite_panel(bot):
    channel = bot.get_channel(int(config.INVITE_PANEL_CHANNEL_ID))
    if not channel:
        print("❌ 招待リンクチャンネルが見つかりません")
        return

    previous = bot_state_collection.find_one({"key": "invite_panel"})
    if previous:
        try:
            old_msg = await channel.fetch_message(previous["message_id"])
            await old_msg.delete()
        except discord.NotFound:
            pass

    embed = create_embed(
        "招待リンクを作成",
        (
            f"## 招待1人ごとに\n"
            f"# {GRAD_FACE} {PNC_EMOJI_STR}`200` **GET**\n"
            f"### ボタンで管理できまちゅ{GERO_FACE}"
        ),
        discord.Color.green()
    )
    view = InvitePanelView()
    msg = await channel.send(embed=embed, view=view)

    bot_state_collection.update_one(
        {"key": "invite_panel"},
        {"$set": {"message_id": msg.id}},
        upsert=True
    )