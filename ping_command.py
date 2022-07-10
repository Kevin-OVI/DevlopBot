import time

import nextcord
from nextcord.ext import commands

from utils import normal_embed
from variables import bot, guild_ids


class PingCommandCog(commands.Cog):
	@nextcord.slash_command(name="ping", description="Affiche la latence du bot", guild_ids=guild_ids)
	async def ping_cmd(self, interaction):
		embed = normal_embed(f"**Latence de l'api discord** : `{round(bot.latency * 1000)}ms`", '<:wifi:895028279478734878> | Temps de réponses :')
		start = time.time()
		await interaction.response.send_message(embed=embed, ephemeral=True)
		msg_latency = time.time() - start
		embed.description += f"\n\n**Temps d'envoi du message** : `{round(msg_latency * 1000)}ms`"
		await interaction.edit_original_message(embed=embed)
