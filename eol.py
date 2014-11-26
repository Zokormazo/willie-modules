# coding=utf8
"""
eol.py - Willie elotrolado.net tools module
Copyright 2014, Julen Landa Alustiza

Licensed under the Eiffel Forum License 2.
"""

import willie
import requests
import re
from bs4 import BeautifulSoup

BASE_URL = 'http://www.elotrolado.net/'
SAY_PREFIX = '[EOL] '

def configure(config):
	"""
	| [eol] | example | purpose |
	| -------- | ------- | ------- |
	| username | foo | username |
	| password | 12345 | password |
	| lines_to_show	| 5 | post/news lines to show |
	"""
	if config.option('Configure user eol module', False):
		config.add_section('eol')
		config.interactive_add('eol', 'username', 'username', '')
		config.interactive_add('eol', 'password', 'password', '')
		config.interactive_add('eol', 'lines_to_show', '5', '5')

def setup(bot):
	bot.memory['eol_manager'] = EolManager(bot)

@willie.module.commands('eol')
def manage_eol(bot, trigger):
	"""Manage ElOtroLado system. For a list of commands, type: .eol help"""
	bot.memory['eol_manager'].manage_eol(bot, trigger)

@willie.module.rule('.*(www.elotrolado.net)((/[\w-])*).*')
def show_about_auto(bot, trigger):
	bot.memory['eol_manager'].show_about(bot, trigger)

