import io
import json
import time

import nextcord
from nextcord import ui
from nextcord.ext import application_checks, commands, tasks

from data_file import data, save_json
from discord_utils import send_dm
from python_utils import get_timestamp
from utils import get_id_str, validation_embed
from variables import bot, bot_name, discord_variables, embed_color, guild_ids


class RulesAcceptView(ui.View):
	view_name = f"{bot_name}:rules_accept"

	def __init__(self):
		super().__init__(timeout=None)

	@ui.button(label="J'accepte", emoji="<:oui:988807617654702140>", style=nextcord.ButtonStyle.primary, custom_id=f"{view_name}:accept")
	async def accept_button(self, button, interaction):
		if str(interaction.user.id) in data['join_not_rules']:
			del (data['join_not_rules'][str(interaction.user.id)])
			save_json()
			bot.dispatch("rules_accept", interaction.user)
		bot.loop.create_task(interaction.user.add_roles(discord_variables.member_role, reason="Le membre a accepté les règles"))
		await interaction.response.send_message(embed=validation_embed(f"Les règles ont été acceptées. Le rôle {discord_variables.member_role.mention} vous a été ajouté"),
			ephemeral=True)


class RulesCog(commands.Cog):
	@nextcord.slash_command(name="rules", guild_ids=guild_ids)
	async def rules_cmd(self):
		pass

	@rules_cmd.subcommand(name="get", description="Permet d'obtenir le json de l'embed du message des règles")
	@application_checks.has_permissions(administrator=True)
	async def rules_get_cmd(self, interaction):
		f = io.StringIO()
		embeds = discord_variables.rules_msg.embeds
		last_embed = embeds[-1]
		last_embed.remove_footer()
		last_embed.timestamp = None
		json.dump([x.to_dict() for x in embeds], f, ensure_ascii=False, indent=2)
		f.seek(0)
		f = io.BytesIO(f.read().encode())
		await interaction.response.send_message("Voici le json de l'embed des règles", file=nextcord.File(f, filename='rules message.json'), ephemeral=True)

	@rules_cmd.subcommand(name="set", description="Permet de définir le json de l'embed du message des règles")
	@application_checks.has_permissions(administrator=True)
	async def rules_set_cmd(self, interaction,
			rules_file: nextcord.Attachment = nextcord.SlashOption(name="embed", description="Le json de l'embed du message des règles", required=True)):
		jload = json.loads(await rules_file.read())
		if type(jload) == list:
			embeds = [nextcord.Embed.from_dict(x) for x in jload]
		elif type(jload) == dict:
			embeds = [nextcord.Embed.from_dict(jload)]
		else:
			await interaction.response.send_message("Le json doit être une liste d'objets embeds ou un objet embed", ephemeral=True)
			return

		last_embed = embeds[-1]
		last_embed.set_footer(text="Cordialement, l'équipe de Dev-TryBranch", icon_url=discord_variables.main_guild.icon.url)
		last_embed.timestamp = get_timestamp()

		await discord_variables.rules_msg.edit(embeds=embeds, view=RulesAcceptView())
		await interaction.response.send_message("Le message des règles a été modifié", ephemeral=True)

	@commands.Cog.listener()
	async def on_member_join(self, member):
		if member.guild == discord_variables.main_guild:
			if not member.bot:
				data["join_not_rules"][str(member.id)] = time.time() + 7200
				save_json()

	@commands.Cog.listener()
	async def on_member_remove(self, member):
		if member.guild == discord_variables.main_guild and (not member.bot):
			member_id_str = get_id_str(member)
			if member_id_str in data['join_not_rules']:
				del (data['join_not_rules'][member_id_str])
			else:
				bot.dispatch("member_remove_accepted_rules", member)

	@commands.Cog.listener()
	async def on_first_ready(self):
		bot.add_view(RulesAcceptView())
		self.kick_not_accept_rules.start()

	@tasks.loop(minutes=1)
	async def kick_not_accept_rules(self):
		section = data['join_not_rules']
		save = False
		for member_id, kick_time in [x for x in section.items()]:
			member = discord_variables.main_guild.get_member(int(member_id))
			if not member:
				del (section[member_id])
				save = True
				continue

			if time.time() >= kick_time:
				mp_embed = nextcord.Embed(title="Vous avez été éjecté du serveur Dev-TryBranch", color=embed_color)
				mp_embed.set_author(name="Dev-TryBranch", icon_url=discord_variables.main_guild.icon.url)
				mp_embed.add_field(name='Raison',
					value="Vous n'avez pas accepté les règles après 2 heures.\nVous pouvez revenir avec [ce lien](https://discord.com/invite/KTHh2KDejy) et retenter votre chance.")
				mp_embed.timestamp = get_timestamp()
				try:
					await send_dm(member, embed=mp_embed)
					dm_sent = True
				except nextcord.Forbidden:
					dm_sent = False
				await discord_variables.main_guild.kick(member, reason="Règles non acceptées après 2 heures" + ("" if dm_sent else " | ⚠️le mp n'a pas pu être envoyé"))
		if save:
			save_json()
