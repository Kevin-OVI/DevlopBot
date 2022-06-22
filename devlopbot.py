from typing import Optional, Union

from dotenv import load_dotenv
from nextcord import ui
from nextcord.ext import application_checks, tasks

from cache_data import cache_return
from discord_utils import *

load_dotenv()
bot_name = "devlopbot"

data = ConfigDict('data_devlopbot.json')
projects_data: dict


def save_json():
	data.save()


def load_json():
	global projects_data

	data.reload()

	for x in ("roleonreact", "join_not_rules", "projects", "config"):
		data.setdefault(x, {})

	data["config"].setdefault("max-projects", 2)
	save_json()

	projects_data = data["projects"]


load_json()


class CreateProjectView(ui.View):
	view_name = f"{bot_name}:create_project"

	def __init__(self):
		super().__init__(timeout=None)

	@ui.button(label="Créer un projet", emoji="🔬", custom_id=f"{view_name}:create_button", style=nextcord.ButtonStyle.primary)
	async def create_button(self, button, interaction):
		await create_project_start(interaction)


class ConfirmationView(ui.View):
	view_name = f"{bot_name}:confirmation"

	def __init__(self):
		super().__init__(timeout=30)
		self.value = None

	@ui.button(label="Confirmer", emoji="✅", style=nextcord.ButtonStyle.green, custom_id=f"{view_name}:confirm")
	async def yes_button(self, button, interaction):
		self.value = True
		self.stop()

	@ui.button(label="Annuler", emoji="❌", style=nextcord.ButtonStyle.gray, custom_id=f"{view_name}:cancel")
	async def no_button(self, button, interaction):
		self.value = False
		self.stop()


class RulesAcceptView(ui.View):
	view_name = "rules_accept"

	def __init__(self):
		super().__init__(timeout=None)

	@ui.button(label="J'accepte", emoji="<:oui:988807617654702140>", style=nextcord.ButtonStyle.primary, custom_id=f"{bot_name}:{view_name}:accept")
	async def accept_button(self, button, interaction):
		if str(interaction.user.id) in data['join_not_rules']:
			del (data['join_not_rules'][str(interaction.user.id)])
			save_json()
		await asyncio.gather(interaction.user.add_roles(member_role, reason="Le membre a accepté les règles"),
			interaction.response.send_message(embed=validation_embed(f"Les règles ont été acceptées. Le rôle {member_role.mention} vous a été ajouté"), ephemeral=True))


class ProjectTopicModal(ui.Modal):
	modal_name = f"{bot_name}:project_topic"

	def __init__(self, interaction: Optional[nextcord.Interaction] = None):
		description, name, title = None, None, "Création d'un projet"
		if interaction:
			creator_id, project_data = find_project(interaction.channel)
			description = project_data["description"]
			name = project_data["name"]
			title = "Modification d'un projet"

		super().__init__(title, timeout=None, custom_id=self.modal_name)

		self.name_field = ui.TextInput(label="Nom du projet", style=nextcord.TextInputStyle.short,
			custom_id=f"{self.modal_name}:name_field", min_length=3, max_length=32, required=True,
			placeholder="Entrez ici un nom pour votre projet", default_value=name)
		self.add_item(self.name_field)

		self.description_field = ui.TextInput(label="Description du projet", style=nextcord.TextInputStyle.paragraph,
			custom_id=f"{self.modal_name}:description_field", min_length=10, max_length=970, required=True,
			placeholder="Entrez ici une description pour votre projet", default_value=description)
		self.add_item(self.description_field)

	async def callback(self, interaction):
		await interaction.response.defer(ephemeral=True)
		user_id_str = str(interaction.user.id)
		channel = await projects_categ.create_text_channel(name=self.name_field.value, overwrites={interaction.user: project_member_perms},
			topic=f"Projet de {interaction.user.mention}\n\n- {self.description_field.value}", reason="Création d'un projet")
		channel_id_str = str(channel.id)
		projects_data.setdefault(user_id_str, {})
		projects_data[user_id_str][channel_id_str] = {"name": self.name_field.value, "description": self.description_field.value, "members": [], "mutes": []}
		projects_data[user_id_str][channel_id_str]["info_message"] = (await send_info_message(interaction.user, channel)).id
		save_json()
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
			creator_id, project_data = r

			bot.loop.create_task(interaction.channel.edit(name=self.name_field.value,
				topic=f"Projet de <@{creator_id}>\n\n- {self.description_field.value}", reason="Modification d'un projet"))

			project_data["name"] = self.name_field.value
			project_data["description"] = self.description_field.value
			project_data["info_message"] = (await edit_info_message(creator_id, channel)).id
			save_json()
			embed = validation_embed(f"Votre projet à été modifié.")
			embed.set_footer(text="Le nom et la description du salon peuvent prendre quelques minutes à se modifier, à cause des ratelimits de discord.")
			await interaction.response.send_message(embed=embed, ephemeral=True)


