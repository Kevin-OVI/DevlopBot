from typing import Optional, Union

import nextcord
from nextcord.ext import application_checks

from cache_data import cache_return
from discord_utils import embed_message, has_guild_permissions
from variables import bot, discord_variables, embed_color


def validation_embed(message, title=nextcord.Embed.Empty):
	return embed_message("<:oui:988807617654702140> " + message, embed_color, title)


def error_embed(message, title=nextcord.Embed.Empty):
	return embed_message(":x: " + message, embed_color, title)


def question_embed(message, title=nextcord.Embed.Empty):
	return embed_message("❓ " + message, embed_color, title)


def normal_embed(message, title=nextcord.Embed.Empty):
	return embed_message(message, embed_color, title)


@cache_return()
def get_id_str(obj: Optional[Union[str, int, nextcord.abc.Snowflake]]) -> str:
	if isinstance(obj, nextcord.abc.Snowflake):
		return str(obj.id)
	elif isinstance(obj, int):
		return str(obj)
	return obj


@cache_return(1800)
def get_member(obj: Union[str, int, nextcord.abc.Snowflake]) -> nextcord.Member:
	if isinstance(obj, str):
		return discord_variables.main_guild.get_member(int(obj))
	if isinstance(obj, int):
		return discord_variables.main_guild.get_member(obj)
	return discord_variables.main_guild.get_member(obj.id)


@cache_return(1800)
def get_textchannel(obj: Union[str, int, nextcord.abc.Snowflake]) -> nextcord.TextChannel:
	if isinstance(obj, str):
		return discord_variables.main_guild.get_channel(int(obj))
	if isinstance(obj, int):
		return discord_variables.main_guild.get_channel(obj)
	return discord_variables.main_guild.get_channel(obj.id)


def send_log(message, title, fields=None):
	embed = normal_embed(message, title)
	if fields:
		for name, value in fields.items():
			embed.add_field(name=name + " :", value=value, inline=False)
	bot.loop.create_task(discord_variables.logs_channel.send(embed=embed, allowed_mentions=nextcord.AllowedMentions.none()))


def is_moderator(member):
	return discord_variables.moderator_role in member.roles or has_guild_permissions(member, administrator=True)


def check_is_moderator():
	return application_checks.check(lambda interaction: is_moderator(interaction.user))


def is_user_on_guild(user):
	return get_member(user) is not None
