# coding=utf8

import willie
import re

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
		self.users = ['ealdor', 'petisoeol']

		self.actions = sorted(method[5:] for method in dir(self) if method[5:] == '_greet_')

	def manage_greeter(self, bot, trigger):
		if not (trigger.admin or trigger.nick.lower() in self.users): 
			bot.reply("Sorry, no admin no party")
			return

		text = trigger.group().split()
		conn = bot.db.connect()
		if text[1] == "add":
			self._greet_add(bot, trigger, conn.cursor())
		if text[1] == "show":
			self._greet_show(bot, trigger, conn.cursor())
		if text[1] == "delete":
			self._greet_del(bot, trigger, conn.cursor())
	        # run the function and commit database changes if it returns true
		#if getattr(self, '_rss_' + text[1])(bot, trigger, conn.cursor()):
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
		""" Delete existint greeting messages for a nickname on a channel (optional)
		Usage: .greeter del <nickname> <#channel>
		"""
		pattern = r'''
			^\.greeter\s+delete
			\s+("[^"]+"|[\w-]+)	# nickname
			\s+([~&#+!][^\s,]+)	# channel
			'''

		match = re.match(pattern, trigger.group(), re.IGNORECASE | re.VERBOSE)
		if match is None:
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
