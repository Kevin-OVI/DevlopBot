from functools import wraps

import nextcord
from nextcord import ui
from nextcord.ext import commands

from cache_data import cache_return
from data_file import save_json, tickets_data
from discord_utils import hidden_pin
from misc_classes import ConfirmationView
from utils import error_embed, get_id_str, get_textchannel, is_user_on_guild, normal_embed, question_embed, validation_embed
from variables import bot, bot_name, discord_variables, guild_ids

ticket_ignore_channels = (995064624712003584,)
ticket_permissions = nextcord.PermissionOverwrite(add_reactions=True, read_messages=True, view_channel=True, send_messages=True,
	embed_links=True, attach_files=True, read_message_history=True, external_emojis=True, external_stickers=True, use_slash_commands=True)


@cache_return()
def is_ticket_channel(channel: nextcord.abc.GuildChannel):
	return channel.category == discord_variables.tickets_categ and channel.id not in ticket_ignore_channels


def check_is_ticket(func):
	@wraps(func)
	async def overwrite(self, interaction, *args, **kwargs):
		if not is_ticket_channel(interaction.channel):
			await interaction.response.send_message(embed=error_embed("La commande ne peut pas être exécutée ici."), ephemeral=True)
			return
		await func(self, interaction, *args, **kwargs)

	return overwrite


class TicketsCog(commands.Cog):
	@nextcord.slash_command(name="ticket", guild_ids=guild_ids)
	async def ticket_cmd(self):
		pass

	@ticket_cmd.subcommand(name='create', description="Permet de créer un ticket")
	async def ticket_create_cmd(self, interaction):
		await create_ticket(interaction)

	@ticket_cmd.subcommand(name="close", description="Permet de fermer un ticket")
	@check_is_ticket
	async def ticket_close_cmd(self, interaction):
		await close_ticket(interaction)

	@ticket_cmd.subcommand(name="add-user", description="Permet d'ajouter un utilisateur à un ticket")
	@check_is_ticket
	async def ticket_add_user_cmd(self, interaction, member: nextcord.Member = nextcord.SlashOption(name="membre", description="Le membre à ajouter au ticket", required=True)):
		ticket_data = tickets_data["channels"][get_id_str(interaction.channel)]
		if member.id in ticket_data["members"]:
			await interaction.response.send_message(embed=error_embed("L'utilisateur est déjà un membre du ticket"), ephemeral=True)
			return
		ticket_data["members"].append(member.id)
		save_json()
		if is_user_on_guild(member):
			bot.loop.create_task(interaction.channel.set_permissions(member, overwrite=ticket_permissions, reason="Ajout d'un membre au ticket"))
		await interaction.response.send_message(embed=validation_embed(f"{member.mention} a été ajouté au ticket"), ephemeral=True)

	@ticket_cmd.subcommand(name="remove-user", description="Permet de retirer un utilisateur à un ticket")
	@check_is_ticket
	async def ticket_remove_user_cmd(self, interaction, member: nextcord.Member = nextcord.SlashOption(name="membre", description="Le membre à retirer du ticket", required=True)):
		ticket_data = tickets_data["channels"][get_id_str(interaction.channel)]
		if member.id not in ticket_data["members"]:
			await interaction.response.send_message(embed=error_embed("L'utilisateur n'est pas un membre du ticket"), ephemeral=True)
			return
		ticket_data["members"].remove(member.id)
		save_json()
		if is_user_on_guild(member):
			bot.loop.create_task(interaction.channel.set_permissions(member, overwrite=None, reason="Retrait d'un membre au ticket"))
		await interaction.response.send_message(embed=validation_embed(f"{member.mention} a été retiré du ticket"), ephemeral=True)

	@commands.Cog.listener()
	async def on_ready(self):
		bot.add_view(CreateTicketView())
		bot.add_view(CloseTicketView())
		bot.add_view(SupportControlsView())

	@commands.Cog.listener()
	async def on_rules_accept(self, member):
		for channel_id, ticket_data in tickets_data["channels"].items():
			if member.id in ticket_data["members"]:
				channel = get_textchannel(channel_id)
				bot.loop.create_task(channel.set_permissions(member, overwrite=ticket_permissions, reason="Ajout d'un membre au ticket lors de l'acceptation des règles"))


class CreateTicketView(ui.View):
	view_name = f"{bot_name}:create_ticket"

	def __init__(self):
		super().__init__(timeout=None)

	@ui.button(label="Créer un ticket", emoji="🎫", style=nextcord.ButtonStyle.primary, custom_id=f"{view_name}:create")
	async def create_button(self, button, interaction):
		await create_ticket(interaction)


