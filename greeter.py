# coding=utf8
"""
greeter.py - Willie Greeting Module
Copyright 2014, Julen Landa Alustiza

"""

import willie
import re

def configure(config):
	"""
	| [greeter] | example | purpose |
	| -------- | ------- | ------- |
	| users | user1, user2 | users who can manage greeter module |
	"""
	if config.option('Configure user greeter module', False):
		config.add_section('greeter')
		config.interactive_add('greeter', 'users', 'comma separated user list', '')

def setup(bot):
	bot.memory['greeter_manager'] = GreetManager(bot)

	if not bot.db:
		raise ConfigurationError("Database not set up, or unavailable")
	conn = bot.db.connect()
	c = conn.cursor()

	# if table doesn't exists, create it
	create_table(bot, c)
	conn.commit()
	conn.close()

def create_table(bot, c):
	if bot.db.type == 'mysql':
		primary_key = '(nickname(254), channel(254))'
	else:
		primary_key = '(nickname, channel)'

	c.execute('''CREATE TABLE IF NOT EXISTS greeter (
		nickname TEXT,
		channel TEXT,
		greeting TEXT,
		id INT,
		PRIMARY KEY {0}
		)'''.format(primary_key)) 

@willie.module.commands('greeter')
def manage_greeter(bot, trigger):
	"""Manage greeter system. For a list of commands, type: .greeter help"""
	bot.memory['greeter_manager'].manage_greeter(bot, trigger)

