from typing import Dict, Optional

import nextcord
from nextcord import ui
from nextcord.ext import commands

from utils import normal_embed
from variables import bot_name, discord_variables, bot


class ModifyRolesView(ui.View):
	view_name = f"{bot_name}:modify_roles"

	def __init__(self):
		super().__init__(timeout=None)

	@ui.button(label="Modifier ses rôles langages", emoji="💻", custom_id=f"{view_name}:edit_language_roles_button")
	async def edit_language_roles_button(self, button, interaction: nextcord.Interaction):
		await interaction.response.send_message(embed=normal_embed("Sélectionnez les languages que vous maitrisez", "Sélectionnez vos rôles"),
												view=RolesDropdownView(LanguageRolesDropdown(interaction.user)), ephemeral=True)

	@ui.button(label="Modifier ses rôles notification", emoji="🔔", custom_id=f"{view_name}:edit_notif_roles_button")
	async def edit_notif_roles_button(self, button, interaction: nextcord.Interaction):
		await interaction.response.send_message(embed=normal_embed("Sélectionnez les notifications auquelles vous souhaitez être mentionnés", "Sélectionnez vos rôles"),
												view=RolesDropdownView(NotifRolesDropdown(interaction.user)), ephemeral=True)


class RolesDropdown(ui.Select):
	def __init__(self, roles_dic, custom_id, placeholder, user: Optional[nextcord.Member]):
		self.roles_dic = roles_dic
		roles = [nextcord.SelectOption(label=name, description=role_data.get("description"), emoji=role_data.get("emoji"),
			default=False if user is None else (role_data["role"] in user.roles)) for name, role_data in roles_dic.items()]
		super().__init__(placeholder=placeholder, min_values=0, max_values=len(roles), options=roles, custom_id=custom_id)

	async def callback(self, interaction: nextcord.Interaction):
		roles = {self.roles_dic[i]["role"] for i in self.values}
		current_roles = set(interaction.user.roles)
		roles_total = {x["role"] for x in self.roles_dic.values()}
		unchecked_roles = (roles_total - roles)
		new_roles = list((current_roles - unchecked_roles) | roles)
		await interaction.user.edit(roles=new_roles, reason="Selection des rôles")
		await interaction.response.send_message("Vos rôles ont été modifiés.", ephemeral=True)


class LanguageRolesDropdown(RolesDropdown):
	def __init__(self, user=None):
		super().__init__(RolesCog.language_roles_dic, "language_roles_dropdown", "Sélectionnez vos rôles de Langages", user)


class NotifRolesDropdown(RolesDropdown):
	def __init__(self, user=None):
		super().__init__(RolesCog.notif_roles_dic, "notif_roles_dropdown", "Sélectionnez vos rôles de Notifications", user)


class RolesDropdownView(ui.View):
	def __init__(self, dropdown: RolesDropdown):
		super().__init__(timeout=None)
		self.add_item(dropdown)


class RolesCog(commands.Cog):
	language_roles_dic: Dict[str, nextcord.Role]
	notif_roles_dic: Dict[str, nextcord.Role]

	@commands.Cog.listener()
	async def on_first_ready(self):
		get_role = discord_variables.main_guild.get_role
		self.__class__.language_roles_dic = {
			"Java": {"role": get_role(988871662227308574)},
			"JavaScript": {"role": get_role(988871735694729327)},
			"VB.net / VBS": {"role": get_role(988871774982799480)},
			"Julia": {"role": get_role(988871819975090196)},
			"Python": {"role": get_role(988871856260014140)},
			"C": {"role": get_role(988871895866810378)},
			"C++": {"role": get_role(988871923578601562)},
			"C#": {"role": get_role(988880822725664788)},
			"Assembleur": {"role": get_role(988871951697190953)},
			"Ruby": {"role": get_role(988871954553524264)},
			"Rust": {"role": get_role(988871954805166101)},
			"LolCode": {"role": get_role(988871955857936454)},
			"AppleScript": {"role": get_role(988871956050890813)},
			"Shell / Bash / PowerShell": {"role": get_role(988872142563180556)},
			"Fortran": {"role": get_role(988872144056385566)},
			"PHP": {"role": get_role(988872144899436584)},
			"HTML / CSS": {"role": get_role(988872146006736906)},
			"WLangage": {"role": get_role(988872146732318720)},
			"AutoHotkey": {"role": get_role(989138310708469771)},
			"TypeScript": {"role": get_role(990699698115452960)}
		}
		self.__class__.notif_roles_dic = {
			"Annonces": {
				"role": get_role(995755726016348171),
				"emoji": "📢",
				"description": "Pour être mentionné lorsque nous postons une annonce"
			},
			"Partenatiats": {
				"role": get_role(995755795364982895),
				"emoji": "🤝",
				"description": "Pour être mentionné lors d'un partenatiat"
			},
			"Actualités développeur Discord": {
				"role": get_role(1042104450539589713),
				"emoji": "⚙",
				"description": "Pour être mentionné lors d'une nouvelle actualité discord"
			}
		}

		bot.add_view(ModifyRolesView())
		bot.add_view(RolesDropdownView(LanguageRolesDropdown()))
		bot.add_view(RolesDropdownView(NotifRolesDropdown()))
