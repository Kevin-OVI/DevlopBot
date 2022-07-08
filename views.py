import nextcord
from nextcord import ui

from data_file import data, save_json
from utils import create_project_start, error_embed, find_project, is_moderator, unhold_for_review, validation_embed
from variables import bot, bot_name, discord_variables


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
	view_name = f"{bot_name}:rules_accept"

	def __init__(self):
		super().__init__(timeout=None)

	@ui.button(label="J'accepte", emoji="<:oui:988807617654702140>", style=nextcord.ButtonStyle.primary, custom_id=f"{view_name}:accept")
	async def accept_button(self, button, interaction):
		if str(interaction.user.id) in data['join_not_rules']:
			del (data['join_not_rules'][str(interaction.user.id)])
			save_json()
			bot.dispatch("rules_accept", interaction.user)
		bot.loop.create_task(interaction.user.add_roles(discord_variables.member_role, reason="Le membre a accepté les règles"))
		await interaction.response.send_message(embed=validation_embed(f"Les règles ont été acceptées. Le rôle {discord_variables.member_role.mention} vous a été ajouté"), ephemeral=True)


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