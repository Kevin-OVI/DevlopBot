import nextcord
from nextcord.ext import application_checks, commands

from project import CreateProjectView
from roles import ModifyRolesView
from tickets import CreateTicketView
from utils import normal_embed
from variables import guild_ids


async def send_create_project(channel):
	await channel.send(embed=normal_embed("Pour créer un salon pour votre projet, veuillez cliquer sur ce bouton ou utilisez la commande `/project create`.\n\
Vous pouvez ensuite le modifier avec la commande `/project edit`", "Créer un projet"), view=CreateProjectView())


async def send_create_ticket(channel):
	await channel.send(embed=normal_embed("Pour ouvrir un ticket, utilisez le sélecteur ci-dessous ou exécutez la commande `/ticket create`", "Ouvrir un ticket"),
		view=CreateTicketView())


async def send_select_roles(channel):
	await channel.send(embed=normal_embed("Appuyez sur un bouton ci-dessous pour sélectionner vos rôles de Langages ou vos rôles de Notification", "Sélectionnez vos rôles"),
		view=ModifyRolesView())


class SendSpecialCog(commands.Cog):
	commands_map = {
		"create project": send_create_project,
		"create ticket": send_create_ticket,
		"select roles": send_select_roles
	}

	@nextcord.slash_command(name="send-special", description="Permet d'envoyer un message spécial", guild_ids=guild_ids,
		default_member_permissions=nextcord.Permissions(administrator=True))
	@application_checks.has_permissions(administrator=True)
	async def send_special_cmd(self, interaction,
			message: str = nextcord.SlashOption(name="message", description="Le message à envoyer", required=True, choices=commands_map.keys())):
		await self.commands_map[message](interaction.channel)
		await interaction.response.send_message("Le message a été envoyé", ephemeral=True)
