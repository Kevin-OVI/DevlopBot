from functools import wraps

import nextcord
from mcstatus import JavaServer
from nextcord.ext import commands

from python_utils import *

default_errors = {
    "invalidcommand": f"❌ La commande est invalide.",
    'permerr': "❌ Vous n'avez pas la permission d'exécuter cette commande.",
    'invalidargs': f"Arguments invalides.",
    'missingarg': f"Il manque un ou plusieurs arguments.",
    'error': 'Il y a eu une erreur inconnue.',
    'botpermerr': "Le bot n'a pas la permission de faire cette action",
    'disabledcommand': "La commande est désactivée"}

check_predicates = {}

def get_name(member):
    return member.display_name


async def send_dm(user, *args, **kwargs):
    if not user.dm_channel:
        await user.create_dm()
    return await user.dm_channel.send(*args, **kwargs)

async def try_send_dm(user, *args, **kwargs):
    try:
        return await send_dm(user, *args, **kwargs)
    except nextcord.errors.HTTPException:
        return


async def try_reply(message_reply, message, error_channel=None):
    try:
        await send_big_msg(error_channel if error_channel else message_reply.channel, message, message_reply)
    except:
        await send_big_msg(error_channel if error_channel else message_reply.channel, message)


def mention2id(metiontext):
    return int(super_replace(metiontext, {"<": "", "@": "", "!": "", ">": "", '&': '', '#': ''}))


def has_permissions(member, channel, **perms):
    invalid = set(perms) - set(nextcord.Permissions.VALID_FLAGS)
    if invalid:
        raise TypeError('Invalid permission(s): %s' % (', '.join(invalid)))
    return not [perm for perm, value in perms.items() if getattr(channel.permissions_for(member), perm) != value]


def has_guild_permissions(member, **perms):
    invalid = set(perms) - set(nextcord.Permissions.VALID_FLAGS)
    if invalid:
        raise TypeError('Invalid permission(s): %s' % (', '.join(invalid)))
    return not [perm for perm, value in perms.items() if getattr(member.guild_permissions, perm) != value]


async def send_big_msg(channel, msg, message_reply=None):
    if message_reply:
        part = msg[:1995]
        msg = msg[1995:]
        if part.count('```') % 2 == 1:
            part += '```'
            msg = '```' + msg
        await message_reply.reply(part)
    while msg:
        part = msg[:1995]
        msg = msg[1995:]
        if part.count('```') % 2 == 1:
            part += '```'
            msg = '```' + msg

        await channel.send(part)

def get_message_link(message):
    return f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"


def message2dict(message):
    message_json = message.to_message_reference_dict()
    message_json['content'] = message.content
    message_json['embeds'] = [x.to_dict() for x in message.embeds]
    message_json['attachments'] = [x.url for x in message.attachments]
    message_json['author_id'] = message.author.id
    message_json['is_dm'] = message.channel.__class__ == nextcord.DMChannel
    message_json['created_at'] = message.created_at.timestamp()
    edited_at = message.edited_at
    if edited_at:
        message_json['edited_at'] = edited_at.timestamp()
    else:
        message_json['edited_at'] = None

    return message_json


def still_on_guild(member_id, guild):
    return guild.get_member(member_id) is not None

def embed_message(description, color, title=nextcord.Embed.Empty):
    return nextcord.Embed(description=description, color=color, title=title)

def check_run(predicate):
    def deco(func):
        @wraps(func)
        async def overwrite(ctx, *args, **kwargs):
            if predicate(ctx):
                await func(ctx, *args, **kwargs)
            else:
                raise commands.errors.CheckFailure("Custom check failed")

        if overwrite not in check_predicates.keys():
            check_predicates[overwrite] = []
        check_predicates[overwrite].append(predicate)
        return overwrite

    deco.predicate = predicate
    return deco

def can_run(func, ctx):
    return False not in [x(ctx) for x in check_predicates.get(func, [])]

def has_permissions_run(**perms):
    return check_run(lambda ctx: has_permissions(ctx.author, ctx.channel, **perms))

def has_guild_permissions_run(**perms):
    return check_run(lambda ctx: has_guild_permissions(ctx.author, **perms))


