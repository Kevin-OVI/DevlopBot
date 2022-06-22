import asyncio
import datetime
import emoji
import io
import json
import mimetypes
import os
import posixpath
import random
import string
import time
import urllib
import urllib.parse
from threading import Thread
from urllib import request

from PIL import Image

headers = {'user-agent': 'Mozilla/5.0 (X11; U; Linux i686) Gecko/20071127 Firefox/2.0.0.11'}

headers_json = headers.copy()
headers_json['Content-Type'] =  'application/json'

digits = [x for x in string.digits]
letters = [x for x in string.ascii_letters]
whitespaces = [x for x in string.whitespace]


class InvalidDurationError(ValueError):
	def __init__(self, message: str, duration_str: str, index: int):
		message += ": "
		index += len(type(self).__name__) + 2 + len(message)
		super().__init__(f"{message}{duration_str}\n{' ' * index}^")

class InvalidUnitError(ValueError):
	pass

def is_digit(c):
	return c in digits


def is_letter(c):
	return c in letters


def is_whitespace(c):
	return c in whitespaces


def parse_one_duration(num: int, unit: str):
	unit = unit.lower()
	if unit == "mo":
		return num * 2592000
	elif unit == "d":
		return num * 86400
	elif unit == "h":
		return num * 3600
	elif unit == "m":
		return num * 60
	elif unit == "s":
		return num
	else:
		raise InvalidUnitError("L'unité est invalide: " + unit)


def parse_duration(duration_str: str):
	duration_seconds = 0
	memo_num = ""
	memo_unit = ""
	i = 0
	done_parsing = 0

	for c in duration_str:
		if not is_whitespace(c):
			if is_letter(c):
				if i == 0:
					if not memo_num:
						raise InvalidDurationError("Un nombre est attendu avant l'unité de durée", duration_str, done_parsing-1)
					i = 1
				memo_unit += c
			elif is_digit(c):
				if i == 1:
					unit_error = False
					try:
						duration_seconds += parse_one_duration(int(memo_num), memo_unit)
					except InvalidUnitError:
						unit_error = True
					if unit_error:
						raise InvalidDurationError("L'unité est invalide", duration_str, done_parsing-1)
					memo_num = ""
					memo_unit = ""
					i = 0
				memo_num += c
			else:
				raise InvalidDurationError("Caractère non valide dans la durée", duration_str, done_parsing)

		done_parsing += 1

	if memo_num:
		if memo_unit:
			unit_error = False
			try:
				duration_seconds += parse_one_duration(int(memo_num), memo_unit)
			except InvalidUnitError:
				unit_error = True
			if unit_error:
				raise InvalidDurationError("L'unité est invalide", duration_str, done_parsing-1)
		else:
			raise InvalidDurationError("Une unité de durée est attendue", duration_str, done_parsing)
	else:
		raise InvalidDurationError("Une durée est attendue", duration_str, done_parsing)

	return duration_seconds


def format_duration(duration: int):
	formated = ""
	x, duration = divmod(duration, 2592000)
	if x:
		formated += f"{x} mois "

	x, duration = divmod(duration, 86400)
	if x:
		formated += f"{x} jours "

	x, duration = divmod(duration, 3600)
	if x:
		formated += f"{x} heures "

	x, duration = divmod(duration, 60)
	if x:
		formated += f"{x} minutes "

	if duration:
		formated += f"{duration} secondes "

	return formated[:-1]

def super_replace(s, x):
	for y in x.keys():
		s = s.replace(y, x[y])
	return s

def list2str(iterable, interval=" "):
	return interval.join(iterable)


def startswith_one(s, starts_with):
	return one_match(starts_with, lambda x: s.startswith(x))

def endswith_one(s, ends_with):
	return one_match(ends_with, lambda x: s.endswith(x))

def contains_one(iterable, contains):
	return one_match(contains, lambda x: x in iterable)

def contains_all(iterable, contains):
	return all_match(contains, lambda x: x in iterable)

def contains_none(iterable, contains):
	return none_match(contains, lambda x: x in iterable)

def one_match(iterable, test_func):
	for x in iterable:
		if test_func(x):
			return True
	return False

def all_match(iterable, test_func):
	for x in iterable:
		if not test_func(x):
			return False
	return True

def none_match(iterable, test_func):
	for x in iterable:
		if test_func(x):
			return False
	return True

def get_alphabet():
	return list(string.ascii_lowercase)


def one_chance(out):
	return random.randint(1, out) == 1


def get_timestamp():
	return datetime.datetime.now()


def get_emoji(s):
	return emoji.emojize(s, use_aliases=True)


jours = ('Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche')
mois = (
	'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre',
	'Décembre')


def ctime_fr(t):
	t = list(time.localtime(t))
	if t[2] == 1:
		t[2] = "1er"
	return f'{jours[t[6]]} {t[2]} {mois[t[1] - 1]} {t[0]} {str(t[3]).zfill(2)}:{str(t[4]).zfill(2)}:{str(t[5]).zfill(2)}'

def format_plural(word, num):
	if num != 0 and num != 1:
		return f"{num} {word}s"
	return f"{num} {word}"


