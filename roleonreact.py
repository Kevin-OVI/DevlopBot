import nextcord
from nextcord.ext import application_checks, commands

from variables import bot, guild_ids
from data_file import data, save_json


class RoleOnReactCog(commands.Cog):
	@nextcord.slash_command(name="roleonreact", guild_ids=guild_ids)
	async def roleonreact_cmd(self, interaction: nextcord.Interaction):
		pass

	@roleonreact_cmd.subcommand(name="add", description="Permet d'ajouter un rôle-réaction")
	@application_checks.has_permissions(administrator=True)
	async def roleonreact_add_cmd(self, interaction,
			message_id: str = nextcord.SlashOption(name="message_id", description="L'identifiant du message auquel ajouter le role-réaction", required=True),
			reaction: str = nextcord.SlashOption(name="reaction", description="La réaction à ajouter", required=True),
			role: nextcord.Role = nextcord.SlashOption(name="role", description="Le rôle à ajouter", required=True)):
		section = data['roleonreact']
		try:
			message = await interaction.channel.fetch_message(message_id)
			await message.add_reaction(reaction)
			section.setdefault(message_id, {})
			section[message_id][reaction] = role.id
			await interaction.response.send_message('Le role sur réaction a été ajouté', ephemeral=True)
			save_json()
		except nextcord.errors.NotFound:
			await interaction.response.send_message("Le message est introuvable", ephemeral=True)
		except AttributeError:
			await interaction.response.send_message("La réaction n'exite pas", ephemeral=True)

	@roleonreact_cmd.subcommand(name="remove", description="Permet de supprimer un rôle-réaction")
	@application_checks.has_permissions(administrator=True)
	async def roleonreact_remove_cmd(self, interaction,
			message_id: str = nextcord.SlashOption(name="message_id", description="L'identifiant du message duquel supprimer le role-réaction", required=True),
			reaction: str = nextcord.SlashOption(name="reaction", description="La réaction à supprimer", required=True)):
		section = data['roleonreact']
		try:
			if message_id in section.keys():
				if reaction in section[message_id].keys():
					del (section[message_id][reaction])

				if not section[message_id]:
					del (section[message_id])
			save_json()
			await interaction.response.send_message("Le rôle-réaction a été supprimé", ephemeral=True)

		except nextcord.errors.NotFound:
			await interaction.response.send_message("Le message est introuvable", ephemeral=True)
		except AttributeError:
			await interaction.response.send_message("La réaction n'existe pas", ephemeral=True)

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
	async def on_member_remove_accepted_rules(self, member):
		for channel in member.guild.text_channels:
			for message_id in data['roleonreact']:
				for emoji_str in data['roleonreact'][message_id]:
					try:
						message = await channel.fetch_message(message_id)
						if message:
							await message.remove_reaction(emoji_str, member)
					except nextcord.errors.NotFound:
						pass
