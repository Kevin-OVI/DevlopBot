import time

import nextcord
from nextcord.ext import commands, tasks

from data_file import data, projects_data, save_json
from discord_utils import send_dm
from modals import ProjectTopicEditModal, ProjectTopicModal
from python_utils import get_timestamp, super_replace
from variables import bot, discord_variables, embed_color
from views import CreateProjectView, ReviewView, RulesAcceptView


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
			self.kick_not_accept_rules.start()
			self.status_change.start()
			self.update_stats.start()

			bot.add_modal(ProjectTopicModal())
			bot.add_modal(ProjectTopicEditModal())
			bot.add_view(CreateProjectView())
			bot.add_view(RulesAcceptView())
			bot.add_view(ReviewView())

	@tasks.loop(minutes=1)
	async def kick_not_accept_rules(self):
		section = data['join_not_rules']
		save = False
		for member_id, kick_time in [x for x in section.items()]:
			member = discord_variables.main_guild.get_member(int(member_id))
			if not member:
				del (section[member_id])
				save = True
				continue

			if time.time() >= kick_time:
				mp_embed = nextcord.Embed(title="Vous avez été éjecté du serveur Dev-TryBranch", color=embed_color)
				mp_embed.set_author(name="Dev-TryBranch", icon_url=discord_variables.main_guild.icon.url)
				mp_embed.add_field(name='Raison',
					value="Vous n'avez pas accepté les règles après 2 heures.\nVous pouvez revenir avec [ce lien](https://discord.com/invite/KTHh2KDejy) et retenter votre chance.")
				mp_embed.timestamp = get_timestamp()
				await send_dm(member, embed=mp_embed)
				await discord_variables.main_guild.kick(member, reason="Règles non acceptées après 2 heures")
				del (section[member_id])
				save = True
		if save:
			save_json()

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
