from python_utils import ConfigDict

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
