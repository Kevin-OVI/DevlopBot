import os

from data_file import ConfigCog
from rules import RulesCog
from roleonreact import RoleOnReactCog
from project import ProjectCog
from misc_classes import EventCog, SingleCommandsCog, WelcomeMessagesCog
from tasks import TasksCog
from variables import bot, discord_variables


@bot.event
async def on_ready():
	print(f"@{bot.user} s'est connecté sur Discord.")


bot.add_cog(discord_variables)
bot.add_cog(EventCog())
bot.add_cog(TasksCog())
bot.add_cog(ProjectCog())
bot.add_cog(RoleOnReactCog())
bot.add_cog(RulesCog())
bot.add_cog(ConfigCog())
bot.add_cog(SingleCommandsCog())
bot.add_cog(WelcomeMessagesCog())
bot.run(os.getenv('TOKEN_DEVLOPBOT'))