class GreetManager:
	def __init__(self, bot):
		self.running = True
		self.sub = bot.db.substitution
		self.actions = sorted(method[7:] for method in dir(self) if method[:7] == '_greet_')

	def _show_doc(self, bot, command):
		"""Given an RSS command, say the docstring for the corresponding method."""
		for line in getattr(self, '_greet_' + command).__doc__.split('\n'):
			line = line.strip()
			if line:
				bot.reply(line)

	def manage_greeter(self, bot, trigger):
		if not (trigger.admin or trigger.nick.lower() in bot.config.greeter.get_list('users')): 
			bot.reply("Sorry, no admin no party")
			return

		text = trigger.group().split()
		if (len(text) < 2 or text[1] not in self.actions):
			bot.reply("Usage: .greeter <command>")
			bot.reply("Available greeter commands: " + ', '.join(self.actions))
			return

		conn = bot.db.connect()
		# run the function and commit database changes if it returns true
		if getattr(self, '_greet_' + text[1])(bot, trigger, conn.cursor()):
			conn.commit()
		conn.close()

	def _greet_add(self, bot, trigger, c):
		""" Add a greeting message for a nickname on a channel.
		Usage: .greeter add <nickname> <#channel> "<greeting message>"
		"""
		pattern = r'''
			^\.greeter\s+add
			\s+("[^"]+"|[\w-]+)	# nickname
			\s+([~&#+!][^\s,]+)	# channel
			\s+("[^"]+"|[\w-]+)	# greeting message
			'''
		match = re.match(pattern, trigger.group(), re.IGNORECASE | re.VERBOSE)
		if match is None:
			self._show_doc(bot, 'add')
			return

		nickname = match.group(1).lower()
		channel = match.group(2).lower()
		greeting = match.group(3).strip('"')

		c.execute('''
			SELECT * FROM greeter WHERE nickname = {0} AND channel = {0}
			'''.format(self.sub), (nickname, channel))
		if not c.fetchone():
			c.execute('''
				INSERT INTO greeter (nickname,channel,greeting)
				VALUES ({0}, {0}, {0})
				'''.format(self.sub), (nickname, channel, greeting))
			bot.reply('Greeting message added for ' + nickname + ' on ' + channel + ': ' + greeting + '.')
		else:
			c.execute('''
				UPDATE greeter SET greeting = {0}
				WHERE nickname = {0} AND channel = {0}
				'''.format(self.sub), (greeting, nickname, channel))
			bot.reply('Greeting message updated for ' + nickname + ' on ' + channel + ': ' + greeting + '.')
	
		return True

	def _greet_del(self, bot, trigger, c):
		""" Delete existing greeting messages for a nickname on a channel (optional)
		Usage: .greeter del <nickname> <#channel>
		"""
		pattern = r'''
			^\.greeter\s+delete
			\s+("[^"]+"|[\w-]+)	# nickname
			\s+([~&#+!][^\s,]+)	# channel
			'''

		match = re.match(pattern, trigger.group(), re.IGNORECASE | re.VERBOSE)
		if match is None:
			self._show_doc(bot, 'del')
			return

		nickname = match.group(1).lower()
		channel = match.group(2).lower()

		c.execute('''
			SELECT * FROM greeter WHERE nickname = :nickname AND channel = :channel
			'''.format(self.sub), {"nickname": nickname, "channel": channel})
		if c.fetchone():
			c.execute('''
				DELETE FROM greeter WHERE nickname = :nickname AND channel = :channel
				'''.format(self.sub), {"nickname": nickname, "channel": channel})
			result = 'Greeting message for {nick} on {chan} deleted'.format(nick=nickname, chan=channel)
		else:
			result = 'There is no greeting message for {nick} on {chan}'.format(nick=nickname, chan=channel)
		bot.reply(result)
		return True;

	def _greet_show(self, bot, trigger, c):
		""" Show greeting message for nickname on the channel.
		Usage: .greeter show <nickname> <#channel>
		"""
		pattern = r'''
			^\.greeter\s+show
			\s+("[^"]+"|[\w-]+)     # nickname
			\s+([~&#+!][^\s,]+)     # channel
			'''
		match = re.match(pattern, trigger.group(), re.IGNORECASE | re.VERBOSE)
		if match is None:
			self._show_doc(bot, 'show')
			return

		nickname = match.group(1).lower()
		channel = match.group(2).lower()

		c.execute('''
			SELECT * FROM greeter WHERE nickname = {0} AND channel = {0}
			'''.format(self.sub), (nickname, channel))
		greeting = c.fetchone()
		if greeting:
			bot.reply('The greeting message for ' + nickname + ' on ' + channel + ' is: ' + greeting[2] + '.')
		else:
			bot.reply('There is no greeting message for ' + nickname + ' on ' + channel + ' channel.')

		return True

	def _greet_list(self, bot, trigger, c):
		""" List users with greeting message on channel.
		Usage: .greetet list <#channel>
		"""
		pattern = r'''
			^\.greeter\s+list
			\s+([~&#+!][^\s,]+)	# channel
			'''
		match = re.match(pattern, trigger.group(), re.IGNORECASE | re.VERBOSE)
		if match is None:
			self._show_doc(bot, 'list')
			return

		channel = match.group(1).lower()

		c.execute('''SELECT * FROM greeter WHERE channel = :channel
		'''.format(self.sub), {"channel": channel})
		nicks = [row[0] for row in c.fetchall()]

		if not nicks:
			bot.reply("No greetings on " + channel + " yet.")
			return

		bot.reply("Users with greeting message on " + channel + ": " + ', '.join(nicks))

	def _greet_help(self, bot, trigger, c):
		"""Get help on any of the greeter commands.
		Usage: .rss help <command>
		"""
		command = trigger.group(4)
		if command in self.actions:
			self._show_doc(bot, command)
		else:
			bot.reply("For help on a command, type: .greet help <command>")
			bot.reply("Available greeter commands: " + ', '.join(self.actions))

	def greet(self, bot, trigger):
		conn = bot.db.connect()
		cursor = conn.cursor()
		nickname = trigger.nick.lower()
		channel = trigger.sender.lower()
		cursor.execute('''SELECT * FROM greeter WHERE nickname = :nickname AND channel = :channel
			'''.format(self.sub), {"channel": channel, "nickname": nickname})
		greeting = cursor.fetchone()
		if greeting:
			text = greeting[2].replace("<nickname>",trigger.nick)
			bot.say(text)
		else:
			nickname = 'default'
			cursor.execute('''SELECT * FROM greeter WHERE nickname = :nickname AND channel = :channel
                        '''.format(self.sub), {"channel": channel, "nickname": nickname})
			greeting = cursor.fetchone()
			if greeting:
				text = greeting[2].replace("<nickname>",trigger.nick)
				bot.say(text)
		conn.commit()
		conn.close()

@willie.module.event('JOIN')
@willie.module.rule('(.*)')
def greet(bot, trigger):
	bot.memory['greeter_manager'].greet(bot, trigger)
