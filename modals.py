from typing import Optional

import nextcord
from nextcord import ui

from variables import bot, bot_name, discord_variables, project_owner_perms
from data_file import projects_data, save_json
from utils import edit_info_message, error_embed, find_project, is_project_channel, send_info_message, send_log, validation_embed


class ProjectTopicModal(ui.Modal):
	modal_name = f"{bot_name}:project_topic"

	def __init__(self, interaction: Optional[nextcord.Interaction] = None):
		description, name, title = None, None, "Création d'un projet"
		if interaction:
			owner_id, project_data = find_project(interaction.channel)
			description = project_data["description"]
			name = project_data["name"]
			title = "Modification d'un projet"

		super().__init__(title, timeout=None, custom_id=self.modal_name)

		self.name_field = ui.TextInput(label="Nom du projet", style=nextcord.TextInputStyle.short,
			custom_id=f"{self.modal_name}:name_field", min_length=3, max_length=32, required=True,
			placeholder="Entrez ici un nom pour votre projet", default_value=name)
		self.add_item(self.name_field)

		self.description_field = ui.TextInput(label="Description du projet", style=nextcord.TextInputStyle.paragraph,
			custom_id=f"{self.modal_name}:description_field", min_length=10, max_length=1024, required=True,
			placeholder="Entrez ici une description pour votre projet", default_value=description)
		self.add_item(self.description_field)

	async def callback(self, interaction):
		await interaction.response.defer(ephemeral=True)
		user_id_str = str(interaction.user.id)
		name = self.name_field.value
		description = self.description_field.value
		channel = await discord_variables.projects_categ.create_text_channel(name=name, overwrites={interaction.user: project_owner_perms},
			topic=f"Projet de {interaction.user.mention}\n\n{description[:988] + '...' if len(description) > 990 else description}", reason="Création d'un projet")
		channel_id_str = str(channel.id)
		projects_data.setdefault(user_id_str, {})
		projects_data[user_id_str][channel_id_str] = {"name": name, "description": description, "members": [], "mutes": [], "held_for_review": False, "archived": False}
		projects_data[user_id_str][channel_id_str]["info_message"] = (await send_info_message(interaction.user, channel)).id
		save_json()
		send_log(f"<@{user_id_str}> a créé le projet [{name}]({channel.jump_url})", "Création d'un projet", {"Description": description})
		await interaction.followup.send(embed=validation_embed(f"Votre projet à été créé : {channel.mention}."), ephemeral=True)


class ProjectTopicEditModal(ProjectTopicModal):
	modal_name = f"{bot_name}:project_topic_edit"

	async def callback(self, interaction):
		channel = interaction.channel
		if channel is None:
			await interaction.response.send_message(embed=error_embed("Impossible de détecter le salon du projet."), ephemeral=True)
		else:
			if not is_project_channel(channel):
				await interaction.response.send_message(embed=error_embed("Cette action n'est possible que dans un salon de projet."), ephemeral=True)

			r = find_project(interaction.channel)
			if r is None:
				await interaction.response.send_message(embed=error_embed("Le projet n'a pas été trouvé ! Il a peut-être été supprimé par un administrateur."), ephemeral=True)
				return
			owner_id, project_data = r
			name = self.name_field.value
			description = self.description_field.value

			bot.loop.create_task(interaction.channel.edit(name=name,
				topic=f"Projet de <@{owner_id}>\n\n{description[:988] + '...' if len(description) > 990 else description}", reason="Modification d'un projet"))

			old_name = project_data["name"]
			old_desctiption = project_data["description"]
			project_data["name"] = name
			project_data["description"] = description
			bot.loop.create_task(edit_info_message(owner_id, channel))
			save_json()
			fields = {"Description": description}
			if old_name != name:
				fields["Ancien nom"] = old_name
			if old_desctiption != description:
				fields["Ancienne description"] = old_desctiption
			send_log(f"{interaction.user.mention} a modifié le projet [{name}]({channel.jump_url}) de <@{owner_id}>", "Modification d'un projet", fields)
			embed = validation_embed(f"Votre projet à été modifié.")
			embed.set_footer(text="Le nom et la description du salon peuvent prendre quelques minutes à se modifier, à cause des ratelimits de discord.")
			await interaction.response.send_message(embed=embed, ephemeral=True)
