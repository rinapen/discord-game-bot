"""
Discord Embed作成ユーティリティ
簡潔なEmbedオブジェクトの作成をサポートします
"""
from typing import Union
import discord


def create_embed(
    title: str,
    description: str,
    color: Union[discord.Color, int]
) -> discord.Embed:
    """
    Discord Embedを作成
    
    Args:
        title: Embedのタイトル
        description: Embedの説明文
        color: Embedの色（discord.Colorまたは16進数）
    
    Returns:
        discord.Embed: 作成されたEmbedオブジェクト
    """
    return discord.Embed(title=title, description=description, color=color)