def validation_embed(message, title=nextcord.Embed.Empty):
	return embed_message("<:oui:988807617654702140> " + message, embed_color, title)


def error_embed(message, title=nextcord.Embed.Empty):
	return embed_message(":x: " + message, embed_color, title)


def question_embed(message, title=nextcord.Embed.Empty):
	return embed_message("❓ " + message, embed_color, title)


def normal_embed(message, title=nextcord.Embed.Empty):
	return embed_message(message, embed_color, title)


def base_cmd_signature(func):
	async def overwrite(interaction):
		return await func(interaction)

	return overwrite


def member_cmd_signature(*, name="membre", description, required=False):
	def decorator(func):
		async def overwrite(interaction, member: nextcord.Member = nextcord.SlashOption(name=name, description=description, required=required)):
			return await func(interaction, member=member)

		return overwrite

	return decorator


async def remove_reactionroles_reactions(member):
	for channel in member.guild.text_channels:
		for message_id in data['roleonreact']:
			for emoji_str in data['roleonreact'][message_id]:
				try:
					message = await channel.fetch_message(message_id)
					if message:
						await message.remove_reaction(emoji_str, member)
				except nextcord.errors.NotFound:
					pass


async def send_welcome(member):
	welcome_msg = nextcord.Embed(color=embed_color, title=f"Bienvenue {member}", description=f"Bienvenue {member.mention}, et merci à toi !!")
	welcome_msg.set_footer(text=f"Le serveur compte maintenant {len(member.guild.humans)} membres !")
	welcome_msg.set_thumbnail(url=member.display_avatar.url)
	await welcome_channel.send(embed=welcome_msg)


async def send_quit(member):
	quit_msg = nextcord.Embed(color=embed_color, title=f"Au revoir {member}", description=f"{member.mention} a malhereusement quitté le serveur. On espère le revoir vite :cry:")
	quit_msg.set_footer(text=f"Le serveur ne compte plus que {len(member.guild.humans)} membres")
	quit_msg.set_thumbnail(url=member.display_avatar.url)
	await welcome_channel.send(embed=quit_msg)


async def update_stats():
	await bot.get_channel(988887221262221342).edit(name=f"Membres: {len(main_guild.humans)}", reason="Mise à jour des statistiques")


async def create_project_start(interaction: nextcord.Interaction):
	user_data = data["projects"].get(str(interaction.user.id))
	max_projects = data["config"]["max-projects"]
	if len(user_data) >= max_projects:
		await interaction.response.send_message(embed=error_embed(f"Vous ne pouvez avoir que {max_projects} projects au maximum."), ephemeral=True)
		return
	await interaction.response.send_modal(ProjectTopicModal())


def get_id_str(obj: Optional[Union[str, int, nextcord.abc.Snowflake]]) -> str:
	if isinstance(obj, nextcord.abc.Snowflake):
		return str(obj.id)
	elif isinstance(obj, int):
		return str(obj)
	return obj


def get_member(obj: Union[str, int, nextcord.abc.Snowflake]) -> nextcord.Member:
	if isinstance(obj, str):
		return main_guild.get_member(int(obj))
	if isinstance(obj, int):
		return main_guild.get_member(obj)
	return main_guild.get_member(obj.id)


