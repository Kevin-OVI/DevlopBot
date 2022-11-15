from nextcord.ext import commands


class DiscordNewsPingerCog(commands.Cog):
	@commands.Cog.listener()
	async def on_message(self, message):
		if message.author.id == 1040557268359450645:
			await message.channel.send(f"<@&1042104450539589713>\n{message.content}", delete_after=2)
