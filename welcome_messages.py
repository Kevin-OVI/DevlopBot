import nextcord
from nextcord.ext import commands

from variables import discord_variables, embed_color


class WelcomeMessagesCog(commands.Cog):
	@commands.Cog.listener()
	async def on_member_remove_accepted_rules(self, member):
		quit_msg = nextcord.Embed(color=embed_color, title=f"Au revoir {member}",
			description=f"{member.mention} a malhereusement quitté le serveur. On espère le revoir vite :cry:")
		quit_msg.set_footer(text=f"Le serveur ne compte plus que {len(member.guild.humans)} membres")
		quit_msg.set_thumbnail(url=member.display_avatar.url)
		await discord_variables.welcome_channel.send(embed=quit_msg)

	@commands.Cog.listener()
	async def on_rules_accept(self, member):
		welcome_msg = nextcord.Embed(color=embed_color, title=f"Bienvenue {member}", description=f"**Bienvenue {member.mention} sur {member.guild.name} !** \n\n\
Vous pouvez créer votre projet dans le <#988778342457147402> ou consulter les projets déjà existants.\n\
Vous pouvez également aller choisir vos rôles dans le <#988785247900565545>.")
		welcome_msg.set_footer(text=f"Le serveur compte maintenant {len(member.guild.humans)} membres !")
		welcome_msg.set_thumbnail(url=member.display_avatar.url)
		await discord_variables.welcome_channel.send(embed=welcome_msg)
