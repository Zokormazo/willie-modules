# coding=utf8

import random
import willie
import re
from cobe.brain import Brain

def setup(bot):
	bot.memory['talking'] = Talking(bot);

class Talking:
	def __init__(self, bot):
		self.talking = True
		self.learning = True
		self.random = True
		self.randomTalk = 0
		self.brainLearning = '/home/julen/.willie/cobe/irc.brain'
		self.ignored = ['ataulfo', 'trivialneitor', 'nickserv', 'chanserv', 'noplanc']
		self.brains = { "irc": "/home/julen/.willie/cobe/irc.brain",
			"monkey": '/home/julen/.willie/cobe/monkeyisland.brain',
			"biblia": '/home/julen/.willie/cobe/biblia.brain',
			"japanese": '/home/julen/.willie/cobe/japanese.brain',
			"lobato": '/home/julen/.willie/cobe/lobato.brain'
		}
		self.brainTalking = 'irc'
		
	def isTalking(self):
		return self.talking

	def setTalking(self, value):
		self.talking = value

	def isLearning(self):
		return self.learning

	def setLearning(self, value):
		self.learning = value

	def isRandom(self):
		return self.random

	def setRandom(self, value):
		self.random = value

	def setRandomTalk(self, value):
		self.randomTalk = value

	def learn(self, bot, trigger):
		if trigger.nick == bot.nick or trigger.nick.lower() in self.ignored or trigger[0] == '.' :
			return
		text = trigger.replace(bot.nick + ":","").encode('utf-8')
		Brain(self.brainLearning).learn(trigger.encode('utf-8'))

	def talk(self,bot,trigger):
		if trigger.nick == bot.nick or trigger.nick.lower() in self.ignored or trigger[0] == '.' :
			return
		if self.randomTalk > 0 or bot.nick.lower() in trigger.lower() :
			text = re.sub(r"^" + bot.nick + "[,:] *", '', trigger).encode('utf-8')
			bot.say(Brain(self.brains[self.brainTalking]).reply(text).replace(bot.nick,trigger.nick))
			self.randomTalk = self.randomTalk -1

	def setBrain(self, brain):
		self.brainTalking = brain

	def setRandomBrain(self):
		self.brainTalking = random.choice(self.brains.keys())
		

@willie.module.commands('brain')
def manage_brain(bot, trigger):
	if not trigger.admin:
		bot.reply("no admin no party")
		return
	text = trigger.group().split()
	if len(text) < 3:
		bot.reply("unknown command")
		return
	
	if text[1] == 'status':
		if text[2] == 'talking':
			if bot.memory['talking'].isTalking():
				bot.reply("I'm talking")
			else:
				bot.reply("I'm not talking")
		elif text[2] == 'learning':
			if bot.memory['talking'].isLearning():
				bot.reply("I'm learning")
			else:
				bot.reply("I'm not learning")
		return
	if text[1] == 'start':
		if text[2] == 'talking':
			bot.memory['talking'].setTalking(True)
			bot.reply("Talking enabled")
		elif text[2] == 'learning':
			bot.memory['talking'].setLearning(True)
			bot.reply("Learning enabled")
		return
	if text[1] == 'stop':
		if text[2] == 'talking':
			bot.memory['talking'].setTalking(False)
			bot.reply("Talking disabled")
		elif text[2] == 'learning':
			bot.memory['talking'].setLearning(False)
			bot.reply("Learning disabled")
		return

	if text[1] == 'set':
		bot.memory['talking'].setBrain(text[2])
		bot.reply("Brain changed to " + text[2])
		return

@willie.module.event('PRIVMSG')
@willie.module.rule('(.*)')
def learn(bot, trigger):
	talking = bot.memory['talking']
	if talking.isTalking():
		talking.talk(bot,trigger)
	if talking.isLearning():
		talking.learn(bot, trigger)

@willie.module.interval(60*60*2)
def randomize(bot, force=False):
	if bot.memory['talking'].isRandom() :
		bot.memory['talking'].setRandomTalk(random.randint(1,5))
		bot.memory['talking'].setRandomBrain()
		
