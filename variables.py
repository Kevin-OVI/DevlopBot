import os

import nextcord
from dotenv import load_dotenv
from nextcord.ext import commands

load_dotenv()

bot_name = "devlopbot"
embed_color = 0xAD1457

project_ignore_channels = (988778342457147402, 988780418365014026)
project_member_perms = nextcord.PermissionOverwrite(create_private_threads=True, create_public_threads=True, embed_links=True,
	attach_files=True, manage_threads=True, manage_messages=True, use_slash_commands=True)
project_owner_perms = nextcord.PermissionOverwrite.from_pair(*project_member_perms.pair())
project_owner_perms.update(view_channel=True)
project_mute_perms = nextcord.PermissionOverwrite(send_messages=False, use_slash_commands=False, send_messages_in_threads=False,
	create_public_threads=False, create_private_threads=False, add_reactions=False)

bot = commands.Bot(intents=nextcord.Intents(guilds=True, members=True, reactions=True, messages=True), status=nextcord.Status.idle,
	activity=nextcord.Activity(type=nextcord.ActivityType.playing, name="démarrer..."))


class DiscordVariables(commands.Cog):
	main_guild: nextcord.Guild
	projects_categ: nextcord.CategoryChannel
	revision_categ: nextcord.CategoryChannel
	welcome_channel: nextcord.TextChannel
	logs_channel: nextcord.TextChannel
	member_stats_channel: nextcord.VoiceChannel
	projects_stats_channel: nextcord.VoiceChannel
	member_role: nextcord.Role
	moderator_role: nextcord.Role
	rules_msg: nextcord.Message

	@commands.Cog.listener()
	async def on_ready(self):
		self.main_guild = bot.get_guild(988543675640455178)
		self.projects_categ = self.main_guild.get_channel(988777897550573599)
		self.revision_categ = self.main_guild.get_channel(989846265347047444)
		self.welcome_channel = self.main_guild.get_channel(988882460601372784)
		self.logs_channel = self.main_guild.get_channel(int(os.getenv("LOG_CHANNEL")))
		self.member_stats_channel = self.main_guild.get_channel(988887221262221342)
		self.projects_stats_channel = self.main_guild.get_channel(989628843629355149)
		self.member_role = self.main_guild.get_role(988878382903214151)
		self.moderator_role = self.main_guild.get_role(988818143453519954)
		self.rules_msg = await self.main_guild.get_channel(988878746096377947).fetch_message(988891271198289970)


discord_variables = DiscordVariables()
