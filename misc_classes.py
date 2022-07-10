import sys
import time
import traceback

import nextcord
from nextcord import ui
from nextcord.ext import commands

from discord_utils import default_errors
from utils import normal_embed

from variables import bot, bot_name, discord_variables, embed_color, guild_ids


class EventCog(commands.Cog):
	@commands.Cog.listener()
	async def on_member_join(self, member):
		if member.guild == discord_variables.main_guild:
			if member.bot:
				bot.loop.create_task(member.add_roles(988881883100217396))


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


class ConfirmationView(ui.View):
	def __init__(self):
		super().__init__(timeout=30)
		self.value = None

	@ui.button(label="Confirmer", emoji="✅", style=nextcord.ButtonStyle.green)
	async def yes_button(self, button, interaction):
		self.value = True
		self.stop()

	@ui.button(label="Annuler", emoji="❌", style=nextcord.ButtonStyle.gray)
	async def no_button(self, button, interaction):
		self.value = False
		self.stop()


class SingleCommandsCog(commands.Cog):
	@nextcord.slash_command(name="ping", description="Affiche la latence du bot", guild_ids=guild_ids)
	async def ping_cmd(self, interaction):
		embed = normal_embed(f"**Latence de l'api discord** : `{round(bot.latency * 1000)}ms`", '<:wifi:895028279478734878> | Temps de réponses :')
		start = time.time()
		await interaction.response.send_message(embed=embed, ephemeral=True)
		msg_latency = time.time() - start
		embed.description += f"\n\n**Temps d'envoi du message** : `{round(msg_latency * 1000)}ms`"
		await interaction.edit_original_message(embed=embed)

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
