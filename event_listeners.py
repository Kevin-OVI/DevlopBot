import sys
import time
import traceback

import nextcord
from nextcord.ext import commands

from async_tasks import task_project_perms, task_remove_reactionroles_reactions, task_send_quit, task_send_welcome
from data_file import data, save_json
from discord_utils import default_errors
from utils import edit_info_message, find_project, get_id_str, normal_embed
from variables import bot, discord_variables


class EventCog(commands.Cog):
	@commands.Cog.listener()
	async def on_ready(self):
		print(f"@{bot.user} s'est connecté sur Discord.")

	@commands.Cog.listener()
	async def on_raw_reaction_add(self, payload):
		guild = bot.get_guild(payload.guild_id)
		member = payload.member
		reaction_emoji = str(payload.emoji)

		if not member:
			return

		if member == bot.user:
			return

		msg_id_str = str(payload.message_id)
		if msg_id_str in data['roleonreact'].keys():
			if reaction_emoji in data['roleonreact'][msg_id_str].keys():
				role = guild.get_role(data['roleonreact'][msg_id_str][reaction_emoji])
				await member.add_roles(role, reason="Rôle-réaction")


	@commands.Cog.listener()
	async def on_raw_reaction_remove(self, payload):
		guild = bot.get_guild(payload.guild_id)
		msg_id_str = str(payload.message_id)
		member = guild.get_member(payload.user_id)
		reaction_emoji = str(payload.emoji)

		if not member:
			return

		if msg_id_str in data['roleonreact'].keys():

			if reaction_emoji in data['roleonreact'][msg_id_str].keys():
				role = guild.get_role(data['roleonreact'][msg_id_str][reaction_emoji])
				await member.remove_roles(role, reason="Rôle-réaction")

	@commands.Cog.listener()
	async def on_member_join(self, member):
		if member.guild == discord_variables.main_guild:
			if member.bot:
				bot.loop.create_task(member.add_roles(988881883100217396))
			else:
				data["join_not_rules"][str(member.id)] = time.time() + 7200
				save_json()

	@commands.Cog.listener()
	async def on_member_remove(self, member):
		if member.guild == discord_variables.main_guild and (not member.bot):
			member_id_str = get_id_str(member)
			if member_id_str in data['join_not_rules']:
				del (data['join_not_rules'][member_id_str])
			else:
				bot.loop.create_task(task_send_quit(member))
				bot.loop.create_task(task_remove_reactionroles_reactions(member))
				task_project_perms(member, True)


	@commands.Cog.listener()
	async def on_application_command_error(self, ctx, error):
		function = ctx.followup.send if ctx.response.is_done() else ctx.response.send_message
		if isinstance(error, nextcord.errors.ApplicationCheckFailure):
			await function(embed=normal_embed(default_errors['permerr']), ephemeral=True)

		else:
			if hasattr(error, 'original'):
				error = error.original
			form = "".join(traceback.format_exception(type(error), error, error.__traceback__))
			try:
				await function(embed=normal_embed(default_errors['error'] + '\n```' + form.strip().split("\n")[-1] + '```'), ephemeral=True)
			except nextcord.errors.NotFound:
				pass
			print(form, file=sys.stderr)


	@commands.Cog.listener()
	async def on_raw_message_delete(self, payload):
		if payload.guild_id == discord_variables.main_guild.id:
			r = find_project(payload.channel_id)
			if r is not None:
				owner_id, project_data = r
				if payload.message_id == project_data["info_message"]:
					await edit_info_message(owner_id, payload.channel_id)


	@commands.Cog.listener()
	async def on_rules_accept(self, member):
		bot.loop.create_task(task_send_welcome(member))
		task_project_perms(member, False, True)
