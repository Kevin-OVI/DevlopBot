from functools import wraps
from typing import Optional

import nextcord
from nextcord import ui
from nextcord.ext import commands

from cache_data import cache_return, empty_function_cache
from data_file import data, projects_data, save_json
from discord_utils import has_guild_permissions, hidden_pin, try_send_dm
from utils import check_is_moderator, error_embed, get_id_str, get_member, get_textchannel, is_moderator, is_user_on_guild, normal_embed, question_embed, send_log, validation_embed
from variables import bot, bot_name, discord_variables, guild_ids
from misc_classes import ConfirmationView

project_ignore_channels = (988778342457147402, )

project_member_perms = nextcord.PermissionOverwrite(create_private_threads=True, create_public_threads=True, embed_links=True,
	attach_files=True, manage_threads=True, manage_messages=True, use_slash_commands=True)
project_owner_perms = nextcord.PermissionOverwrite.from_pair(*project_member_perms.pair())
project_owner_perms.update(view_channel=True)
project_mute_perms = nextcord.PermissionOverwrite(send_messages=False, use_slash_commands=False, send_messages_in_threads=False,
	create_public_threads=False, create_private_threads=False, add_reactions=False)


def check_is_project(func):
	@wraps(func)
	async def overwrite(self, interaction, *args, **kwargs):
		if not is_project_channel(interaction.channel):
			await interaction.response.send_message(embed=error_embed("La commande ne peut pas être exécutée ici."), ephemeral=True)
			return
		await func(self, interaction, *args, **kwargs)

	return overwrite


def check_project_owner(func):
	@check_is_project
	@wraps(func)
	async def overwrite(self, interaction, *args, **kwargs):
		if (not is_project_owner(interaction.user, interaction.channel)) and has_guild_permissions(interaction.user, administrator=False):
			await interaction.response.send_message(embed=error_embed("Vous devez être le propriétaire du projet pour effectuer cette action."), ephemeral=True)
			return
		return await func(self, interaction, *args, **kwargs)

	return overwrite


def check_project_member(func):
	@check_is_project
	@wraps(func)
	async def overwrite(self, interaction, *args, **kwargs):
		if (not is_project_member(interaction.user, interaction.channel)) and has_guild_permissions(interaction.user, administrator=False):
			await interaction.response.send_message(embed=error_embed("Vous devez être un membre du projet pour effectuer cette action."), ephemeral=True)
			return
		return await func(self, interaction, *args, **kwargs)

	return overwrite


