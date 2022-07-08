import nextcord
from nextcord.ext import application_checks, commands

from cache_data import empty_cache
from variables import guild_ids
from python_utils import ConfigDict
from utils import normal_embed, validation_embed

data = ConfigDict('data_devlopbot.json')
projects_data: dict


def save_json():
	data.save()


def load_json():
	global projects_data

	data.reload()

	for x in ("roleonreact", "join_not_rules", "projects", "config"):
		data.setdefault(x, {})

	data["config"].setdefault("max-projects", 2)
	save_json()

	projects_data = data["projects"]


load_json()


class ConfigCog(commands.Cog):
	@nextcord.slash_command(name="config", guild_ids=guild_ids, default_member_permissions=nextcord.Permissions(administrator=True))
	@application_checks.has_permissions(administrator=True)
	async def config_cmd(self):
		pass

	@config_cmd.subcommand(name="save", description="Permet de sauvegarder le fichier de configuration")
	@application_checks.is_owner()
	async def config_save_cmd(self, interaction: nextcord.Interaction):
		save_json()
		await interaction.response.send_message(embed=validation_embed("Le fichier de configuration a été sauvegardé"), ephemeral=True)

	@config_cmd.subcommand(name="reload", description="Permet de recharger le fichier de configuration")
	@application_checks.is_owner()
	async def config_save_cmd(self, interaction: nextcord.Interaction):
		load_json()
		empty_cache()
		await interaction.response.send_message(embed=validation_embed("Le fichier de configuration a été rechargé"), ephemeral=True)

	@config_cmd.subcommand(name="settings", description="Permet de définir certains paramètres")
	@application_checks.has_permissions(administrator=True)
	async def config_settings_cmd(self, interaction: nextcord.Interaction,
			max_projects: int = nextcord.SlashOption(name="max-projets", description="Définir le maximum de projets par membre", required=False)):
		section = data["config"]
		if max_projects is None:
			lines = []
			for config_name, display_name in (("max-projects", "Nombre de projets maximum"),):
				lines.append(f"{display_name}: {section[config_name]}")
			await interaction.response.send_message(embed=normal_embed("\n".join(lines), "Paramètres actuels :"), ephemeral=True)
		else:
			for config_name, command_variable in (("max-projects", max_projects),):
				if command_variable is not None:
					section[config_name] = command_variable
			save_json()
			await interaction.response.send_message(embed=validation_embed("Les paramètres ont été modifiés"), ephemeral=True)
