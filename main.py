#!/bin/python3


import discord
import random
import asyncio
import time
import math
import settings
import server
import util
import pickle
from log import log_msg

#state_lock = asyncio.Lock()
bot_state = util.Object()
#client = discord.Client(intents = discord.Intents.all())
client = discord.Client()

def get_server(guild):
	server_id = guild.id
	# Server may not exist or may exist in un-inited state.
	if server_id not in bot_state.servers:
		log_msg(f'New server {guild.name} ({server_id})')
		bot_state.servers[server_id] = server.Server_State(bot_state, client, guild)
	elif not bot_state.servers[server_id].inited:
		bot_state.servers[server_id].full_init(bot_state, client, guild)
		
	return bot_state.servers[server_id]

def handle_emoji(reaction, user, add = True):
	if user.id == client.user.id:
		return
	guild = reaction.message.guild
	if guild == None:
		return
	server_id = guild.id
	srv = get_server(guild)
	if srv.active_lobby != -1:
		game = srv.games[srv.active_lobby]
		if reaction.message.id == game.emoji_join_msg_id:
			if add:
				game.emoji_join[user.id] = user
			else:
				del game.emoji_join[user.id]

@client.event
async def on_message(message):
	bot_state.name_cache[message.author.id] = f'{message.author.name}#{message.author.discriminator}'
	# Ignore messages from this bot
	if message.author.id == client.user.id:
		if message.content.startswith('A party has started. React with '):
			srv = get_server(message.guild)
			await message.add_reaction(srv.settings['start_emoji'])
			if srv.active_lobby != -1 and srv.games[srv.active_lobby].status == 0:
				srv.games[srv.active_lobby].emoji_join_msg_id = message.id
			
		return
	if message.channel.type == discord.ChannelType.text:
		server_id = message.guild.id
		srv = get_server(message.guild)
		await srv.handle_msg(message)
		return
	elif message.channel.type == discord.ChannelType.private:
		# private message
		print(f'DM / {message.author.name}: {message.content}')
		if message.author.id in bot_state.players:
			data = bot_state.players[message.author.id]
			await data.game.handle_dm(message)
			return
		else:
			await message.channel.send('you\'re not in a game, try signing up lol')
			return
			
@client.event
async def on_reaction_add(reaction, user):
	handle_emoji(reaction, user, True)
	
@client.event
async def on_reaction_remove(reaction, user):
	handle_emoji(reaction, user, False)

	
	
@client.event
async def on_ready():
	print(f'Logged in as {client.user.name}')

if __name__ == '__main__':
	bot_state.servers = {}
	bot_state.players = {} # dict player id -> { game ptr, last_action }
	bot_state.name_cache = {} # player id -> name#discriminator
	try:
		with open('server_cache', 'rb') as f:
			data = pickle.load(f)
			for i in data:
				vals = data[i]
				bot_state.servers[i] = server.Server_State()
				for i2 in vals['settings']:
					bot_state.servers[i].settings[i2] = vals['settings'][i2]
				bot_state.servers[i].score_record = vals['score_record']
				print(vals)
		with open('name_cache', 'rb') as f:
			bot_state.name_cache = pickle.load(f)
	except BaseException as e:
		print(e)
		
	try:
		client.run(settings.bot_token)
	except Exception as e:
		print(e)
		
	with open('server_cache', 'wb') as f:
		data = {}
		for i in bot_state.servers:
			data[i] = { 'settings' : bot_state.servers[i].settings, 'score_record' : bot_state.servers[i].score_record }
		f.write(pickle.dumps(data))
		print(data)
		
	with open('name_cache', 'wb') as f:
		f.write(pickle.dumps(bot_state.name_cache))