class ProjectCog(commands.Cog):
	@nextcord.slash_command(name="project", guild_ids=guild_ids)
	async def project_cmd(self):
		pass

	@project_cmd.subcommand(name="create", description="Permet de créer un projet")
	async def project_create_cmd(self, interaction: nextcord.Interaction):
		await create_project_start(interaction)

	@project_cmd.subcommand(name="add-member", description="Permet d'ajouter un membre au projet")
	@check_project_owner
	async def project_addmember_cmd(self, interaction: nextcord.Interaction,
			member: nextcord.Member = nextcord.SlashOption(name="membre", description="Le membre à ajouter au projet", required=True)):
		if is_project_member(member, interaction.channel):
			await interaction.response.send_message(embed=error_embed("Le membre est déjà membre de ce projet"), ephemeral=True)
			return

		owner_id, project_data = find_project(interaction.channel)
		user_id = get_id_str(member)
		if user_id in project_data["mutes"]:
			await interaction.response.send_message(embed=error_embed("Vous ne pouvez pas ajouter au projet un membre réduit au silence."), ephemeral=True)
			return

		project_data["members"].append(user_id)
		save_json()

		empty_function_cache(is_project_member)
		bot.loop.create_task(edit_info_message(owner_id, interaction.channel))
		if is_user_on_guild(member):
			bot.loop.create_task(interaction.channel.set_permissions(member, overwrite=project_member_perms, reason="Ajout d'un membre au projet"))
			bot.loop.create_task(try_send_dm(member,
				embed=normal_embed(f"Vous avez été ajouté aux membre du projet [{project_data['name']}]({interaction.channel.jump_url}) de <@{owner_id}>")))
		send_log(f"{interaction.user.mention} a ajouté {member.mention} aux membres du projet [{project_data['name']}]({interaction.channel.jump_url}) de <@{owner_id}>",
			"Ajout d'un membre à un projet")
		await interaction.response.send_message(embed=validation_embed(f"{member.mention} a été ajouté aux membres du projet."), ephemeral=True)

	@project_cmd.subcommand(name="remove-member", description="Permet de retirer un membre du projet")
	@check_project_owner
	async def project_removemember_cmd(self, interaction: nextcord.Interaction,
			member: nextcord.Member = nextcord.SlashOption(name="membre", description="Le membre à retirer au projet", required=True)):
		if is_project_owner(member, interaction.channel):
			await interaction.response.send_message(embed=error_embed("Vous ne pouvez pas retirer le propriétaire du projet"), ephemeral=True)
			return

		if not is_project_member(member, interaction.channel):
			await interaction.response.send_message(embed=error_embed("Le membre n'est pas membre de ce projet"), ephemeral=True)
			return

		owner_id, project_data = find_project(interaction.channel)
		project_data["members"].remove(get_id_str(member))
		save_json()

		empty_function_cache(is_project_member)
		bot.loop.create_task(edit_info_message(owner_id, interaction.channel))
		if is_user_on_guild(member):
			bot.loop.create_task(interaction.channel.set_permissions(member, overwrite=None, reason="Suppression d'un membre du projet"))
			bot.loop.create_task(try_send_dm(member,
				embed=normal_embed(f"Vous avez été retiré des membres du projet [{project_data['name']}]({interaction.channel.jump_url}) de <@{owner_id}>")))
		send_log(f"{interaction.user.mention} a retiré {member.mention} des membres du projet [{project_data['name']}]({interaction.channel.jump_url}) de <@{owner_id}>",
			"Retrait d'un membre d'un projet")
		await interaction.response.send_message(embed=validation_embed(f"{member.mention} a été retiré des membres du projet."), ephemeral=True)

	@project_cmd.subcommand(name="edit", description="Permet de modifier le nom ou la description du projet")
	@check_project_owner
	async def project_edit_cmd(self, interaction: nextcord.Interaction):
		await interaction.response.send_modal(ProjectTopicEditModal(interaction))

	@project_cmd.subcommand(name="delete", description="Permet de supprimer le projet")
	@check_project_owner
	async def project_delete_cmd(self, interaction: nextcord.Interaction):
		view = ConfirmationView()
		await interaction.response.send_message(embed=question_embed("Êtes-vous sur de vouloir supprimer ce projet ?"), view=view, ephemeral=True)
		await view.wait()
		if view.value:
			owner_id, project_data = find_project(interaction.channel)
			del (projects_data[owner_id][get_id_str(interaction.channel)])
			if not projects_data[owner_id]:
				del [projects_data[owner_id]]
			save_json()
			send_log(f"{interaction.user.mention} a supprimé le projet `{project_data['name']}` de <@{owner_id}>", "Suppression d'un projet")
			await interaction.channel.delete(reason="Suppression d'un projet")
		else:
			await interaction.edit_original_message(embed=normal_embed("Suppression du projet annulée"), view=None)

	@project_cmd.subcommand(name="mute", description="Permet de réduire au silence un membre")
	@check_project_member
	async def project_mute_cmd(self, interaction: nextcord.Interaction,
			member: nextcord.Member = nextcord.SlashOption(name="membre", description="Le membre à réduire au silence", required=True)):
		owner_id, project_data = find_project(interaction.channel)
		user_id = get_id_str(member)
		if user_id in project_data["mutes"]:
			await interaction.response.send_message(embed=error_embed("Le membre est déjà réduit au silence."), ephemeral=True)
			return

		if is_project_member(member, interaction.channel):
			await interaction.response.send_message(embed=error_embed("Vous ne pouvez pas réduire au silence un membre du projet."), ephemeral=True)
			return

		project_data["mutes"].append(user_id)
		save_json()
		if is_user_on_guild(member):
			bot.loop.create_task(interaction.channel.set_permissions(member, overwrite=project_mute_perms, reason="Mute d'un membre"))
			bot.loop.create_task(try_send_dm(member,
				embed=normal_embed(f"Vous avez été réduit au silence dans le projet [{project_data['name']}]({interaction.channel.jump_url}) de <@{owner_id}>")))
		send_log(f"{interaction.user.mention} a réduit {member.mention} au silence dans le projet [{project_data['name']}]({interaction.channel.jump_url}) de <@{owner_id}>",
			"Mute d'un membre")
		await interaction.response.send_message(embed=validation_embed(f"{member.mention} a été réduit au silence dans ce salon."), ephemeral=True)

	@project_cmd.subcommand(name="unmute", description="Permet de supprimer la réduction au silence d'un membre")
	@check_project_member
	async def project_unmute_cmd(self, interaction: nextcord.Interaction,
			member: nextcord.Member = nextcord.SlashOption(name="membre", description="Le membre auquel supprimer la réduction au silence", required=True)):
		owner_id, project_data = find_project(interaction.channel)
		user_id = get_id_str(member)
		if user_id not in project_data["mutes"]:
			await interaction.response.send_message(embed=error_embed("Le membre n'est pas réduit au silence."), ephemeral=True)
			return

		project_data["mutes"].remove(user_id)
		save_json()
		if is_user_on_guild(member):
			bot.loop.create_task(interaction.channel.set_permissions(member, overwrite=None, reason="Unmute d'un membre"))
			bot.loop.create_task(try_send_dm(member,
				embed=normal_embed(f"Vous n'êtes plus réduit au silence dans le projet [{project_data['name']}]({interaction.channel.jump_url}) de <@{owner_id}>")))
		send_log(f"{interaction.user.mention} a supprimé la réduction au silence de {member.mention} dans le projet [{project_data['name']}]({interaction.channel.jump_url}) \
	de <@{owner_id}>", "Unmute d'un membre")
		await interaction.response.send_message(embed=validation_embed(f"{member.mention} n'est plus réduit au silence dans ce salon."), ephemeral=True)

	@project_cmd.subcommand(name="hold-for-review", description="Permet de marquer un projet comme `à examiner`")
	@check_is_moderator()
	@check_is_project
	async def project_holdforreview_cmd(self, interaction: nextcord.Interaction):
		owner_id, project_data = find_project(interaction.channel)
		if project_data["held_for_review"]:
			await unhold_for_review(interaction, owner_id, project_data)
		else:
			project_data["held_for_review"] = True
			save_json()
			overwrites = interaction.channel.overwrites
			overwrites[interaction.guild.default_role] = nextcord.PermissionOverwrite(view_channel=False)
			overwrites[discord_variables.moderator_role] = nextcord.PermissionOverwrite(view_channel=True)
			bot.loop.create_task(interaction.channel.edit(category=discord_variables.revision_categ, overwrites=overwrites, reason="Marquage comme `à examiner`"))
			bot.loop.create_task(try_send_dm(get_member(owner_id),
				embed=normal_embed(f"Votre projet [{project_data['name']}]({interaction.channel.jump_url}) à été marqué comme `à examiner`.\n\
	Cela signifie qu'il n'est plus visible au public et qu'un modérateur ou administrateur doit l'examiner pour qu'il soit de nouveau accessible.")))
			send_log(f"Le projet [{project_data['name']}]({interaction.channel.jump_url}) de <@{owner_id}> à été marqué comme `à examiner` par {interaction.user.mention}",
				"Mise en examen")
			await interaction.response.send_message(embed=validation_embed("Le projet à été marqué comme `à examiner`"), view=ReviewView())

	@project_cmd.subcommand(name="transfer-property", description="Permet de transférer la propriété du projet à un autre membre du serveur")
	@check_project_owner
	async def project_transferproperty_cmd(self, interaction: nextcord.Interaction,
			member: nextcord.Member = nextcord.SlashOption(name="membre", description="Le membre auquel transférer la propriété", required=True),
			stay_member: bool = nextcord.SlashOption(name="rester_membre", description="Souhaitez vous rester membre du projet après le transfert ?", required=True)):
		if not is_user_on_guild(member):
			await interaction.response.send_message(embed=error_embed("L'utilisateur n'est pas présent sur le serveur."), ephemeral=True)
			return
		old_owner_id, project_data = find_project(interaction.channel)
		new_owner_id = get_id_str(member)
		if old_owner_id == new_owner_id:
			await interaction.response.send_message(embed=error_embed("Le membre est déjà propriétaire de ce projet"), ephemeral=True)
			return

		embed = question_embed(
			f"Êtes-vous sur de vouloir transférer la propriété du projet [{project_data['name']}]({interaction.channel.jump_url}) à {member} ({member.mention}) ?",
			"Attention, vous ne pourrez pas annuler cette action")
		embed.set_footer(text=f"En transférant la propriété du projet à {member}, vous reconnaissez que celui-ci lui appartiendra officiellement")
		view = ConfirmationView()
		await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
		await view.wait()
		if view.value:
			channel_id = get_id_str(interaction.channel)
			if stay_member:
				project_data["members"].append(old_owner_id)
				empty_function_cache(is_project_member)
			if new_owner_id in project_data["members"]:
				project_data["members"].remove(new_owner_id)
			projects_data.setdefault(new_owner_id, {})
			projects_data[new_owner_id][channel_id] = project_data
			del (projects_data[old_owner_id][channel_id])
			if not projects_data[old_owner_id]:
				del [projects_data[old_owner_id]]
			save_json()
			empty_function_cache(is_project_owner)
			empty_function_cache(find_project)
			bot.loop.create_task(edit_info_message(new_owner_id, interaction.channel))
			bot.loop.create_task(try_send_dm(member, embed=normal_embed(f"Vous avez reçu la propriété du projet [{project_data['name']}]({interaction.channel.jump_url})")))
			send_log(
				f"La propriété du projet [{project_data['name']}]({interaction.channel.jump_url}) de <@{old_owner_id}> à été transférée à {member.mention} par {interaction.user.mention}",
				"Transfert de propriété")
			await interaction.edit_original_message(embed=validation_embed("Le transfert de propriété a été effectué"), view=None)
		else:
			await interaction.edit_original_message(embed=normal_embed("Le transfert de propriété a été annulé"), view=None)

	@commands.Cog.listener()
	async def on_first_ready(self):
		bot.add_modal(ProjectTopicModal())
		bot.add_modal(ProjectTopicEditModal())
		bot.add_view(CreateProjectView())
		bot.add_view(ReviewView())

	@commands.Cog.listener()
	async def on_member_remove_accepted_rules(self, member):
		task_project_perms(member, True)

	@commands.Cog.listener()
	async def on_rules_accept(self, member):
		task_project_perms(member, False, True)

	@commands.Cog.listener()
	async def on_raw_message_delete(self, payload):
		if payload.guild_id == discord_variables.main_guild.id:
			r = find_project(payload.channel_id)
			if r is not None:
				owner_id, project_data = r
				if payload.message_id == project_data["info_message"]:
					await edit_info_message(owner_id, payload.channel_id)


