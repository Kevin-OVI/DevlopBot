from nextcord.ext import commands

from variables import bot, discord_variables


class BotRoleAdderCog(commands.Cog):
	@commands.Cog.listener()
	async def on_member_join(self, member):
		if member.guild == discord_variables.main_guild:
			if member.bot:
				bot.loop.create_task(member.add_roles(988881883100217396))
