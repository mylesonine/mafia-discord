import settings
from roles import *
from log import log_msg
from game import Game_State, Game_Player
import util
import random
import mafia
import town
#import generic
#import discord
import asyncio
from time import time

eval_state = {}
def get_server():
	return eval_state['server']
	
def get_message():
	return eval_state['message']
	
def reply(msg):
	global eval_state
	if type(msg) != 'str':
		msg = str(msg)
	if eval_state['output'] != '':
		eval_state['output'] += '\n'
	eval_state['output'] +=  msg
		
class Server_State:	
	def __init__(self, bot_state = None, client = None, guild = None):
		self.inited = False
		self.bot_state = bot_state
		self.client = client
		self.guild = guild
		self.guild_id = 0
		
		if bot_state != None and client != None and guild != None:
			self.inited = True
			self.guild_id = guild.id
		
		self.games = []
		self.active_lobby = -1
		self.lobby_count = 0
		
		self.settings = {}
		self.settings['night_duration'] = 60
		self.settings['day_duration'] = settings.day_duration
		self.settings['required_roles'] = [ Role.mafioso, Role.doctor, Role.sheriff, Role.vigilante, Role.politician]
		self.settings['role_reveal_players'] = 11
		self.settings['max_players'] = settings.max_players
		self.settings['start_emoji'] = settings.start_emoji
		self.settings['banned_roles'] = []
		self.settings['game_count'] = 0
		self.settings['role_balance'] = []
		
		self.data = {}
		self.data['finished_games'] = 0
		
		
		self.score_record = {}
	
	def full_init(self, bot_state, client, guild):
		self.bot_state = bot_state
		self.client = client
		self.guild = guild
		self.guild_id = guild.id
		self.inited = True
	
	def update_scores(self, winners = [], losers = []):
		for i in winners + losers:
			if i not in self.score_record:
				self.score_record[i] = (0, 0)
		for i in winners:
			s = self.score_record[i]
			self.score_record[i] = (s[0] + 1, s[1])
		for i in losers:
			s = self.score_record[i]
			self.score_record[i] = (s[0], s[1] + 1)
	
	async def handle_msg(self, message):
		print(f'{message.author.name}: {message.content}')
		msg = message.content
		
		if message.author.id in [104162965162303488, 95306897103532032]:
			if msg.startswith('```') and msg.endswith('```') and len(msg) > 3:
				try:
					global eval_state
					eval_state['server'] = self
					eval_state['channel'] = message.channel
					eval_state['output'] = ''
					eval_state['message'] = message
					exec(msg[3:-3])
					if eval_state['output'] != '':
						await message.channel.send(eval_state['output'])
					else:
						await message.channel.send('OK')
					return
				except BaseException as e:
					await message.channel.send(f'Exception: {e}')
					return
		if msg.lower() == '!cleanup' and ('admins' in self.settings and message.author.id in self.settings['admins']):
			for i in self.games:
				await i.cleanup(clean_finish = False)
		for i in self.games:
			if i.status != 0 and message.channel == i.channel:
				#print('forwarded message to game')
				await i.handle_msg(message)
				return
		if msg.lower() == settings.command_prefix + 'start':
			# extra condition: don't allow start if there's no active lobby
			# break conditions: not having enough players, someone who isnt the owner starting
			if self.active_lobby < 0:
				await message.channel.send(f'No party is currently active. Type {settings.command_prefix}setup to start a party.')
				return
			if self.games[self.active_lobby].owner != message.author.id:
				msg = 'Only the party leader may start the  game.'
				await message.channel.send(msg)
				return
			if len(self.games[self.active_lobby].players) > settings.max_players:
				msg = 'Not enough players to start.'
				await message.channel.send(msg)
				return
			# start game
			game = self.games[self.active_lobby]
			self.active_lobby = -1
			# add emoji join players
			for i in set(game.emoji_join.keys()).difference(set(game.players.keys())):
				if i not in self.bot_state.players:
					u = game.emoji_join[i]
					player = Game_Player(u.id, game, u.name, u)
					game.players[i] = player
					o = util.Object()
					o.last_action = time()
					o.game = game
					self.bot_state.players[i] = o

			self.settings['game_count'] += 1
			await game.start_game()
				
		elif msg.lower().startswith(settings.command_prefix + 'setup'):
			# Check if player is already in a lobby
			if message.author.id in self.bot_state.players:
				g = self.bot_state.players[message.author.id].game
				msg_out = ''
				if g.status == 0:
					msg_out = f'You are already in a party.'
				else:
					msg_out = 'You are already in a game.'
				await message.channel.send(msg_out)
				return
			# check opts
			opts = msg.lower().split(' ')[1:]
			allowed_opts = { 'random_roles', 'no_third_party', 'hardcore_jester', 'preserve_channel' }
			invalid_opts = set(opts).difference(allowed_opts)
			if len(invalid_opts) != 0:
				await message.channel.send(f'Unknown option(s): {", ".join(invalid_opts)}')
				return
			# Check if a lobby is already in progress
			for i in self.games:
				if i.status == 0 and len(i.players) == settings.max_players:
					msg_out = f'A lobby is already in progress. React with {settings.start_emoji} to join.'
					await message.channel.send(content=msg_out)
					return
			self.lobby_count += 1
			game = Game_State(self, message)
			sender_id = message.author.id
			game.owner = sender_id
			p = Game_Player(sender_id, game, message.author.name, message.author)
			game.players[sender_id] = p
			game.options = opts
			
			new_p = util.Object()
			new_p.game = game
			new_p.last_action = time()
			self.bot_state.players[sender_id] = new_p
			
			self.active_lobby = len(self.games)
			self.games.append(game)
			
			msg = f'A party has started. React with {settings.start_emoji} to this message to join.'
			if opts != []:
				msg += f' Options are: {opts}.'
			await message.channel.send(content=msg)
			
		elif msg.lower() == settings.command_prefix + 'leaderboard' or msg.lower() == '!leaderboard-all':
			if len(self.score_record) == 0:
				await message.channel.send('No games have been played on this server yet.')
				return
				
			out_msg = 'Leaderboard:'
			scores = list(map(lambda x: (x, self.score_record[x][0], self.score_record[x][1]), self.score_record))
			scores.sort(key = lambda x: x[1] - x[2], reverse = True)
			if msg.lower() != '!leaderboard-all':
				scores = scores[:5]
			for i in scores:
				name = self.get_cached_name(i[0])
				out_msg += f'\n{name}: {i[1]}-{i[2]}'
				if len(out_msg) > 8000:
					break
			
			await message.channel.send(out_msg)
			return
		elif msg.lower() == settings.command_prefix + 'score':
			id = message.author.id
			if id not in self.score_record:
				await message.channel.send('You haven\'t played any games on this server.')
				return
			s = self.score_record[id]
			name = self.get_cached_name(i[0])
			await message.channel.send(f'History for {name}: {s[0]}-{s[1]}')
			return
			
	def end_game(self, game):
		for i in game.players.keys():
			if i in self.bot_state.players:
				del self.bot_state.players[i]
		game.players = {}
		active_lobby = self.active_lobby
		self.games = list(filter(lambda x : x != game, self.games))
		if active_lobby > len(self.games):
			# Adjust active game
			self.active_lobby -= 1

	def get_cached_name(self, id):
		if id not in self.bot_state.name_cache:
			return 'UNKNOWN'
		return self.bot_state.name_cache[id]