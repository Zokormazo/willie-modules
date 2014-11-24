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
	"""
	if config.option('Configure user eol module', False):
		config.add_section('eol')
		config.interactive_add('eol', 'username', 'username', '')
		config.interactive_add('eol', 'password', 'password', '')

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
		left = soup.find('form', {'id': 'viewprofile'})
		title = left.find('dd')
		user = title.find_next('span')
		detail = soup.find('div', {'class': 'column2'})
		registered = detail.find('dd')
		last_seen = registered.find_next('dd')
		messages = last_seen.find_next('dd').a.string
		bot.say(SAY_PREFIX + "Usuario: " + user.string + " - " + title.string + " | Registrado: " + registered.string + " | Ultima vez: " + last_seen.string + " | " + messages)
		wiki = detail.find_next('div', {'class': 'column2'})
		most_edited = wiki.find('dd')
		if most_edited is None:
			return
		last_edited = most_edited.find_next('dd')
		stats = last_edited.find_next('dd')
		bot.say(SAY_PREFIX + stats.text + " |  Mas editado: " + most_edited.text + " | Ultimo editado: " + last_edited.a.text)

	def _login(self, bot):
		response = self.session.get(BASE_URL + 'ucp.php')
		sid = response.cookies['phpbb3_eol_sid']
		params = { 'mode' : 'login' }
		formdata = { 'username' : bot.config.eol.username, 'password' : bot.config.eol.password, 'sid' : sid, 'autologin' : 'on', 'redirect': 'ucp.php', 'login': 'Identificarse' }
		response = self.session.post(BASE_URL + 'ucp.php', params=params, data=formdata)
		

	def show_about(self, bot, trigger):
		bot.say('EOL show about...')