def get_textchannel(obj: Union[str, int, nextcord.abc.Snowflake]) -> nextcord.TextChannel:
	if isinstance(obj, str):
		return main_guild.get_channel(int(obj))
	if isinstance(obj, int):
		return main_guild.get_channel(obj)
	return main_guild.get_channel(obj.id)


def generate_info_message(user, channel):
	user_id = get_id_str(user)
	channel_id = get_id_str(channel)

	project_data = projects_data[user_id][channel_id]
	embed = nextcord.Embed(description=project_data["description"], color=embed_color, title=project_data["name"])
	embed.add_field(name="Créateur", value=f"<@{user_id}>", inline=False)
	embed.add_field(name="Membres du projet", value=" ".join([f"<@{x}>" for x in (project_data["members"] + [user_id])]), inline=False)
	embed.set_footer(text="Merci de ne pas supprimer ce message.")
	return embed


async def send_info_message(user, channel):
	channel_obj = get_textchannel(channel)
	message = await channel_obj.send(embed=generate_info_message(user, channel))
	bot.loop.create_task(message.pin(reason="Épinglage du message d'informations"))
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
		bot.loop.create_task(message.pin(reason="Épinglage du message d'informations"))
	return message


def is_project_channel(channel: nextcord.abc.GuildChannel):
	return channel.category == projects_categ and channel.id not in project_ignore_channels


@cache_return(1800)
def find_project(channel):
	channel_id = get_id_str(channel)
	for user, projects in projects_data.items():
		if channel_id in projects:
			return user, projects[channel_id]


@cache_return(1800)
def is_project_creator(user, channel):
	user_id = get_id_str(user)
	channel_id = get_id_str(channel)
	return channel_id in projects_data.get(user_id, {})


def is_project_member(user, channel):
	user_id = get_id_str(user)
	if is_project_creator(user_id, channel):
		return True

	project = find_project(channel)[1]
	if project is None:
		return False
	return user_id in project["members"]


def check_bot_owner():
	return application_checks.check(lambda interaction: interaction.user.id == 894999665760665600)


embed_color = 0xAD1457
TOKEN = os.getenv('TOKEN_DEVLOPBOT')
guild_ids = [895005331980185640, 988543675640455178]
project_ignore_channels = (988778342457147402, 988780418365014026)
project_member_perms = nextcord.PermissionOverwrite(create_private_threads=True, create_public_threads=True, embed_links=True,
	attach_files=True, manage_threads=True, manage_messages=True)
project_mute_perms = nextcord.PermissionOverwrite(send_messages=False, use_slash_commands=False, send_messages_in_threads=False,
	create_public_threads=False, create_private_threads=False, add_reactions=False)
status_msg = [0, (
	(nextcord.ActivityType.playing, "coder"),
	(nextcord.ActivityType.listening, f'les commandes slash'),
	(nextcord.ActivityType.watching, "%members% membres")
)]

bot = nextcord.Client(intents=nextcord.Intents(guilds=True, members=True, reactions=True), activity=nextcord.Activity(type=nextcord.ActivityType.playing, name="démarrer..."))


@bot.slash_command(name="project", guild_ids=guild_ids)
async def project_cmd(self):
	pass


def check_project_creator(func):
	@wraps(func)
	async def overwrite(interaction, *args, **kwargs):
		if not is_project_channel(interaction.channel):
			await interaction.response.send_message(embed=error_embed("La commande ne peut pas être exécutée ici."), ephemeral=True)
			return
		if (not is_project_creator(interaction.user, interaction.channel)) and has_guild_permissions(interaction.user, administrator=False):
			await interaction.response.send_message(embed=error_embed("Vous devez être le créateur du projet pour effectuer cette action."), ephemeral=True)
			return
		return await func(interaction, *args, **kwargs)

	return overwrite


def check_project_member(func):
	@wraps(func)
	async def overwrite(interaction, *args, **kwargs):
		if not is_project_channel(interaction.channel):
			await interaction.response.send_message(embed=error_embed("La commande ne peut pas être exécutée ici."), ephemeral=True)
			return
		if (not is_project_member(interaction.user, interaction.channel)) and has_guild_permissions(interaction.user, administrator=False):
			await interaction.response.send_message(embed=error_embed("Vous devez être un membre du projet pour effectuer cette action."), ephemeral=True)
			return
		return await func(interaction, *args, **kwargs)

	return overwrite