async def get_server_status_embeds(servers):
    timestamp = get_timestamp()
    embeds = []
    servers_status = {}
    for name, data in servers.items():
        ip = data['ip']
        image = data.get("image")
        embed = nextcord.Embed(title=f"Statut du {name}", timestamp=timestamp)
        if image is not None:
            embed.set_thumbnail(url=image)

        try:
            status = (await (await JavaServer.async_lookup(ip)).async_status()).raw

            servers_status[name] = {'online': True, 'players': {"online": status['players']['online'], "max": status['players']['max'], "sample": status['players'].get('sample', [])}}
            embed.colour = 0x00FF00
            embed.add_field(name="Status", value="En ligne", inline=False)
            players = f"**{status['players']['online']}/{status['players']['max']}**"
            for player in status['players'].get('sample', []):
                players += "\n> " + player['name']
            embed.add_field(name=f"Joueurs", value=players, inline=False)

        except (OSError, ConnectionRefusedError, asyncio.exceptions.TimeoutError):
            servers_status[name] = {'online': False}
            embed.colour = 0xFF0000
            embed.add_field(name="Status", value="Hors ligne", inline=False)
            embed.add_field(name="Joueurs", value=f"--/--", inline=False)

        embeds.append(embed)

    return embeds, servers_status

def get_custom_id(bot_name: str, view: str, button_name: str):
    return f"{bot_name}:{view}:{button_name}".upper()


def get_emoji_url(url):
    url = url.split("?")[0].split("#")[0]
    filename = url.split("/")[-1]
    name = ".".join(filename.split(".")[:-1])
    extention = filename.split(".")[-1].upper()
    content = request.urlopen(request.Request(url, method="GET", headers=headers)).read()
    image = bytes2image(content, (extention, ))
    size = len(content)
    if size > 256000:
        divide = (size / 256000)**0.5
        image = image.resize((int(image.width/divide), int(image.height/divide)))

    return name, image2bytes(image, extention)


async def async_get_emoji_url(url):
    return await AsyncExecReturn(get_emoji_url, (url, ))()


def image2nextcordFile(image, format, filename):
    return nextcord.File(image2bytesIO(image, format), filename=filename)

async def image_link(bot, file: nextcord.File):
    return (await bot.get_channel(895008983209898014).send(file=file)).attachments[0].url

def find_by_tag(bot, username, discriminator):
    return find(bot.get_all_members(), lambda user: user.name == username and user.discriminator == discriminator)


async def autocomplete_duration_noperm(interaction, param):
    if param == "":
        return ["30s", "20m", "5h", "1d", "7d", "1mo"]

    duration_units = ['mo', 'd', 'h', 'm', 's']
    if is_digit(param[-1]):
        return [param + x for x in duration_units]
    else:
        ret = []
        i = -1
        while -i < len(param) and (not is_digit(param[i])):
            i -= 1

        end = param[i+1:].lower()

        for unit in duration_units:
            if unit.startswith(end):
                ret.append(param[:i+1] + unit)

        return ret


async def autocomplete_duration(interaction: nextcord.Interaction, param):
    if param == "":
        return ["perm", "5h", "1d", "7d", "1mo"]

    if "perm".startswith(param.lower()):
        return ["perm"]

    return autocomplete_duration_noperm(interaction, param)

async def get_first_message(channel: nextcord.TextChannel):
    messages = await channel.history(limit=1, oldest_first=True).flatten()
    if messages:
        return messages[0]
    return None

def get_field_id(embed, name):
    for field in embed.fields:
        if field.name == name:
            return field

    return None


class RawRequester:
    API_BASE = 'https://discord.com/api/v9'
    IMAGE_BASE = 'https://cdn.discordapp.com'
    bot_headers = headers_json.copy()
    bot_headers['User-Agent'] = 'DiscordBot (https://github.com/nextcord/nextcord/2.0.0a2) Python/3.9 aiohttp/3.7.4'
    def __init__(self, token):
        self.bot_headers['Authorization'] = f'Bot {token}'

    @async_function
    def send_base_request(self, method: str, url: str, data=None, headers=None):
        return request.urlopen(request.Request(method=method, url=url, data=data, headers=headers)).read()


    async def send_image_request(self, path):
        if not path.startswith("/"):
            path = "/" + path
        url = self.IMAGE_BASE + path
        return await self.send_base_request('GET', url, None, headers)


    async def send_bot_request(self, method: str, path: str, data=None):
        if not path.startswith("/"):
            path = "/" + path
        url = self.API_BASE + path
        if data:
            data = json.dumps(data).encode()

        r = (await self.send_base_request(method, url, data, self.bot_headers)).decode()
        if r:
            return json.loads(r)