class EolManager:
	def __init__(self, bot):
		self.actions = sorted(method[5:] for method in dir(self) if method[:5] == '_eol_')
		self.session = requests.Session()
		self.session.headers.update({'User-Agent': 'Braulio el bot de Zokormazo 0.1-git'})
		self._login(bot)

	def _show_doc(self, bot, command):
		"""Given an RSS command, say the docstring for the corresponding method."""
		for line in getattr(self, '_eol_' + command).__doc__.split('\n'):
			line = line.strip()
			if line:
				bot.reply(line)

	def manage_eol(self, bot, trigger):
		text = trigger.group().split()
		if (len(text) < 2 or text[1] not in self.actions):
			bot.reply("Usage: .eol <command>")
			bot.reply("Available EOL commands: " + ', '.join(self.actions))
			return

		# run the function and commit database changes if it returns true
		getattr(self, '_eol_' + text[1])(bot, trigger)

	def _eol_help(self, bot, trigger):
		"""Get help on any of the EOL commands.
		Usage: .eol help <command>
		"""
		command = trigger.group(4)
		if command in self.actions:
			self._show_doc(bot, command)
		else:
			bot.reply("For help on a command, type: .eol help <command>")
			bot.reply("Available greeter commands: " + ', '.join(self.actions))

	def _eol_who(self, bot, trigger):
		""" Show user's EOL profile
		Usage: .eol who <user> | .eol who "Username with special characters"
		"""
		pattern = r'''
			^\.eol\s+who
			\s+("[^"]+"|[\w-]+)	#username
			'''
		match = re.match(pattern, trigger.group(), re.IGNORECASE | re.VERBOSE)
		if match is None:
			self._show_doc(bot, 'who')
			return

		username = match.group(1).replace('"','')
		params = { 'mode': 'viewprofile', 'mention': '1', 'un': username }
		response = self.session.get(BASE_URL + 'memberlist.php', params=params)
		if response.status_code == 404:
			bot.say('Usuario no encontrado')
			return
		if response.status_code == 403:
			self._login(bot)
			self._eol_who(bot, trigger)
			return
		soup = BeautifulSoup(response.text)
		tag = soup.find('form', {'id': 'viewprofile'}).find('dd') # user's title
		if tag.string is None:
			string = ""
		else:
			string = " :: " + tag.string
		tag = tag.find_next('span')	# username
		string = tag.string + string
		tag = soup.find('div', {'class': 'column2'}) # user details
		tag = tag.find('dd')	# registered
		string = string + " | Registered: " + tag.string
		tag = tag.find_next('dd') # last seen
		string = string + " | Ultima vez: " + tag.string
		tag = tag.find_next('dd').a
		string = string + " | Mensajes: " + tag.string
		tag = tag.find_next('div', {'class': 'column2'}) # wiki details
		tag = tag.find('dd')	# most_edited
		if tag is not None:	# there is wiki info
			string2 = "Mas editado: " + tag.text
			tag = tag.find_next('dd').a	#last edited
			string2 = string2 + " | Ultimo editado: " + tag.text
			tag = tag.find_next('dd')	#wiki stats
			string = string + "\n" + tag.text + " | " + string2
		for line in string.split('\n'):
			bot.say(SAY_PREFIX + line)

	def _eol_thread(self, bot, trigger):
		""" Show thread
		Usage: .eol thread <thread-number>
		"""
		pattern = r'''
			^\.eol\s+thread
			\s+([0-9]+)	#thread number
			'''
		match = re.match(pattern, trigger.group(), re.IGNORECASE | re.VERBOSE)
		if match is None:
			self._show_doc(bot, 'thread')
			return
		thread = match.group(1)
		self._show_thread(bot, thread)

	def _eol_post(self, bot, trigger):
		""" Show post
		Usage: .eol post <post-number>
		"""
		pattern = r'''
			^\.eol\s+post
			\s+([0-9]+)	#post number
			'''
		match = re.match(pattern, trigger.group(), re.IGNORECASE | re.VERBOSE)
		if match is None:
			self._show_doc(bot, 'post')
			return
		post = match.group(1)
		self._show_post(bot, post)

	def _show_thread(self, bot, thread):
		response = self.session.get(BASE_URL + "hilo__" + str(thread))
		if response.status_code == 404:
			bot.say(SAY_PREFIX + "Hilo no encontrado")
			return
		if response.status_code == 403:
			bot.say(SAY_PREFIX + "No tengo permiso para ver ese hilo")
			return
		soup = BeautifulSoup(response.text)
		string = SAY_PREFIX + "Hilo: " + soup.find('h1').find('a').string.strip()
		forums = []
		for a in soup.find('h3').find_all('a'):
			forums.append(a.string)
		string = string + " | Foro: " + ', '.join(forums)
		string = string + " | Autor: " + soup.find('div', {'class': 'postuser'}).find('a').string.strip()
		match = re.match(r'.*\s(\d+\smensajes?)', soup.find('div', {'class': 'pagination'}).text)
		if match:
			string = string + " | " + match.group(1)
		bot.say(string)

	def _show_post(self, bot, post):
		params = { 'p': str(post) }
		response = self.session.get(BASE_URL + "viewtopic.php", params=params)
		if response.status_code == 404:
			bot.say(SAY_PREFIX + "Post no encontrado")
			return
		if response.status_code == 403:
			bot.say(SAY_PREFIX + "No tengo permiso para ver ese post")
			return
		soup = BeautifulSoup(response.text)
		post = soup.find('div', {'id': 'p' + post})
		string = "Post | Autor: " + post.find('div', {'class': 'postuser'}).find('a').string
		string = string + " | Posteado el: " + post.find('div', {'class': 'postuser'}).find('p').text
		body = post.find('div', {'class': 'postbody'})
		for tag in body.findAll('div'):
			tag.unwrap()
		for tag in body.findAll('blockquote'):		
			tag.extract()
		for tag in body.findAll('dl', {'class': 'codebox'}):
			tag.extract()
		for tag in body.findAll('br'):
			tag.replace_with('\n')
		post_list = re.sub('\n+', '\n', unicode(body.text.strip())).split('\n')
		
		for line in string.split('\n'):
			bot.say(SAY_PREFIX + line)
		for line in post_list[0:int(bot.config.eol.lines_to_show)]:
			bot.say(SAY_PREFIX + "\t" + line)
		if len(post_list) > int(bot.config.eol.lines_to_show):
			bot.say(SAY_PREFIX + "\t(...)")

	def _login(self, bot):
		response = self.session.get(BASE_URL + 'foro_playstation-4_204')
		sid = response.cookies['phpbb3_eol_sid']
		params = { 'mode' : 'forcemobile', 'sid' : sid }
		response = self.session.get(BASE_URL + 'rpc.php', params=params)
		params = { 'mode' : 'login' }
		formdata = { 'username' : bot.config.eol.username, 'password' : bot.config.eol.password, 'sid' : sid, 'autologin' : 'on', 'redirect': 'ucp.php', 'login': 'Identificarse' }
		response = self.session.post(BASE_URL + 'ucp.php', params=params, data=formdata)
		

	def show_about(self, bot, trigger):
		pattern = r'''
			(.*\s)?
			(http://)?www\.elotrolado\.net/
			([a-z]+)
			_.*_
			(\d+)
			(?:_s\d+)?
			(?:\#p(\d+))?
			'''
		match = re.match(pattern, trigger.group(), re.IGNORECASE | re.VERBOSE)
		if match is None:
			pattern = r'''
				(.*\s)?
				(http://)?www\.elotrolado\.net/viewtopic\.php\?p=
				(\d+)
				'''
			match = re.match(pattern, trigger.group(), re.IGNORECASE | re.VERBOSE)
			if match is not None:
				self._show_post(bot, match.group(3))
		else:
			type = match.group(3)
			id = match.group(4)
			post = match.group(5) if match.group(5) else None
			if type == 'hilo':
				self._show_thread(bot, id)
				if post:
					self._show_post(bot, post)
