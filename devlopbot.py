import os

from commands import ProjectCommandCog, RoleOnReactCommandCog, RulesCommandCog, ConfigCommandCog, SingleCommandsCog
from event_listeners import EventCog
from tasks import TasksCog
from variables import bot, discord_variables

bot.add_cog(discord_variables)
bot.add_cog(EventCog())
bot.add_cog(TasksCog())
bot.add_cog(ProjectCommandCog())
bot.add_cog(RoleOnReactCommandCog())
bot.add_cog(RulesCommandCog())
bot.add_cog(ConfigCommandCog())
bot.add_cog(SingleCommandsCog())
bot.run(os.getenv('TOKEN_DEVLOPBOT'))