@project_cmd.subcommand(name="create", description="Permet de créer un projet")
async def project_create_cmd(interaction: nextcord.Interaction):
	await create_project_start(interaction)


@project_cmd.subcommand(name="add-member", description="Permet d'ajouter un membre au projet")
@check_project_creator
async def project_addmember_cmd(interaction: nextcord.Interaction,
		member: nextcord.Member = nextcord.SlashOption(name="membre", description="Le membre à ajouter au projet", required=True)):
	if is_project_member(member, interaction.channel):
		await interaction.response.send_message(embed=error_embed("Le membre est déjà membre de ce projet"), ephemeral=True)
		return

	creator_id, project_data = find_project(interaction.channel)
	user_id = get_id_str(member)
	if user_id in project_data["mutes"]:
		await interaction.response.send_message(embed=error_embed("Vous ne pouvez pas ajouter au projet un membre réduit au silence."), ephemeral=True)
		return

	project_data["members"].append(user_id)
	save_json()

	bot.loop.create_task(edit_info_message(creator_id, interaction.channel))
	bot.loop.create_task(interaction.channel.set_permissions(member, overwrite=project_member_perms, reason="Ajout d'un membre au projet"))
	bot.loop.create_task(try_send_dm(member, embed=normal_embed(f"Vous avez été ajouté aux membre du projet [{project_data['name']}]({interaction.channel.jump_url})")))
	await interaction.response.send_message(embed=validation_embed(f"{member.mention} a été ajouté aux membres du projet."))


@project_cmd.subcommand(name="remove-member", description="Permet de retirer un membre du projet")
@check_project_creator
async def project_removemember_cmd(interaction: nextcord.Interaction,
		member: nextcord.Member = nextcord.SlashOption(name="membre", description="Le membre à retirer au projet", required=True)):
	if is_project_creator(member, interaction.channel):
		await interaction.response.send_message(embed=error_embed("Vous ne pouvez pas retirer le créateur du projet"), ephemeral=True)
		return

	if not is_project_member(member, interaction.channel):
		await interaction.response.send_message(embed=error_embed("Le membre n'est pas membre de ce projet"), ephemeral=True)
		return

	creator_id, project_data = find_project(interaction.channel)
	project_data["members"].remove(get_id_str(member))
	save_json()

	bot.loop.create_task(edit_info_message(creator_id, interaction.channel))
	bot.loop.create_task(interaction.channel.set_permissions(member, overwrite=None, reason="Suppression d'un membre du projet"))
	bot.loop.create_task(try_send_dm(member, embed=normal_embed(f"Vous avez été retiré des membres du projet [{project_data['name']}]({interaction.channel.jump_url})")))
	await interaction.response.send_message(embed=validation_embed(f"{member.mention} a été retiré des membres du projet."))


@project_cmd.subcommand(name="edit", description="Permet de modifier le nom ou la description du projet")
@check_project_creator
async def project_edit_cmd(interaction: nextcord.Interaction):
	await interaction.response.send_modal(ProjectTopicEditModal(interaction))


@project_cmd.subcommand(name="delete", description="Permet de supprimer le projet")
@check_project_creator
async def project_delete_cmd(interaction: nextcord.Interaction):
	view = ConfirmationView()
	await interaction.response.send_message(embed=question_embed("Êtes-vous sur de vouloir supprimer ce projet ?"), view=view, ephemeral=True)
	await view.wait()
	if view.value:
		creator_id = find_project(interaction.channel)[0]
		del (projects_data[creator_id][get_id_str(interaction.channel)])
		save_json()
		await interaction.channel.delete(reason="Suppression d'un projet")
	else:
		await interaction.edit_original_message(embed=normal_embed("Suppression du projet annulée"), view=None)