def format_time(seconds):
	hours = int(seconds / 3600);
	minutes = int((seconds % 3600) / 60);
	seconds = int((seconds % 3600) % 60);
	s = ""
	if hours != 0:
		s += format_plural("heure", hours)
		if minutes != 0:
			s += " "
			s += format_plural("minute", minutes)
		return s
	if minutes != 0:
		s += format_plural("minute", minutes)
		if seconds != 0:
			s += " "
			s += format_plural("seconde", seconds)
		return s
	if seconds == 0:
		return "1 seconde"
	return format_plural("seconde", seconds)

def get_ascii(text):
	return request.urlopen(request.Request(f"https://artii.herokuapp.com/make?text={urllib.parse.quote(text)}", headers=headers, method='GET')).read().decode()

async def async_get_ascii(text):
	return await AsyncExecReturn(get_ascii, (text,))()

def bytesIO2image(bytesIO, formats):
	return Image.open(bytesIO, formats=formats)

def bytes2image(bytes, formats):
	return bytesIO2image(io.BytesIO(bytes), formats)

def image2bytesIO(image, format):
	byteIo = io.BytesIO()
	image.save(byteIo, format=format)
	byteIo.seek(0)
	return byteIo

def image2bytes(image, format):
	return image2bytesIO(image, format).read()


def multi_pixel(img, multi):
	img_resized = Image.new('RGBA', (multi * img.width, multi * img.height))
	for x in range(multi * img.width):
		for y in range(multi * img.height):
			img_resized.putpixel((x, y), img.getpixel((int(x / multi), int(y / multi))))

	return img_resized

if not mimetypes.inited:
	mimetypes.init()
extensions_map = mimetypes.types_map.copy()
extensions_map.update({
	'': 'application/octet-stream', # Default
	'.py': 'text/plain',
	'.c': 'text/plain',
	'.h': 'text/plain',
})

def guess_type(path):
	base, ext = posixpath.splitext(path)
	if ext in extensions_map:
		return extensions_map[ext]
	ext = ext.lower()
	if ext in extensions_map:
		return extensions_map[ext]
	else:
		return extensions_map['']


def async_function(func):
	async def overwrite(*args, **kwargs):
		return await AsyncExecReturn(func, args, kwargs)()

	return overwrite

def dasha2kwa(args):
	kwargs = {}
	for x in args:
		if x.startswith("-"):
			split = x.split(":")
			kwargs[split[0][1:]] = ":".join(split[1:])
	return kwargs

def find(iterable, condition):
	found = find_all(iterable, condition)
	return None if not found else found[0]

def find_all(iterable, condition):
	return [x for x in iterable if condition(x)]

"""def translate(string, to_lang, from_lang="auto", api="http://localhost:40000/translate"):
	data = json.dumps({"q": string, "source": from_lang, "target": to_lang, "format": "text"}).encode('utf-8')
	return json.loads(request.urlopen(request.Request(api, data=data, method="POST", headers={'content-type': 'application/json', 'origin': 'https://libretranslate.com', 'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36 OPR/82.0.4227.50'})).decode())['translatedText']
"""

async def aexec(code, globals=None, locals=None, /):
	if globals is None:
		globals = {}
	if locals is None:
		locals = {}

	variables = {}
	variables.update(globals)
	variables.update(locals)
	env_locals = {}
	exec("async def __ex(" + ', '.join(variables.keys()) + "):\n " + '\n '.join(x for x in code.split('\n')), None, env_locals)
	await env_locals['__ex'](**variables)

def translate(string, to_lang, from_lang="fra"):
	data = json.dumps({"format":"text","from":from_lang,"to":to_lang,"input":string,"options":{"sentenceSplitter":False,"origin":"translation.web","contextResults":False,"languageDetection":True}}).encode('utf8')
	return json.loads(request.urlopen(request.Request("https://api.reverso.net/translate/v1/translation", method="POST", data=data, headers={"content-type": "application/json", "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36 OPR/82.0.4227.50"})).read())["translation"][0]


async_translate = async_function(translate)

class AsyncExecReturn(Thread):
	def __init__(self, target, args=(), kwargs=None):
		if kwargs is None:
			kwargs = {}
		self.return_value = None
		self.error = None
		self.target = target
		self.args = args
		self.kwargs = kwargs
		super().__init__()

	def run(self):
		try:
			self.return_value = self.target(*self.args, **self.kwargs)
		except Exception as e:
			self.error = e

	async def start_wait(self):
		self.start()
		while self.is_alive():
			await asyncio.sleep(0.1)
		if self.error:
			raise self.error
		return self.return_value

	async def __call__(self):
		return await self.start_wait()


class ConfigDict(dict):
	def __init__(self, configfile):
		self.configfile = configfile
		self.reload()

	def reload(self):
		if os.path.exists(self.configfile):
			super().__init__(json.load(open(self.configfile, 'r', encoding='utf8')))
		else:
			super().__init__({})
			self.save()

	def save(self, **kwargs):
		kwargs.setdefault("indent", 1)
		with open(self.configfile, 'w') as f:
			json.dump(self, f, **kwargs)