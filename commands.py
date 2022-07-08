import io
import json
import time

import nextcord
from nextcord.ext import application_checks, commands

from cache_data import empty_cache, empty_function_cache
from data_file import data, load_json, projects_data, save_json
from discord_utils import try_send_dm
from modals import ProjectTopicEditModal
from utils import check_is_moderator, check_is_project, check_project_member, check_project_owner, create_project_start, edit_info_message, error_embed, \
	find_project, get_id_str, get_member, is_project_member, is_project_owner, is_user_on_guild, normal_embed, question_embed, send_log, unhold_for_review, validation_embed
from variables import bot, discord_variables, project_member_perms, project_mute_perms
from views import ConfirmationView, ReviewView, RulesAcceptView

guild_ids = [895005331980185640, 988543675640455178]


class ProjectCommandCog(commands.Cog):
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


class RoleOnReactCommandCog(commands.Cog):
	@nextcord.slash_command(name="roleonreact", guild_ids=guild_ids)
	async def roleonreact_cmd(self):
		pass

	@roleonreact_cmd.subcommand(name="add", description="Permet d'ajouter un rôle-réaction")
	@application_checks.has_permissions(administrator=True)
	async def roleonreact_add_cmd(self, interaction,
			message_id: str = nextcord.SlashOption(name="message_id", description="L'identifiant du message auquel ajouter le role-réaction", required=True),
			reaction: str = nextcord.SlashOption(name="reaction", description="La réaction à ajouter", required=True),
			role: nextcord.Role = nextcord.SlashOption(name="role", description="Le rôle à ajouter", required=True)):
		section = data['roleonreact']
		try:
			message = await interaction.channel.fetch_message(message_id)
			await message.add_reaction(reaction)
			section.setdefault(message_id, {})
			section[message_id][reaction] = role.id
			await interaction.response.send_message('Le role sur réaction a été ajouté', ephemeral=True)
			save_json()
		except nextcord.errors.NotFound:
			await interaction.response.send_message("Le message est introuvable", ephemeral=True)
		except AttributeError:
			await interaction.response.send_message("La réaction n'exite pas", ephemeral=True)

	@roleonreact_cmd.subcommand(name="remove", description="Permet de supprimer un rôle-réaction")
	@application_checks.has_permissions(administrator=True)
	async def roleonreact_remove_cmd(self, interaction,
			message_id: str = nextcord.SlashOption(name="message_id", description="L'identifiant du message duquel supprimer le role-réaction", required=True),
			reaction: str = nextcord.SlashOption(name="reaction", description="La réaction à supprimer", required=True)):
		section = data['roleonreact']
		try:
			if message_id in section.keys():
				if reaction in section[message_id].keys():
					del (section[message_id][reaction])

				if not section[message_id]:
					del (section[message_id])
			save_json()
			await interaction.response.send_message("Le rôle-réaction a été supprimé", ephemeral=True)

		except nextcord.errors.NotFound:
			await interaction.response.send_message("Le message est introuvable", ephemeral=True)
		except AttributeError:
			await interaction.response.send_message("La réaction n'existe pas", ephemeral=True)


class RulesCommandCog(commands.Cog):
	@nextcord.slash_command(name="rules", guild_ids=guild_ids)
	async def rules_cmd(self):
		pass

	@rules_cmd.subcommand(name="get", description="Permet d'obtenir le json de l'embed du message des règles")
	@application_checks.has_permissions(administrator=True)
	async def rules_get_cmd(self, interaction):
		f = io.StringIO()
		json.dump([x.to_dict() for x in discord_variables.rules_msg.embeds], f, ensure_ascii=False, indent=2)
		f.seek(0)
		f = io.BytesIO(f.read().encode())
		await interaction.response.send_message("Voici le json de l'embed des règles", file=nextcord.File(f, filename='rules message.json'), ephemeral=True)

	@rules_cmd.subcommand(name="set", description="Permet de définir le json de l'embed du message des règles")
	@application_checks.has_permissions(administrator=True)
	async def rules_set_cmd(self, interaction,
			rules_file: nextcord.Attachment = nextcord.SlashOption(name="embed", description="Le json de l'embed du message des règles", required=True)):
		jload = json.loads(await rules_file.read())
		if type(jload) == list:
			embeds = [nextcord.Embed.from_dict(x) for x in jload]
		elif type(jload) == dict:
			embeds = [nextcord.Embed.from_dict(jload)]
		else:
			await interaction.reply("Le json doit être une liste d'objets embeds ou un objet embed")
			return

		await discord_variables.rules_msg.edit(embeds=embeds, view=RulesAcceptView())
		await interaction.response.send_message("Le message des règles a été modifié", ephemeral=True)


class ConfigCommandCog(commands.Cog):
	@nextcord.slash_command(name="config", guild_ids=guild_ids, default_member_permissions=nextcord.Permissions(administrator=True))
	@application_checks.has_permissions(administrator=True)
	async def config_cmd(self):
		pass

	@config_cmd.subcommand(name="save", description="Permet de sauvegarder le fichier de configuration")
	@application_checks.is_owner()
	async def config_save_cmd(self, interaction: nextcord.Interaction):
		save_json()
		await interaction.response.send_message(embed=validation_embed("Le fichier de configuration a été sauvegardé"), ephemeral=True)

	@config_cmd.subcommand(name="reload", description="Permet de recharger le fichier de configuration")
	@application_checks.is_owner()
	async def config_save_cmd(self, interaction: nextcord.Interaction):
		load_json()
		empty_cache()
		await interaction.response.send_message(embed=validation_embed("Le fichier de configuration a été rechargé"), ephemeral=True)

	@config_cmd.subcommand(name="settings", description="Permet de définir certains paramètres")
	@application_checks.has_permissions(administrator=True)
	async def config_settings_cmd(self, interaction: nextcord.Interaction,
			max_projects: int = nextcord.SlashOption(name="max-projets", description="Définir le maximum de projets par membre", required=False)):
		section = data["config"]
		if max_projects is None:
			lines = []
			for config_name, display_name in (("max-projects", "Nombre de projets maximum"),):
				lines.append(f"{display_name}: {section[config_name]}")
			await interaction.response.send_message(embed=normal_embed("\n".join(lines), "Paramètres actuels :"), ephemeral=True)
		else:
			for config_name, command_variable in (("max-projects", max_projects),):
				if command_variable is not None:
					section[config_name] = command_variable
			save_json()
			await interaction.response.send_message(embed=validation_embed("Les paramètres ont été modifiés"), ephemeral=True)


class SingleCommandsCog(commands.Cog):
	@nextcord.slash_command(name="ping", description="Affiche la latence du bot", guild_ids=guild_ids)
	async def ping_cmd(self, interaction):
		embed = normal_embed(f"**Latence de l'api discord** : `{round(bot.latency * 1000)}ms`", '<:wifi:895028279478734878> | Temps de réponses :')
		start = time.time()
		await interaction.response.send_message(embed=embed, ephemeral=True)
		msg_latency = time.time() - start
		embed.description += f"\n\n**Temps d'envoi du message** : `{round(msg_latency * 1000)}ms`"
		await interaction.edit_original_message(embed=embed)