@project_cmd.subcommand(name="mute", description="Permet de réduire au silence un membre")
@check_project_member
async def project_mute_cmd(interaction: nextcord.Interaction,
		member: nextcord.Member = nextcord.SlashOption(name="membre", description="Le membre à réduire au silence", required=True)):
	creator_id, project_data = find_project(interaction.channel)
	user_id = get_id_str(member)
	if user_id in project_data["mutes"]:
		await interaction.response.send_message(embed=error_embed("Le membre est déjà réduit au silence."), ephemeral=True)
		return

	if is_project_member(member, interaction.channel):
		await interaction.response.send_message(embed=error_embed("Vous ne pouvez pas réduire au silence un membre du projet."), ephemeral=True)
		return

	project_data["mutes"].append(user_id)
	save_json()
	bot.loop.create_task(interaction.channel.set_permissions(member, overwrite=project_mute_perms, reason="Mute d'un membre"))
	await interaction.response.send_message(embed=validation_embed(f"{member.mention} a été réduit au silence dans ce salon."))


@project_cmd.subcommand(name="unmute", description="Permet de supprimer la réduction au silence d'un membre")
@check_project_member
async def project_unmute_cmd(interaction: nextcord.Interaction,
		member: nextcord.Member = nextcord.SlashOption(name="membre", description="Le membre auquel supprimer la réduction au silence", required=True)):
	creator_id, project_data = find_project(interaction.channel)
	user_id = get_id_str(member)
	if user_id not in project_data["mutes"]:
		await interaction.response.send_message(embed=error_embed("Le membre n'est pas réduit au silence."), ephemeral=True)
		return

	project_data["mutes"].remove(user_id)
	save_json()
	bot.loop.create_task(interaction.channel.set_permissions(member, overwrite=None, reason="Unmute d'un membre"))
	await interaction.response.send_message(embed=validation_embed(f"{member.mention} n'est plus réduit au silence dans ce salon."))


@bot.slash_command(name="roleonreact", guild_ids=guild_ids)
async def roleonreact_cmd():
	pass


@roleonreact_cmd.subcommand(name="add", description="Permet d'ajouter un rôle-réaction")
@application_checks.has_permissions(administrator=True)
async def roleonreact_add_cmd(interaction,
		message_id: str = nextcord.SlashOption(name="message_id", description="L'identifiant du message auquel ajouter le role-réaction", required=True),
		reaction: str = nextcord.SlashOption(name="reaction", description="La réaction à ajouter", required=True),
		role: nextcord.Role = nextcord.SlashOption(name="role", description="Le rôle à ajouter", required=True)):
	try:
		message = await interaction.channel.fetch_message(message_id)
		await message.add_reaction(reaction)
		data['roleonreact'].setdefault(message_id, {})
		data['roleonreact'][message_id][reaction] = role.id
		await interaction.response.send_message('Le role sur réaction a été ajouté', ephemeral=True)
		save_json()
	except nextcord.errors.NotFound:
		await interaction.response.send_message("Le message est introuvable", ephemeral=True)
	except AttributeError:
		await interaction.response.send_message("La réaction n'exite pas", ephemeral=True)


@roleonreact_cmd.subcommand(name="remove", description="Permet de supprimer un rôle-réaction")
@application_checks.has_permissions(administrator=True)
async def roleonreact_remove_cmd(interaction,
		message_id: str = nextcord.SlashOption(name="message_id", description="L'identifiant du message duquel supprimer le role-réaction", required=True),
		reaction: str = nextcord.SlashOption(name="reaction", description="La réaction à supprimer", required=True)):
	try:
		if message_id in data['roleonreact'].keys():
			if reaction in data['roleonreact'][message_id].keys():
				del (data['roleonreact'][message_id][reaction])

			if not data['roleonreact'][message_id]:
				del (data['roleonreact'][message_id])
		save_json()
		await interaction.response.send_message("Le rôle-réaction a été supprimé", ephemeral=True)

	except nextcord.errors.NotFound:
		await interaction.response.send_message("Le message est introuvable", ephemeral=True)
	except AttributeError:
		await interaction.response.send_message("La réaction n'exite pas", ephemeral=True)


@bot.slash_command(name="rules", guild_ids=guild_ids)
async def rules_cmd():
	pass


