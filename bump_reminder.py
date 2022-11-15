from typing import Dict

import nextcord
from nextcord.ext import commands

import scheduler
from data_file import data, save_json
from utils import normal_embed, validation_embed
from variables import discord_variables, guild_ids


class BumpReminderCog(commands.Cog):
	def __init__(self):
		self.scheduled_reminders: Dict[int, scheduler.ScheduledTask] = {}

	@nextcord.slash_command(name="bump_reminder", description="Permet d'activer ou de désactiver le rappel de bump", guild_ids=guild_ids)
	async def bump_reminder_cmd(self, interaction: nextcord.Interaction):
		if interaction.user.id in data["bump_reminder_disabled"]:
			data["bump_reminder_disabled"].remove(interaction.user.id)
			save_json()
			await interaction.response.send_message(embed=validation_embed("Le rappel de bump a été réactivé."), ephemeral=True)
		else:
			data["bump_reminder_disabled"].append(interaction.user.id)
			save_json()
			scheduled_reminder = self.scheduled_reminders.get(interaction.user.id)
			if scheduled_reminder is not None:
				scheduled_reminder.cancel()
				del (self.scheduled_reminders[interaction.user.id])
			await interaction.response.send_message(embed=validation_embed("Le rappel de bump a été désactivé."), ephemeral=True)

	@commands.Cog.listener()
	async def on_message(self, message: nextcord.Message):
		interaction = message.interaction
		if interaction is None or message.author.id != 302050872383242240 or interaction.name != "bump":
			return

		interaction_user = interaction.user
		if interaction_user.id not in data["bump_reminder_disabled"]:
			await message.reply(embed=validation_embed(f"Merci d'avoir bumpé notre serveur. Nous allons vous rappeler de le bumper à nouveau dans 2 heures.").set_footer(
				text=f"Rien ne vous oblige de le faire bien sur, vous pouvez désactiver le rappel avec la commande {self.bump_reminder_cmd.get_mention(discord_variables.main_guild)}"),
				delete_after=7200)
			self.scheduled_reminders[interaction.user.id] = scheduler.run_task_later(7200, self.remind_now, message, interaction_user)

	async def remind_now(self, message: nextcord.Message, interaction_user: nextcord.User):
		del (self.scheduled_reminders[interaction_user.id])
		await message.reply(f"{interaction_user.mention} C'est l'heure du </bump:947088344167366698> !", embed=normal_embed(
			f"Rien ne vous oblige de le faire bien sur, vous pouvez désactiver ce rappel avec la commande {self.bump_reminder_cmd.get_mention(discord_variables.main_guild)}"))
