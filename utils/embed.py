import discord

def create_embed(title, description, color):
    return discord.Embed(title=title, description=description, color=color)