class ProjectTopicModal(ui.Modal):
	modal_name = f"{bot_name}:project_topic"

	def __init__(self, interaction: Optional[nextcord.Interaction] = None):
		description, name, title = None, None, "Création d'un projet"
		if interaction:
			owner_id, project_data = find_project(interaction.channel)
			description = project_data["description"]
			name = project_data["name"]
			title = "Modification d'un projet"

		super().__init__(title, timeout=None, custom_id=self.modal_name)

		self.name_field = ui.TextInput(label="Nom du projet", style=nextcord.TextInputStyle.short,
			custom_id=f"{self.modal_name}:name_field", min_length=3, max_length=32, required=True,
			placeholder="Entrez ici un nom pour votre projet", default_value=name)
		self.add_item(self.name_field)

		self.description_field = ui.TextInput(label="Description du projet", style=nextcord.TextInputStyle.paragraph,
			custom_id=f"{self.modal_name}:description_field", min_length=10, max_length=1024, required=True,
			placeholder="Entrez ici une description pour votre projet", default_value=description)
		self.add_item(self.description_field)

	async def callback(self, interaction):
		await interaction.response.defer(ephemeral=True)
		user_id_str = str(interaction.user.id)
		name = self.name_field.value
		description = self.description_field.value
		channel = await discord_variables.projects_categ.create_text_channel(name=name, overwrites={interaction.user: project_owner_perms},
			topic=f"Projet de {interaction.user.mention}\n\n{description[:988] + '...' if len(description) > 990 else description}", reason="Création d'un projet")
		channel_id_str = str(channel.id)
		projects_data.setdefault(user_id_str, {})
		projects_data[user_id_str][channel_id_str] = {"name": name, "description": description, "members": [], "mutes": [], "held_for_review": False, "archived": False}
		projects_data[user_id_str][channel_id_str]["info_message"] = (await send_info_message(interaction.user, channel)).id
		save_json()
		send_log(f"<@{user_id_str}> a créé le projet [{name}]({channel.jump_url})", "Création d'un projet", {"Description": description})
		await interaction.followup.send(embed=validation_embed(f"Votre projet à été créé : {channel.mention}."), ephemeral=True)


