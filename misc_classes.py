import nextcord
from nextcord import ui


class ConfirmationView(ui.View):
	def __init__(self):
		super().__init__(timeout=30)
		self.value = None

	@ui.button(label="Confirmer", emoji="✅", style=nextcord.ButtonStyle.green)
	async def yes_button(self, button, interaction):
		self.value = True
		self.stop()

	@ui.button(label="Annuler", emoji="❌", style=nextcord.ButtonStyle.gray)
	async def no_button(self, button, interaction):
		self.value = False
		self.stop()