@rules_cmd.subcommand(name="get", description="Permet d'obtenir le json de l'embed du message des règles")
@application_checks.has_permissions(administrator=True)
async def rules_get_cmd(interaction):
	f = io.StringIO()
	json.dump([x.to_dict() for x in rules_msg.embeds], f, ensure_ascii=False, indent=2)
	f.seek(0)
	f = io.BytesIO(f.read().encode())
	await interaction.response.send_message("Voici le json de l'embed des règles", file=nextcord.File(f, filename='rules message.json'), ephemeral=True)


@rules_cmd.subcommand(name="set", description="Permet de définir le json de l'embed du message des règles")
@application_checks.has_permissions(administrator=True)
async def rules_set_cmd(interaction, rules_file: nextcord.Attachment = nextcord.SlashOption(name="embed", description="Le json du message des règles", required=True)):
	jload = json.loads(await rules_file.read())
	if type(jload) == list:
		embeds = [nextcord.Embed.from_dict(x) for x in jload]
	elif type(jload) == dict:
		embeds = [nextcord.Embed.from_dict(jload)]
	else:
		await interaction.reply("Le json doit être un array d'objets embeds ou un objet embed")
		return

	await rules_msg.edit(embeds=embeds, view=RulesAcceptView())
	await interaction.response.send_message("Le message des règles a été modifié", ephemeral=True)


@bot.slash_command(name="ping", description="Affiche la latence du bot", guild_ids=guild_ids)
async def ping_cmd(interaction):
	embed = nextcord.Embed(title='<:wifi:895028279478734878> | Temps de réponses :',
		description=f"**Latence de l'api discord** : `{round(bot.latency * 1000)}ms`", color=embed_color)
	start = time.time()
	await interaction.response.send_message(embed=embed, ephemeral=True)
	msg_latency = time.time() - start
	embed.description += f"\n\n**Temps d'envoi du message** : `{round(msg_latency * 1000)}ms`"
	await interaction.edit_original_message(embed=embed)


@bot.slash_command(name="config", guild_ids=guild_ids, default_member_permissions=nextcord.Permissions(administrator=True))
@application_checks.has_permissions(administrator=True)
async def config_cmd():
	pass


@config_cmd.subcommand(name="save", description="Permet de sauvegarder le fichier de configuration")
@check_bot_owner()
async def config_save_cmd(interaction: nextcord.Interaction):
	save_json()
	await interaction.response.send_message(embed=validation_embed("Le fichier de configuration a été sauvegardé"), ephemeral=True)


@config_cmd.subcommand(name="reload", description="Permet de recharger le fichier de configuration")
@check_bot_owner()
async def config_save_cmd(interaction: nextcord.Interaction):
	load_json()
	await interaction.response.send_message(embed=validation_embed("Le fichier de configuration a été rechargé"), ephemeral=True)


@config_cmd.subcommand(name="settings", description="Permet de définir certains paramètres")
@application_checks.has_permissions(administrator=True)
async def config_settings_cmd(interaction: nextcord.Interaction,
		max_projects: int = nextcord.SlashOption(name="max-projets", description="Définir le maximum de projets par membre", required=False)):
	config = data["config"]
	if max_projects is None:
		lines = []
		for setting in (("max-projects", "Nombre de projets maximum"),):
			lines.append(f"{setting[1]}: {config[setting[0]]}")
		await interaction.response.send_message(embed=normal_embed("\n".join(lines), "Paramètres actuels :"), ephemeral=True)
	else:
		if max_projects is not None:
			config["max-projects"] = max_projects
		save_json()
		await interaction.response.send_message(embed=validation_embed("Les paramètres ont été modifiés"), ephemeral=True)


@tasks.loop(minutes=1)
async def kick_not_accept_rules():
	for member_id, kick_time in [x for x in data['join_not_rules'].items()]:
		member = main_guild.get_member(int(member_id))
		if not member:
			del (data['join_not_rules'][member_id])
			continue

		if time.time() >= kick_time:
			mp_embed = nextcord.Embed(title="Vous avez été éjecté du serveur Dev-TryBranch", color=embed_color)
			mp_embed.set_author(name="Dev-TryBranch", icon_url=main_guild.icon.url)
			mp_embed.add_field(name='Raison',
				value="Vous n'avez pas accepté les règles après 2 heures.\nVous pouvez revenir avec [ce lien](https://discord.com/invite/KTHh2KDejy) et retenter votre chance.")
			mp_embed.timestamp = get_timestamp()
			await send_dm(member, embed=mp_embed)
			await main_guild.kick(member, reason="Règles non acceptées après 2 heures")
			del (data['join_not_rules'][member_id])