class ProjectTopicEditModal(ProjectTopicModal):
	modal_name = f"{bot_name}:project_topic_edit"

	async def callback(self, interaction):
		channel = interaction.channel
		if channel is None:
			await interaction.response.send_message(embed=error_embed("Impossible de détecter le salon du projet."), ephemeral=True)
		else:
			if not is_project_channel(channel):
				await interaction.response.send_message(embed=error_embed("Cette action n'est possible que dans un salon de projet."), ephemeral=True)

			r = find_project(interaction.channel)
			if r is None:
				await interaction.response.send_message(embed=error_embed("Le projet n'a pas été trouvé ! Il a peut-être été supprimé par un administrateur."), ephemeral=True)
				return
			owner_id, project_data = r
			name = self.name_field.value
			description = self.description_field.value

			bot.loop.create_task(interaction.channel.edit(name=name,
				topic=f"Projet de <@{owner_id}>\n\n{description[:988] + '...' if len(description) > 990 else description}", reason="Modification d'un projet"))

			old_name = project_data["name"]
			old_desctiption = project_data["description"]
			project_data["name"] = name
			project_data["description"] = description
			bot.loop.create_task(edit_info_message(owner_id, channel))
			save_json()
			fields = {"Description": description}
			if old_name != name:
				fields["Ancien nom"] = old_name
			if old_desctiption != description:
				fields["Ancienne description"] = old_desctiption
			send_log(f"{interaction.user.mention} a modifié le projet [{name}]({channel.jump_url}) de <@{owner_id}>", "Modification d'un projet", fields)
			embed = validation_embed(f"Votre projet à été modifié.")
			embed.set_footer(text="Le nom et la description du salon peuvent prendre quelques minutes à se modifier, à cause des ratelimits de discord.")
			await interaction.response.send_message(embed=embed, ephemeral=True)


