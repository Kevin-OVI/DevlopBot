import nextcord

from data_file import data, projects_data, save_json
from utils import get_id_str, get_textchannel, normal_embed, send_log
from variables import bot, discord_variables, embed_color, project_member_perms, project_mute_perms, project_owner_perms


def task_project_perms(member, archive, do_not_save=False):
	member_id = get_id_str(member)
	save = False
	for owner_id, member_projects in projects_data.items():
		if member_id == owner_id:
			for channel_id, project_data in member_projects.items():
				if project_data["archived"] != archive:
					channel = get_textchannel(channel_id)
					if archive:
						bot.loop.create_task(channel.set_permissions(discord_variables.main_guild.default_role, send_messages=False, reason="Archivage du projet"))
						bot.loop.create_task(channel.send(embed=normal_embed("Le projet à été archivé car son propriétaire a quitté le serveur.")))
						send_log(f"Le projet `{project_data['name']}` de <@{member_id}> a été archivé car il a quitté le serveur", "Archivage d'un projet")
					else:
						overwrites = channel.overwrites
						overwrites[discord_variables.main_guild.default_role] = nextcord.PermissionOverwrite(send_messages=False)
						overwrites[member] = project_owner_perms
						bot.loop.create_task(channel.edit(overwrites=overwrites, reason="Désarchivage du projet"))
						bot.loop.create_task(channel.send(embed=normal_embed("Le projet à été désarchivé car son propriétaire a de nouveau rejoint le serveur.")))
						send_log(f"Le projet `{project_data['name']}` de <@{member_id}> a été désarchivé car il a de nouveau rejoint le serveur", "Désarchivage d'un projet")
					project_data["archived"] = archive
					save = True

		elif not archive:
			for channel_id, project_data in member_projects.items():
				if member_id in project_data["members"]:
					channel = get_textchannel(channel_id)
					bot.loop.create_task(channel.set_permissions(member, overwrite=project_member_perms, reason="Ré-ajout d'un membre au projet"))
				elif member_id in project_data["mutes"]:
					channel = get_textchannel(channel_id)
					bot.loop.create_task(channel.set_permissions(member, overwrite=project_mute_perms, reason="Re-mute d'un membre"))

	if save and (not do_not_save):
		save_json()


async def task_remove_reactionroles_reactions(member):
	for channel in member.guild.text_channels:
		for message_id in data['roleonreact']:
			for emoji_str in data['roleonreact'][message_id]:
				try:
					message = await channel.fetch_message(message_id)
					if message:
						await message.remove_reaction(emoji_str, member)
				except nextcord.errors.NotFound:
					pass


async def task_send_welcome(member):
	welcome_msg = nextcord.Embed(color=embed_color, title=f"Bienvenue {member}", description=f"Bienvenue {member.mention}, et merci à toi !!")
	welcome_msg.set_footer(text=f"Le serveur compte maintenant {len(member.guild.humans)} membres !")
	welcome_msg.set_thumbnail(url=member.display_avatar.url)
	await discord_variables.welcome_channel.send(embed=welcome_msg)


async def task_send_quit(member):
	quit_msg = nextcord.Embed(color=embed_color, title=f"Au revoir {member}", description=f"{member.mention} a malhereusement quitté le serveur. On espère le revoir vite :cry:")
	quit_msg.set_footer(text=f"Le serveur ne compte plus que {len(member.guild.humans)} membres")
	quit_msg.set_thumbnail(url=member.display_avatar.url)
	await discord_variables.welcome_channel.send(embed=quit_msg)