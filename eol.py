# coding=utf8
"""
eol.py - Willie elotrolado.net tools module
Copyright 2014, Julen Landa Alustiza

Licensed under the Eiffel Forum License 2.
"""

import willie
import requests
import re
import os
from bs4 import BeautifulSoup
from collections import OrderedDict
from time import sleep

BASE_URL = 'http://www.elotrolado.net/'
SAY_PREFIX = '[EOL] '

__version__ = '0.1-git'
regexes = {
	'thread' : re.compile('(?:http://www\.elotrolado\.net/hilo_[\a-z0-9\-]*_)(\d+)(?:_s\d+)?(?:\#p(\d+))?'),
	'new' : re.compile('(?:http://www\.elotrolado\.net/noticia_[\a-z0-9\-]*_)(\d+)'),
	'viewtopic' : re.compile('(?:http://www\.elotrolado\.net/viewtopic\.php\?p=)(\d+)'),
	'viewprofile' : re.compile('(?:http://www\.elotrolado\.net/memberlist.php\?mode=viewprofile\&u=)(\d+)')
}

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
	if not bot.memory.contains('url_callbacks'):
		bot.memory['url_callbacks'] = tools.WillieMemory()
	bot.memory['url_callbacks'][regexes['thread']] = show_about_thread
	bot.memory['url_callbacks'][regexes['new']] = show_about_new
	bot.memory['url_callbacks'][regexes['viewtopic']] = show_about_viewtopic
	bot.memory['url_callbacks'][regexes['viewprofile']] = show_about_viewprofile

@willie.module.commands('who')
@willie.module.example('.who melado') 
def who(bot, trigger):
	"""Show profile info"""
	if not trigger.group(2):
		return
	bot.memory['eol_manager']._show_profile(bot,trigger.group(2))

@willie.module.rule('.*(?:http://www\.elotrolado\.net/hilo_[a-z0-9\-]*_)(\d+)(?:_s\d+)?(?:\#p(\d+))?')
def show_about_thread(bot, trigger, found_match=None):
	"""
	Get information about thread and/or post from hilo_ link
	"""
	match = found_match or trigger
	if match:
		bot.memory['eol_manager']._show_thread(bot,match.group(1))
		if match.group(2):
			bot.memory['eol_manager']._show_post(bot,match.group(2))

@willie.module.rule('.*(?:http://www\.elotrolado\.net/noticia_[a-z0-9\-]*_)(\d+)')
def show_about_new(bot, trigger, found_match=None):
	"""
	Get information about new from noticia_ link
	"""
	match = found_match or trigger
	if match:
		bot.memory['eol_manager']._show_new(bot, match.group(1))

@willie.module.rule('.*(?:http://www\.elotrolado\.net/viewtopic\.php\?p=)(\d+)')
def show_about_viewtopic(bot, trigger, found_match=None):
	"""
	Get information about thread and post from viewtopic.php link
	"""
	match = found_match or trigger
	if match:
		bot.memory['eol_manager']._show_thread_from_post(bot, match.group(1))
		bot.memory['eol_manager']._show_post(bot, match.group(1))

@willie.module.rule('.*(?:http://www\.elotrolado\.net/memberlist.php\?mode=viewprofile&u=)(\d+)')
def show_about_viewprofile(bot, trigger, found_match=None):
	"""
	Get information about profile from memberlist.php link
	"""
	match = found_match or trigger
	if match:
		bot.memory['eol_manager']._show_profile(bot, match.group(1))

class UserProfile:
	def __init__(self, soup):
		self.profile = dict()
		self.wiki = dict()
		tag = soup.find('form', {'id': 'viewprofile'}).find('dd') # user's title
		if tag.string is not None:
			self.profile['title'] = tag.string
		tag = tag.find_next('span')	# username
		self.profile['username'] = tag.string
		tag = soup.find('div', {'class': 'column2'}).find('dd')	#registered
		self.profile['registered'] = tag.string
		tag = tag.find_next('dd')	# last seen
		string = tag.string.strip()
		if string != '' or string != '-':
			self.profile['last_seen'] = string
		tag = tag.find_next('dd').a		# messages
		self.profile['messages'] = tag.string
		tag = tag.find_next('div', {'class': 'column2'}).find('dd')
		if tag is not None:	# there is wiki info
			self.wiki['most_edited'] = tag.text	# most edited articles
			tag = tag.find_next('dd').a		# last edited
			self.wiki['last_edited'] = tag.text
			tag = tag.find_next('dd')		# wiki stats
			self.wiki['stats'] = tag.text

	def __unicode__(self):
		string = self.profile['username']
		if 'title' in self.profile:
			string = string + " :: " + self.profile['title']
		string = string + " | Registrado: " + self.profile['registered']
		if 'last_seen' in self.profile:
			string = string + " | Ultima vez: " + self.profile['last_seen']
		string = string + " | " + self.profile['messages']
		if 'stats' in self.wiki:
			string = string + '\n' + self.wiki['stats'] + ' | Mas editado: ' + self.wiki['most_edited'] + ' | Ultimo editado: ' + self.wiki['last_edited']
		return string