@tasks.loop(seconds=15)
async def status_change():
	await bot.change_presence(status=nextcord.Status.online,
		activity=nextcord.Activity(type=status_msg[1][status_msg[0]][0],
			name=super_replace(status_msg[1][status_msg[0]][1], {
				'%members%': str(len(main_guild.humans))})))
	status_msg[0] += 1
	if status_msg[0] > len(status_msg[1]) - 1:
		status_msg[0] = 0


@bot.event
async def on_raw_reaction_add(payload):
	msg_id = payload.message_id
	channel = bot.get_channel(payload.channel_id)
	message = await channel.fetch_message(msg_id)
	guild_id = payload.guild_id
	guild = bot.get_guild(guild_id)
	member = payload.member
	reaction_emoji = payload.emoji

	if not member:
		return

	if member == bot.user:
		return

	msg_id_str = str(msg_id)
	if msg_id_str in data['roleonreact'].keys():
		if str(reaction_emoji) in data['roleonreact'][msg_id_str].keys():
			role = guild.get_role(data['roleonreact'][msg_id_str][str(reaction_emoji)])
			await member.add_roles(role, reason="Rôle-réaction")


@bot.event
async def on_raw_reaction_remove(payload):
	msg_id = payload.message_id
	guild_id = payload.guild_id
	guild = bot.get_guild(guild_id)
	msg_id_str = str(msg_id)
	member = guild.get_member(payload.user_id)
	if not member:
		return
	if msg_id_str in data['roleonreact'].keys():
		reaction_emoji = payload.emoji
		if str(reaction_emoji) in data['roleonreact'][msg_id_str].keys():
			role = guild.get_role(data['roleonreact'][msg_id_str][str(reaction_emoji)])
			await member.remove_roles(role, reason="Rôle-réaction")


@bot.event
async def on_member_join(member):
	if member.guild == main_guild:
		if member.bot:
			bot.loop.create_task(member.add_roles(988881883100217396))
		else:
			bot.loop.create_task(send_welcome(member))
			bot.loop.create_task(update_stats())
			data["join_not_rules"][str(member.id)] = time.time() + 7200
			save_json()


@bot.event
async def on_member_remove(member):
	if member.guild == main_guild and (not member.bot):
		bot.loop.create_task(send_quit(member))
		bot.loop.create_task(update_stats())
		bot.loop.create_task(remove_reactionroles_reactions(member))


async def startup_tasks():
	bot.add_modal(ProjectTopicModal())
	bot.add_modal(ProjectTopicEditModal())
	bot.add_view(CreateProjectView())
	bot.add_view(RulesAcceptView())

	# await bot.get_channel(988778342457147402).send(embed=nextcord.Embed(title="Créer un projet", color=embed_color, description="Pour créer un salon pour votre projet, veuillez cliquer sur ce bouton ou utilisez la commande `/project create`.\nVous pouvez ensuite le modifier avec la commande `/project edit`"), view=CreateProjectView())
	# print(await bot.get_channel(988898926507720754).create_invite(reason="Création d'un lien d'invitation permanent"))
	bot.loop.create_task(update_stats())
	kick_not_accept_rules.start()
	status_change.start()


startup_tasks.launched = False


@bot.event
async def on_ready():
	global main_guild, projects_categ, welcome_channel, rules_msg, member_role

	main_guild = bot.get_guild(988543675640455178)
	projects_categ = main_guild.get_channel(988777897550573599)
	welcome_channel = main_guild.get_channel(988882460601372784)

	rules_msg = await main_guild.get_channel(988878746096377947).fetch_message(988891271198289970)

	member_role = main_guild.get_role(988878382903214151)

	print(f"@{bot.user} s'est connecté sur Discord.")

	if not startup_tasks.launched:
		startup_tasks.launched = True
		await startup_tasks()


bot.run(TOKEN)