class CreateProjectView(ui.View):
	view_name = f"{bot_name}:create_project"

	def __init__(self):
		super().__init__(timeout=None)

	@ui.button(label="Créer un projet", emoji="🔬", custom_id=f"{view_name}:create_button", style=nextcord.ButtonStyle.primary)
	async def create_button(self, button, interaction):
		await create_project_start(interaction)


class ReviewView(ui.View):
	view_name = f"{bot_name}:revision"

	def __init__(self):
		super().__init__(timeout=None)

	@ui.button(label="Réouvrir au public", emoji="📤", style=nextcord.ButtonStyle.green, custom_id=f"{view_name}:reopen")
	async def reopen_button(self, button, interaction):
		if not is_moderator(interaction.user):
			await interaction.response.send_message(embed=error_embed("Vous n'avez pas la permission de réouvrir ce projet au public."), ephemeral=True)
			return

		owner_id, project_data = find_project(interaction.channel)
		if not project_data["held_for_review"]:
			bot.loop.create_task(interaction.message.delete())
			await interaction.response.send_message(embed=error_embed("Le projet n'est pas marqué comme `à examiner`"), ephemeral=True)
			return

		await unhold_for_review(interaction, owner_id, project_data)


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


def generate_info_message(user, channel):
	user_id = get_id_str(user)
	channel_id = get_id_str(channel)

	project_data = projects_data[user_id][channel_id]
	embed = normal_embed(project_data["description"], project_data["name"])
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


async def create_project_start(interaction: nextcord.Interaction):
	user_data = data["projects"].get(str(interaction.user.id))
	max_projects = data["config"]["max-projects"]
	if len(user_data) >= max_projects:
		await interaction.response.send_message(embed=error_embed(f"Vous ne pouvez avoir que {max_projects} projects au maximum."), ephemeral=True)
		return
	await interaction.response.send_modal(ProjectTopicModal())


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