class Thread:
	def __init__(self, soup):
		self.thread = dict()
		self.thread['title'] = soup.find('h1').find('a').string.strip()
		forums = []
		for a in soup.find('h3').find_all('a'):
			forums.append(a.string)
		self.thread['forums'] = forums
		self.thread['author'] = soup.find('div', {'class': 'postuser'}).find('a').string.strip()
		match = re.match(r'.*\s(\d+\smensajes?)', soup.find('div', {'class': 'pagination'}).text)
		if match:
			self.thread['messages'] = match.group(1)

	def __unicode__(self):
		return 'Hilo: ' + self.thread['title'] + ' | Foro: ' + ', '.join(self.thread['forums']) + ' | Autor: ' + self.thread['author']

class Post:
	def __init__(self, soup):
		self.post = dict()
		self.post['author'] = soup.find('div', {'class': 'postuser'}).find('a').string.strip()
		self.post['date'] = soup.find('div', {'class': 'postuser'}).find('p').text.strip()
		body = soup.find('div', {'class' : 'postbody'})
		for tag in body.findAll('div'):
			tag.unwrap()
		for tag in body.findAll('blockquote'):		
			tag.extract()
		for tag in body.findAll('dl', {'class': 'codebox'}):
			tag.extract()
		for tag in body.findAll('br'):
			tag.replace_with('\n')
		self.post['body'] = re.sub('\n+', '\n', unicode(body.text.strip())).split('\n')
				
		
	def __unicode__(self):
		string = 'Post | Autor: ' + self.post['author'] + ' | Posteado el: ' + self.post['date']
		for line in self.post['body'][0:2]:
			string = string + '\n\t' + line
		return string

class New:
	def __init__(self, soup):
		self.new = dict()
		self.new['title'] = soup.find('h3').find('a').string.strip()
		notimeta = soup.find('p', {'class': 'notimeta'})
		self.new['author'] = notimeta.find('strong').string.strip()
		self.new['category'] = notimeta.find('a').string.strip()
		self.new['comments'] = notimeta.find('a').find_next('a').string.strip()

	def __unicode__(self):
		return 'Noticia: ' + self.new['title'] + ' | Categoria: ' + self.new['category'] + ' | Autor: ' + self.new['author'] + ' | ' + self.new['comments']

