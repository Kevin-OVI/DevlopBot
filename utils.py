from functools import wraps
from typing import Optional, Union

import nextcord
from nextcord.ext import application_checks

from cache_data import cache_return
from data_file import data, projects_data, save_json
from discord_utils import embed_message, has_guild_permissions, hidden_pin, try_send_dm

from variables import bot, discord_variables, embed_color, project_ignore_channels


def validation_embed(message, title=nextcord.Embed.Empty):
	return embed_message("<:oui:988807617654702140> " + message, embed_color, title)


def error_embed(message, title=nextcord.Embed.Empty):
	return embed_message(":x: " + message, embed_color, title)


def question_embed(message, title=nextcord.Embed.Empty):
	return embed_message("❓ " + message, embed_color, title)


def normal_embed(message, title=nextcord.Embed.Empty):
	return embed_message(message, embed_color, title)


async def create_project_start(interaction: nextcord.Interaction):
	user_data = data["projects"].get(str(interaction.user.id))
	max_projects = data["config"]["max-projects"]
	if len(user_data) >= max_projects:
		await interaction.response.send_message(embed=error_embed(f"Vous ne pouvez avoir que {max_projects} projects au maximum."), ephemeral=True)
		return
	from modals import ProjectTopicModal  # Éviter une importation circulaire
	await interaction.response.send_modal(ProjectTopicModal())


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


def generate_info_message(user, channel):
	user_id = get_id_str(user)
	channel_id = get_id_str(channel)

	project_data = projects_data[user_id][channel_id]
	embed = nextcord.Embed(description=project_data["description"], color=embed_color, title=project_data["name"])
	embed.add_field(name="Propriétaire", value=f"<@{user_id}>", inline=False)
	embed.add_field(name="Membres du projet", value=" ".join([f"<@{x}>" for x in (project_data["members"] + [user_id])]), inline=False)
	embed.set_footer(text="Merci de ne pas supprimer ce message.")
	return embed


async def send_info_message(user, channel):
	channel_obj = get_textchannel(channel)
	message = await channel_obj.send(embed=generate_info_message(user, channel))
	bot.loop.create_task(hidden_pin(message, reason="Épinglage du message d'informations"))
	return message


async def edit_info_message(user, channel):
	user_id = get_id_str(user)
	channel_id = get_id_str(channel)
	channel_obj = get_textchannel(channel)

	embed = generate_info_message(user_id, channel_id)
	project_data = data["projects"][user_id][channel_id]
	try:
		message = await channel_obj.fetch_message(project_data["info_message"])
		bot.loop.create_task(message.edit(embed=embed))
	except nextcord.errors.NotFound:
		message = await channel_obj.send("Ne vous ai-je pas dit de ne pas supprimer ce message ?", embed=embed)
		bot.loop.create_task(hidden_pin(message, reason="Épinglage du message d'informations"))
		project_data["info_message"] = message.id
		save_json()
	return message


@cache_return()
def is_project_channel(channel: nextcord.abc.GuildChannel):
	return channel.category in (discord_variables.projects_categ, discord_variables.revision_categ) and channel.id not in project_ignore_channels


@cache_return()
def find_project(channel):
	channel_id = get_id_str(channel)
	for user, projects in projects_data.items():
		if channel_id in projects:
			return user, projects[channel_id]


@cache_return()
def is_project_owner(user, channel):
	user_id = get_id_str(user)
	channel_id = get_id_str(channel)
	return channel_id in projects_data.get(user_id, {})


@cache_return()
def is_project_member(user, channel):
	user_id = get_id_str(user)
	if is_project_owner(user_id, channel):
		return True

	project = find_project(channel)[1]
	if project is None:
		return False
	return user_id in project["members"]


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


def check_is_project(func):
	@wraps(func)
	async def overwrite(interaction, *args, **kwargs):
		if not is_project_channel(interaction.channel):
			await interaction.response.send_message(embed=error_embed("La commande ne peut pas être exécutée ici."), ephemeral=True)
			return
		await func(interaction, *args, **kwargs)

	return overwrite


def check_project_owner(func):
	@check_is_project
	@wraps(func)
	async def overwrite(interaction, *args, **kwargs):
		if (not is_project_owner(interaction.user, interaction.channel)) and has_guild_permissions(interaction.user, administrator=False):
			await interaction.response.send_message(embed=error_embed("Vous devez être le propriétaire du projet pour effectuer cette action."), ephemeral=True)
			return
		return await func(interaction, *args, **kwargs)

	return overwrite


def check_project_member(func):
	@check_is_project
	@wraps(func)
	async def overwrite(interaction, *args, **kwargs):
		if (not is_project_member(interaction.user, interaction.channel)) and has_guild_permissions(interaction.user, administrator=False):
			await interaction.response.send_message(embed=error_embed("Vous devez être un membre du projet pour effectuer cette action."), ephemeral=True)
			return
		return await func(interaction, *args, **kwargs)

	return overwrite


async def unhold_for_review(interaction, owner_id, project_data):
	project_data["held_for_review"] = False
	save_json()
	overwrites = interaction.channel.overwrites
	try:
		del (overwrites[interaction.guild.default_role])
	except KeyError:
		pass
	try:
		del (overwrites[discord_variables.moderator_role])
	except KeyError:
		pass
	bot.loop.create_task(interaction.channel.edit(category=discord_variables.projects_categ, overwrites=overwrites, reason="Retrait du marquage comme `à examiner`"))
	bot.loop.create_task(try_send_dm(get_member(owner_id),
		embed=normal_embed(f"Le marquage de votre projet [{project_data['name']}]({interaction.channel.jump_url}) a été retiré.")))
	send_log(f"Le marquage `à examiner` du projet [{project_data['name']}]({interaction.channel.jump_url}) de <@{owner_id}> a été retiré par {interaction.user.mention}",
		"Retrait de mise en examen")
	if interaction.message:
		await interaction.message.edit(embed=validation_embed("Le marquage `à examiner` à été retiré du projet."), view=None)
	else:
		await interaction.response.send_message(embed=validation_embed("Le marquage `à examiner` à été retiré du projet."))
