# coding=utf8
"""
brain.py - Willie talking bot module
Copyright 2014, Julen Landa Alustiza

Licensed under the Eiffel Forum License 2.
"""

import willie
import re
import os

from cobe.brain import Brain

def configure(config):
	"""
	| [brain] | example | purpose |
	| -------- | ------- | ------- |
	| path | ~/.willie/cobe/ | cobe brain directory path |
	| learn | irc | cobe brain for learning |
	| ignored_nicks | nick1, nick2 | nicks to ignore |
	"""
	if config.option('Configure brain module', False):
		config.add_section('brain')
		config.interactive_add('brain', 'path', 'directory path', '~/.willie/bot/')
		config.interactive_add('brain', 'learn', 'cobe brain name' 'irc')
		config.interactive_add('brain', 'ignored_nicks', 'nicks to ignore', '')

def setup(bot):
	bot.memory['talking'] = Talking(bot);

class Talking:
	def __init__(self, bot):
		self.talking = True
		self.learning = True
		self.brainTalking = bot.config.brain.learn
		self.actions = sorted(method[7:] for method in dir(self) if method[:7] == '_brain_')
		self.brains = []
		for file in os.listdir(bot.config.brain.path):
			if file.endswith(".brain"):
				self.brains.append(os.path.splitext(os.path.basename(file))[0])
		

	def _show_doc(self, bot, command):
		"""Given an brain command, say the docstring for the corresponding method."""
		for line in getattr(self, '_brain_' + command).__doc__.split('\n'):
			line = line.strip()
			if line:
				bot.reply(line)

	def manage_brain(self, bot, trigger):
		text = trigger.group().split()
		if (len(text) < 2 or text[1] not in self.actions):
			bot.reply("Usage: .brain <command>")
			bot.reply("Available brain commands: " + ', '.join(self.actions))
			return

		getattr(self, '_brain_' + text[1])(bot, trigger)

	def _brain_status(self, bot, trigger):
		""" Show brain module status.
		Usage: .brain status
		"""
		pattern = r'''
			^\.brain\s+status
			'''

		match = re.match(pattern, trigger.group(), re.IGNORECASE | re.VERBOSE)
		if match is None:
			self._show_doc(bot, 'status')
			return

		bot.reply('brain module status')
		bot.reply('Talking: ' + str(self.talking) + '. Talking brain: ' + self.brainTalking)
		bot.reply('Learning: ' + str(self.learning) + '. Learning brain: ' + bot.config.brain.learn)

	def _brain_start(self, bot, trigger):
		""" Start talking/learning.
		Usage .brain start talking|learning
		"""
		if not trigger.admin:
			bot.reply("no admin no party")
			return

		pattern = r'''
			^\.brain\s+start
			\s+(talking|learning)	# talking/learning
			'''
		match = re.match(pattern, trigger.group(), re.IGNORECASE | re.VERBOSE)
		if match is None:
			self._show_doc(bot, 'start')
			return

		action = match.group(1).lower()
		setattr(self,action,True)
		bot.reply("I'm " + action)

	def _brain_stop(self, bot, trigger):
		""" Stop talking/learning
		Usage .brain stop talking|learning
		"""
		if not trigger.admin:
			bot.reply("no admin no party")
			return

		pattern = r'''
			^\.brain\s+stop
			\s+(talking|learning)   # talking/learning
			'''
		match = re.match(pattern, trigger.group(), re.IGNORECASE | re.VERBOSE)
		if match is None:
			self._show_doc(bot, 'start')
			return

		action = match.group(1).lower()
		setattr(self,action,False)
		bot.reply("I'm not " + action)

	def _brain_list(self, bot, trigger):
		""" List available brains
		Usage .brain list
		"""
		pattern = r'''
			^\.brain\s+list
			'''
		match = re.match(pattern, trigger.group(), re.IGNORECASE | re.VERBOSE)
		if match is None:
			self._show_doc(bot, 'list')
			return
		bot.reply("Available brains: " + ', '.join(self.brains))

	def _brain_set(self, bot, trigger):
		""" Set talking brain
		Usage .brain set <brain>
		"""
		if not trigger.admin:
			bot.reply("no admin no party")
			return
		pattern = r'''
			^\.brain\s+set
			\s+("[^"]+"|[\w-]+)	# brain
			'''
		match = re.match(pattern, trigger.group(), re.IGNORECASE | re.VERBOSE)
		if match is None:
			self._show_doc(bot, 'set')
			return
		brain = match.group(1)
		if not brain in self.brains:
			bot.reply("Brain not found. Available brains: " + ', '.join(self.brains))
			return
		self.brainTalking = brain
		bot.reply("Brain changed to " + brain)

	def _brain_help(self, bot, trigger):
		"""Get help on any of the brain commands.
		Usage: .brain help <command>
		"""
		command = trigger.group(4)
		if command in self.actions:
			self._show_doc(bot, command)
		else:
			bot.reply("For help on a command, type: .brain help <command>")
			bot.reply("Available brain commands: " + ', '.join(self.actions))


	def _learn(self, bot, trigger):
		if trigger.nick == bot.nick or trigger.nick.lower() in bot.config.brain.get_list('ignored_users') or trigger[0] == '.' :
			return
		text = trigger.replace(bot.nick + ":","").encode('utf-8')
		Brain(bot.config.brain.path + bot.config.brain.learn + '.brain').learn(trigger.encode('utf-8'))

	def _talk(self, bot, trigger):
		if trigger.nick == bot.nick or trigger.nick.lower() in bot.config.brain.get_list('ignored_users') or trigger[0] == '.' :
			return
		if bot.nick.lower() in trigger.lower() :
			text = re.sub(r"^" + bot.nick + "[,:] *", '', trigger).encode('utf-8')
			bot.say(Brain(bot.config.brain.path + self.brainTalking + '.brain').reply(text).replace(bot.nick,trigger.nick))

	def trigger(self, bot, trigger):
		if self.talking :
			self._talk(bot, trigger)
		if self.learning :
			self._learn(bot, trigger)

@willie.module.commands('brain')
def manage_brain(bot, trigger):
	"""Manage brain system. For a list of commands, type: .brain help"""
	bot.memory['talking'].manage_brain(bot, trigger)


@willie.module.event('PRIVMSG')
@willie.module.rule('(.*)')
def manage_trigger(bot, trigger):
	bot.memory['talking'].trigger(bot, trigger)		
