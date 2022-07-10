import os
import sys
import traceback

import nextcord

from bot_role_adder import BotRoleAdderCog
from data_file import ConfigCog
from discord_utils import default_errors
from rules import RulesCog
from roleonreact import RoleOnReactCog
from project import ProjectCog
from utils import normal_embed
from welcome_messages import WelcomeMessagesCog
from sendspecial import SendSpecialCog
from tasks import TasksCog
from tickets import TicketsCog
from variables import bot, discord_variables


@bot.event
async def on_application_command_error(ctx, error):
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


@bot.event
async def on_ready():
	print(f"@{bot.user} s'est connecté sur Discord.")


bot.add_cog(discord_variables)
bot.add_cog(TasksCog())
bot.add_cog(ProjectCog())
bot.add_cog(RoleOnReactCog())
bot.add_cog(RulesCog())
bot.add_cog(ConfigCog())
bot.add_cog(WelcomeMessagesCog())
bot.add_cog(SendSpecialCog())
bot.add_cog(TicketsCog())
bot.add_cog(BotRoleAdderCog())
bot.run(os.getenv('TOKEN_DEVLOPBOT'))
