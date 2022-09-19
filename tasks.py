import nextcord
from nextcord.ext import commands, tasks

from data_file import projects_data
from python_utils import super_replace
from variables import bot, discord_variables


class TasksCog(commands.Cog):
	messages = (
		(nextcord.ActivityType.playing, "coder"),
		(nextcord.ActivityType.listening, f'les commandes slash'),
		(nextcord.ActivityType.watching, "%members% membres")
	)

	def __init__(self):
		self.state_index = 0
		self.started = False

	@commands.Cog.listener()
	async def on_ready(self):
		if not self.started:
			self.started = True
			bot.dispatch("first_ready")

	@commands.Cog.listener()
	async def on_first_ready(self):
		self.status_change.start()
		self.update_stats.start()

	@tasks.loop(seconds=15)
	async def status_change(self):
		current_state = self.messages[self.state_index]
		await bot.change_presence(status=nextcord.Status.online, activity=nextcord.Activity(type=current_state[0],
			name=super_replace(current_state[1], {'%members%': str(len(discord_variables.main_guild.humans))})))
		self.state_index += 1
		if self.state_index >= len(self.messages):
			self.state_index = 0

	@tasks.loop(minutes=10)
	async def update_stats(self):
		new_name = f"👨・{len(discord_variables.main_guild.humans)} membres"
		if discord_variables.member_stats_channel.name != new_name:
			await discord_variables.member_stats_channel.edit(name=new_name, reason="Mise à jour des statistiques")

		total_projets = 0
		for projets in projects_data.values():
			total_projets += len(projets)
		new_name = f"⌨️・{total_projets} projets"
		if discord_variables.projects_stats_channel.name != new_name:
			await discord_variables.projects_stats_channel.edit(name=new_name, reason="Mise à jour des statistiques")