class EolManager:
	def __init__(self, bot):
		self.actions = sorted(method[5:] for method in dir(self) if method[:5] == '_eol_')
		self.session = requests.Session()
		self.session.headers.update({'User-Agent': 'Braulio el bot de Zokormazo ' + __version__})
		self._login(bot)
		self.filename = os.path.join(bot.config.dotdir, 'eol.option')
		self.thread_title = bot.config.eol.thread_title
		self._read_config()

	def _read_config(self):
		if not os.path.exists(self.filename):
			self.thread = ''
			self.last_post = ''
		else:
			try:
				f = open(self.filename, 'r')
			except OSError:
				pass
			else:
				self.thread = f.readline().split('\n')[0]
				self.last_post = f.readline().split('\n')[0]
				f.close()

	def _write_config(self):
		try:
			f = open(self.filename, 'w')
		except OSError:
			pass
		else:
			f.write(self.thread + '\n' + self.last_post)
			f.close()


	def _show_doc(self, bot, command):
		"""Given an eol command, say the docstring for the corresponding method."""
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

	def _show_thread(self, bot, thread):
		response = self.session.get(BASE_URL + 'hilo__' + str(thread))
		if response.status_code == 404:
			bot.say(SAY_PREFIX + 'Hilo no encontrado')
			return
		if response.status_code == 403:
			bot.say(SAY_PREFIX + 'No tengo permiso para ver ese hilo')
			return
		soup = BeautifulSoup(response.text)
		thread = Thread(soup)
		for line in unicode(thread).split('\n'):
			bot.say(SAY_PREFIX + line)

	def _show_thread_from_post(self, bot, post):
		params = {'p' : post }
		response = self.session.head(BASE_URL + 'viewtopic.php', params=params, allow_redirects = False)
		if response.status_code == 301:
			self._show_thread(bot, response.headers['location'].split("=")[2])

	def _show_post(self, bot, post):
		params = { 'p': str(post) }
		response = self.session.get(BASE_URL + 'viewtopic.php', params=params)
		if response.status_code == 404:
			bot.say(SAY_PREFIX + "Post no encontrado")
			return
		if response.status_code == 403:
			bot.say(SAY_PREFIX + 'No tengo permiso para ver ese post')
			return
		soup = BeautifulSoup(response.text)
		post = Post(soup.find('div', {'id': 'p' + post}))
		for line in unicode(post).split('\n'):
			bot.say(SAY_PREFIX + line)

	def _show_profile(self, bot, profile):
		params = {
			'mode' : 'viewprofile' ,
		}
		if profile.isdigit():
			params['u'] = profile
		else:
			params['un'] = profile
		response = self.session.get(BASE_URL + 'memberlist.php', params = params)
		if response.status_code == 404:
			bot.say('Usuario no encontrado')
			return
		if response.status_code == 403:
			bot.say('No tengo permiso para ver este usuario')
			return
		if response.status_code == requests.codes.ok:
			soup = BeautifulSoup(response.text)
			profile = UserProfile(soup)
			for line in unicode(profile).split('\n'):
				bot.say(SAY_PREFIX + line)
	def _show_new(self, bot, new):
		response = self.session.get(BASE_URL + 'noticia__' + str(new))
		if response.status_code == 404:
			bot.say('Noticia no encontrada')
			return
		if response.status_code == 403:
			bot.say('No tengo permiso para ver esa noticia')
			return
		soup = BeautifulSoup(response.text)
		new = New(soup)
		for line in unicode(new).split('\n'):
			bot.say(SAY_PREFIX + line)

	def _login(self, bot):
		response = self.session.head(BASE_URL + 'foro_playstation-4_204')
		sid = response.cookies['phpbb3_eol_sid']
		params = { 'mode' : 'forcemobile', 'sid' : sid }
		response = self.session.head(BASE_URL + 'rpc.php', params=params)
		params = { 'mode' : 'login' }
		formdata = { 'username' : bot.config.eol.username, 'password' : bot.config.eol.password, 'sid' : sid, 'autologin' : 'on', 'redirect': 'ucp.php', 'login': 'Identificarse' }
		response = self.session.post(BASE_URL + 'ucp.php', params=params, data=formdata)

	def _new_thread(self, message):
		params = { 'mode' : 'post', 'f' : '21' }
		response = self.session.get(BASE_URL + 'posting.php', params=params)
		if response.status_code != requests.codes.ok:
			return False
		soup = BeautifulSoup(response.text)
		formdata = {
			'subject' : 'El hilo de Don Braulio',
			'message' : message,
			'post' : 'Enviar',
			'attach_sig' : 'on',
		}
		for input in soup.find('form', {'id' : 'postform'}).find_all('input', { 'type' : 'hidden' }):
			formdata[input['name']] = input['value']
		sleep(2)
		response = self.session.post(BASE_URL + 'posting.php', params=params, data=formdata)
		if response.status_code != requests.codes.ok:
			return False
		soup = BeautifulSoup(response.text)
		link = soup.find('div', {'class' : 'inner'}).find_next('a')['href']
		self.thread = link.split('t=')[1]
		response = self.session.get(BASE_URL + link)
		if response.status_code != requests.codes.ok:
			return False
		soup = BeautifulSoup(response.text)
		self.last_post = soup.find('div', {'class' : 'post bg2'})['id'][1:]
		self._write_config()
		return True

	def _new_reply(self, thread, message):
		params = {'mode' : 'reply', 'f' : '21', 't' : thread}
		response = self.session.get(BASE_URL + 'posting.php', params=params)
		if response.status_code != requests.codes.ok:
			return False
		if 'Lo sentimos' in response.text:
			# double posting, edit instead of reply
			self._edit_post(self.last_post, message)
			return False
		soup = BeautifulSoup(response.text)
		formdata = {
			'message' : message,
			'post' : 'Enviar',
			'attach_sig' : 'on',
		}
		for input in soup.find('form', {'id' : 'postform'}).find_all('input', {'type': 'hidden'}):
			formdata[input['name']] = input['value']
		sleep(2)
		response = self.session.post(BASE_URL + 'posting.php', params=params, data=formdata)
		if response.status_code != requests.codes.ok:
			return False
		soup = BeautifulSoup(response.text)
		self.last_post = soup.find('div', {'class' : 'inner'}).find_next('a')['href'].split('#p')[1]
		self._write_config()
		return True

	def _edit_post(self, post, message):
		params = {'mode' : 'edit', 'f' : '21', 'p' : post}
		response = self.session.get(BASE_URL + 'posting.php', params=params)
		if response.status_code != requests.codes.ok:
			return False
		soup = BeautifulSoup(response.text)
		formdata = {
			'message' : soup.find('textarea', {'name' : 'message'}).string + '\n\nEDIT:\n\n' + message,
			'post' : 'Enviar',
			'attach_sig' : 'on',
		}
		for input in soup.find('form', {'id' : 'postform'}).find_all('input', {'type' : 'hidden'}):
			formdata[input['name']] = input['value']
		subject = soup.find('input', {'id': 'subject'})
		if subject is not None:
			formdata['subject'] = subject['value']
		sleep(2)
		response = self.session.post(BASE_URL + 'posting.php', params=params, data=formdata)
		return True

	def post(self, message):
		if message == '':
			return
		if self.thread is None or self.thread == '':
			self._new_thread(message)
		else:
			if self.session.head(BASE_URL + 'hilo__' + self.thread).status_code == requests.codes.ok:
				self._new_reply(self.thread, message)
			else:
				self._new_thread(message)