class CloseTicketView(ui.View):
	view_name = f"{bot_name}:close_ticket"

	def __init__(self):
		super().__init__(timeout=None)

	@ui.button(label="Fermer le ticket", emoji="🗑️", style=nextcord.ButtonStyle.red, custom_id=f"{view_name}:close")
	async def close_button(self, button, interaction):
		await close_ticket(interaction)


class SupportControlsView(ui.View):
	view_name = f"{bot_name}:support_controls"

	def __init__(self):
		super().__init__(timeout=None)

	@ui.button(label="Réouvrir le ticket", emoji="📤", style=nextcord.ButtonStyle.green, custom_id=f"{view_name}:reopen")
	async def reopen_button(self, button, interaction):
		ticket_data = tickets_data["channels"][get_id_str(interaction.channel)]
		if ticket_data["open"]:
			bot.loop.create_task(interaction.message.delete())
			await interaction.response.send_message("Le ticket est déjà réouvert", ephemeral=True)
			return
		ticket_data["open"] = True
		save_json()
		overwrites = interaction.channel.overwrites
		for member_id in ticket_data["members"]:
			member = discord_variables.main_guild.get_member(member_id)
			if member is not None:
				overwrites[member] = ticket_permissions

		bot.loop.create_task(interaction.message.delete())
		bot.loop.create_task(interaction.channel.edit(overwrites=overwrites, reason=f"Réouverture du ticket"))

		await interaction.response.send_message(embed=normal_embed(f"Le ticket a été réouvert par {interaction.user.mention}"), allowed_mentions=nextcord.AllowedMentions.none())

	@ui.button(label="Supprimer le salon", emoji="❌", style=nextcord.ButtonStyle.red, custom_id=f"{view_name}:delete")
	async def delete_button(self, button, interaction):
		del (tickets_data["channels"][get_id_str(interaction.channel)])
		save_json()
		await interaction.channel.delete(reason="Suppression du ticket")


async def create_ticket(interaction):
	tickets_data["counter"] += 1
	count_str = str(tickets_data["counter"]).zfill(4)
	channel = await discord_variables.tickets_categ.create_text_channel(f"ticket-{count_str}", overwrites={
		discord_variables.main_guild.default_role: nextcord.PermissionOverwrite(view_channel=False),
		discord_variables.support_role: nextcord.PermissionOverwrite(view_channel=True), interaction.user: ticket_permissions}, reason="Création d'un ticket")
	start_embed = normal_embed(f"Bienvenue {interaction.user.mention}, un membre du staff vous répondra au plus vite.\nEn attendant, vous pouvez nous expliquer votre demande.")
	start_embed.add_field(name="Auteur", value=interaction.user.mention, inline=False)
	start_embed.add_field(name="Aide", value="""Pour refermer le ticket, cliquez sur le button ci-dessous ou exécutez la commande `/ticket close`.
Pour ajouter ou retirer un membre de votre ticket, exécutez les commandes `/ticket add <membre>` ou `/ticket remove <membre>`.""", inline=False)
	await interaction.response.send_message(f"Le ticket à été créé: {channel.mention}.", ephemeral=True)
	start_msg = await channel.send(embed=start_embed, view=CloseTicketView())
	tickets_data["channels"][get_id_str(channel)] = {"members": [interaction.user.id], "system_messages": [start_msg.id], "open": True}
	save_json()
	bot.loop.create_task(hidden_pin(start_msg, reason="Épinglage du message d'informations"))


async def close_ticket(interaction):
	ticket_data = tickets_data["channels"][get_id_str(interaction.channel)]
	if not ticket_data["open"]:
		await interaction.response.send_message(embed=error_embed("Le ticket est déjà fermé"), ephemeral=True)
		return

	view = ConfirmationView()
	await interaction.response.send_message(embed=question_embed('Êtes-vous sur de vouloir fermer ce ticket ?'), view=view)
	await view.wait()
	if view.value:
		if not ticket_data["open"]:
			await interaction.edit_original_message(embed=error_embed("Le ticket est déjà fermé"), view=None)
			await interaction.delete_original_message(delay=30)
			return

		ticket_data["open"] = False
		save_json()

		overwrites = interaction.channel.overwrites
		for member_id in ticket_data["members"]:
			member = discord_variables.main_guild.get_member(member_id)
			if member is not None:
				try:
					del (overwrites[member])
				except KeyError:
					pass
		bot.loop.create_task(interaction.channel.edit(overwrites=overwrites, reason=f"Fermeture du ticket"))
		bot.loop.create_task(interaction.channel.send(embed=normal_embed("Contrôles de l'équipe de support"), view=SupportControlsView()))
		await interaction.edit_original_message(embed=normal_embed(f"Ticket fermé par {interaction.user.mention}"), allowed_mentions=nextcord.AllowedMentions.none(), view=None)

	else:
		await interaction.edit_original_message(embed=normal_embed("Fermeture du ticket annulée"), view=None)
		await interaction.delete_original_message(delay=30)
