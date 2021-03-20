import discord
import settings
import asyncio
import random
import util
from time import time
from roles import *
from log import *
import third_party
import mafia
import town
import re
import matchmaking as mm

class Game_Player:
	def __init__(self, id, game, name, member):
		self.id = id
		self.role = 0
		self.game = game
		self.name = name
		self.member = member
		self.role_data = {}
		self.translation_list = {}
		self.recent_msgs = []
		self.is_alive = True
		self.game = None
		self.old_channel = None
		self.is_muted = False
		
		# Default role state data
		self.role_data['is_cursed'] = []
		self.msg_buffer = ''
		self.nickname_set = False
		
	async def send_msg(self, msg, flush = False):
		if self.msg_buffer != '':
			self.msg_buffer += '\n'
		self.msg_buffer += msg
		if flush:
			await self.flush_buffers()
		
	async def flush_buffers(self):
		if self.member != None and self.msg_buffer != '':
			await self.member.send(self.msg_buffer)
			self.msg_buffer = ''
			
	async def set_nickname(self, nick):
		try:
			if not self.nickname_set:
				if self.member.nick != None:
					self.old_nick = self.member.nick
				else:
					self.old_nick = ''
			self.nickname_set = True
			await self.member.edit(nick=nick)
		except Exception as e:
			print(f'set_nickname: {e}')
		
	async def clear_nickname(self):
		try:
			if self.nickname_set:
				await self.member.edit(nick=self.old_nick)
				self.nickname_set = False
		except Exception as e:
			print(f'clear_nickname: {e}')

class Game_State:	
	def __init__(self, server, message):
		self.server = server
		self.channel = message.channel
		self.original_channel = message.channel

		self.owner = message.author.id
		self.status = 0 # 0 = setup, 1 = day, 2 = night
		self.players = {}
		self.voice_channel = None
		self.new_role = None
		self.owner = 0
		self.unique_id = int(time())
		self.recent_msgs = []
		
		self.protected_players = []
		
		self.gameplay_state = {}
		self.visits = []
		self.settings = server.settings.copy()
		self.turn_number = 0
		self.emoji_join = {}
		self.emoji_join_msg_id = 0
		self.options = []
		self.state = {}

		
	async def start_game(self):
		# check start conditions
		#	send error message if failed
		#  	minimum players, maximum players?
		if len(self.players) < settings.min_players:
			await self.channel.send(f'Minimum {settings.min_players} players to start the game')
			return
		if len(self.players) > settings.max_players:
			await self.channel.send('too many players. this message should never happen')
			return
			
		mm.gen_game_comp(self)
		# start the game
		for i in self.players.values():
			u = self.server.client.get_user(i.id)
			if u != None:
				if u.dm_channel == None:
					try:
						await u.create_dm()
					except:
						pass
		
		
		self.state['janitor_cleans_remaining'] = 2 + len(self.players) // 8
		# send server message to start game and message all players their role
		for i in self.players.values():
			i.discord_user = self.server.client.get_user(i.id)
			await i.send_msg(f'Your role is {get_role_name(i.role)}. Description: {get_role_description(i.role)}')
		
		self.settings['enable_role_reveal'] = self.settings['role_reveal_players'] <= len(self.players)
		await self.channel.send(f'Game #{self.settings["game_count"]} has started.')
		
		# create role for members
		game_name = f'Mafia_{self.settings["game_count"]}'
		new_role = None
		try:
			new_role = await self.server.guild.create_role(name = game_name, mentionable = False, reason = 'Mafia game')
			log_msg(f'Role creation success for game {game_name}')
		except Exception as e:
			print(e)
			await self.channel.send(e)
			return
		# add role to members
		member_list = []
		server_members = []
		try:
			server_members = await self.server.guild.fetch_members(limit=None).flatten()
		except BaseException as e:
			print(f'failed to get server members {e}')
		for i in self.players.values():
			if i.member == None:
				print(f'trying {i.id}')
				i.member = self.server.guild.get_member(i.id)
				if i.member == None:
					# fall back to fetch_members
					print(f'{i.id} resolved to none')
					for x in server_members:
						if x.id == i.id:
							i.member = x
							break
					if i.member == None:
						print('failed to resolve through get_member')
						continue
			await i.member.add_roles(new_role)
		
		self.new_role = new_role
		
		# create channel for game
		server_overwrites = {
			self.server.guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages = False),
			new_role: discord.PermissionOverwrite(read_messages=True),
			self.server.guild.me: discord.PermissionOverwrite(read_messages=True)
		}
		try:
			self.channel = await self.server.guild.create_text_channel(game_name, overwrites = server_overwrites)
			print('channel creation success')
		except BaseException as e:
			print(e)
			return
		try:
			self.voice_channel = await self.server.guild.create_voice_channel(game_name, overwrites = server_overwrites)
		except BaseException as e:
			print(e)
			return
			
		mafia_list = list(filter(lambda x: is_mafia(x.role), self.players.values()))
		msg = 'The mafia is composed of:\n' + '\n'.join(list(map(lambda x: f'{x.name}: {get_role_name(x.role)}', mafia_list)))
		for i in mafia_list:
			await i.send_msg(msg)
			
		log_msg(f'Game #{self.settings["game_count"]} Start')
		for i in self.players.values():
			log_msg(f'{i.name} => {get_role_name(i.role)}')
			try:
				if i.member.voice != None:
					i.old_channel = i.member.voice.channel
				await i.member.move_to(channel = self.voice_channel, reason='Mafia start')
			except BaseException as e:
				print(e)
				pass
		await self.flush_messages()
		self.status = -1
		await asyncio.sleep(10)
		await self.set_state(2)
	
	async def handle_dm(self, message):
		id = message.author.id
		assert(id in self.players.keys())
		player = self.players[id]
		player.recent_msgs.append(message.content)
		
	async def handle_msg(self, message):
		self.recent_msgs.append(message)
		id = message.author.id
		if message.content.lower() == '!reveal':
			if id in self.players and self.players[id].role == Role.mayor:
				if 'revealed_mayor' not in self.players[id].role_data:
					self.players[id].role_data['revealed_mayor'] = True
					await self.channel.send(f'{message.author.name} has revealed themselves as the mayor! Their vote will count for extra for the rest of the game')
		
	async def mute_player(self, player, mute = True):
		if player.is_muted != mute:
			await player.member.edit(mute = mute)
			player.is_muted = mute
	
	async def set_state(self, new_state):
		val = await self.check_victory_conditions()
		if val != None:
			return
		await self.flush_messages()
		self.status = new_state
		if new_state == 1:
			# day time
			self.turn_number += 1
			log_msg('Day cycle')
			await self.channel.send('It is now day time. You may now discuss the events of last night. Players may be called to the stand with !nominate @name')
			
			overwrites = {
				self.server.guild.default_role: discord.PermissionOverwrite(send_messages=False, speak = False),
				self.new_role: discord.PermissionOverwrite(speak = True, send_messages = True)
			}
			not_mute_perm = discord.PermissionOverwrite(send_messages = True)
			mute_perm = discord.PermissionOverwrite(send_messages = False)
			blackmailer_mutes = []
			for i in self.players.values():
				if i.role == Role.blackmailer:
					if 'blackmail_target' in i.role_data and i.role_data['blackmail_target'] != None:
						blackmailer_mutes.append(i.role_data['blackmail_target'].id)
						i.role_data.pop('blackmail_target') # remove
			for i in self.players.values():
				i.recent_msgs = []
				try:
					if not i.is_alive or i.id in blackmailer_mutes:
						await self.mute_player(i, mute = True)
						overwrites[i.member] = mute_perm
					else:
						await self.mute_player(i, mute = False)
						overwrites[i.member] = not_mute_perm
				except BaseException as e:
					print(e)
					
			for i in blackmailer_mutes:
				#await i.discord_user.edit(nick=f'{self.players[i].name} (Muted)')
				p = self.players[i]
				await p.set_nickname(f'{p.name} (Muted)')
				
			for i in self.players.values():
				if i.id not in blackmailer_mutes:
					await i.clear_nickname()
			
			await self.channel.edit(overwrites=overwrites, reason = 'Mafia day phase')
			await self.voice_channel.edit(overwrites=overwrites, reason = 'Mafia day phase')
			day_start_t = time()
			
			round_finished = False
			self.recent_msgs = []
			nominees = {}
			called_player = None
			time_alerts = []
			while not round_finished:
				# spam sleep until we get a first nomination
				await asyncio.sleep(1)
				
				for i in self.recent_msgs:
					res = re.match(r'!nominate <@!?(\d+)>', i.content.lower())
					if res != None:
						id = int(res[1])
						if id != i.author.id:
							if id in self.players and self.players[id].is_alive:
								name = self.players[id].name
								nom = i.author.name
								if id not in nominees:
									nominees[id] = [ i.author.id ]
								else:
									if i.author.id in nominees[id]:
										# Already voted, skip
										continue
									else:
										called_player = id
										nominees = {}
										self.recent_msgs = []
								await self.channel.send(f'{nom} has nominated {name} to take the stand.')
				
				if called_player != None:
					name = self.players[called_player].name
					await self.channel.send(f'{name} was called to the stand. You have 1 minute to present your case.')
					await asyncio.sleep(45)
					await self.channel.send(f'15 seconds remaining...')
					await asyncio.sleep(15)
					await self.channel.send(f'It\'s time to vote. Should {name} be executed? Vote by typing !yes or !no in DM.')
					# clear recent msgs to allow voting
					valid_players = list(filter(lambda x: x.is_alive and x.id != called_player, self.players.values()))
					for i in valid_players:
						i.recent_msgs = []
					for i in valid_players:
						await i.send_msg(f'This is your chance to vote to execute {name}. Respond with !yes or !no to vote.', flush = True)
					self.recent_msgs = []
					
					await asyncio.sleep(30)
					votes = {}
					for i in filter(lambda x: x.is_alive, self.players.values()):
						votes[i.id] = -1
					#votes[called_player] = 0 # called players cannot vote against themselves

					for i in filter(lambda x: x.is_alive and x.id != called_player, self.players.values()):
						for i2 in reversed(i.recent_msgs):
							msg = i2.lower()
							if msg == '!yes' or msg == '!no':
								votes[i.id] = 1 if msg == '!yes' else 0
								break
								
					yes_count = len(list(filter(lambda x: x == 1, votes.values())))
					#no_count = len(list(filter(lambda x: x == 0, votes.values())))
					no_count = len(valid_players) - yes_count
					# Add extra votes for revealed mayors
					
					for i in votes:
						if 'revealed_mayor' in self.players[i].role_data:
							if votes[i] == 0 or votes[i] == -1:
								no_count += 1
							else:
								yes_count += 1
					
					vote_msg = '\nVotes:'
					for i in votes:
						val = votes[i]
						m = 'Yes'
						if val == -1:
							m = 'No (abstain)'
						elif val == 0:
							m = 'No'
						vote_msg += f'\n{self.players[i].name}: {m}'
						
					#await self.channel.send(vote_msg)
					# default vote no if they don't vote
					#print(f'{yes_count} yes votes, {no_count} no votes')
					if yes_count > no_count:
						round_finished = True
						msg = f'{name} has been executed.'
						if self.settings['enable_role_reveal']:
							msg = f'{name} ({get_role_name(self.players[called_player].role)}) has been executed.'
						p = self.players[called_player]
						if p.role == Role.jester or (p.role == Role.executioner and p.role_data['is_jester']):
							msg = f'{name} has been executed. The jester wins!'
							id = self.players[called_player].id
							if id not in self.server.score_record:
								self.server.score_record[id] = (0, 0)
							score = self.server.score_record[id]
							self.server.score_record[id] = (score[0] + 1, score[1])
							self.players[called_player].role_data['won_game'] = True
							# Check for hardcore jester condition
							if await self.check_victory_conditions(jester_executed = self.players[called_player]) != None:
								return
						for i in filter(lambda x: x.is_alive and x.role == Role.executioner, self.players.values()):
							if 'marked_player' in i.role_data and i.role_data['marked_player'] == called_player:
								msg += f'\n{name} was marked for death by {i.name}. The executioner wins!'
								i.role_data['won_game'] = True
								
						await self.mute_player(self.players[called_player], mute = True)
						self.players[called_player].is_alive = False
						
						msg += '\nThe day is now over.'
					else:
						msg = f'{name} has been removed from the stand.'
						# Don't allow a second vote if the day is almost over
						if time() - day_start_t < self.settings['day_duration'] - 20:
							msg += "\nAdditional nominations may be made for the remainder of the day."
						called_player = None
						
					msg += vote_msg
					await self.channel.send(msg)
					await asyncio.sleep(6)
					# Clear recent msgs to allow for another vote
					for i in valid_players:
						i.recent_msgs = []
					self.recent_msgs = []
				else:
					if time() - day_start_t < self.settings['day_duration'] and not round_finished:
						t_remaining = int(time() - day_start_t)
						if t_remaining > self.settings['day_duration'] - 60 and 1 not in time_alerts:
							#await self.channel.send('1 minute remaining for the day...')
							await self.channel.send(f'{t_remaining} seconds remaining for the day.')
							time_alerts.append(1)
							time_alerts.append(2)
						#elif time() - day_start_t > self.settings['day_duration'] - 120 and 2 not in time_alerts:
						#	await self.channel.send('2 minutes remaining for the day...')
						#	time_alerts.append(2)
				if time() - day_start_t > self.settings['day_duration'] and not round_finished:
					# Day expired
					round_finished = True
				
				
			await self.set_state(2)
			return
		elif new_state == 2:
			# night time
			log_msg('night cycle')
			await self.channel.send('It is now night time!')
			
			overwrites = {
				self.new_role: discord.PermissionOverwrite(speak = False, send_messages = False)
			}
			await self.channel.edit(overwrites=overwrites, reason = 'Mafia night phase')
			await self.voice_channel.edit(overwrites=overwrites, reason = 'Mafia night phase')
			
			mute_perm = discord.PermissionOverwrite(send_messages = False)
			for i in self.players.values():
				i.recent_msgs = []
				try:
					await self.mute_player(i, mute = True)
				except BaseException as e:
					print(e)
			
			self.doctor_protecting = []
			self.visits = []
			for i in filter(lambda x: x.is_alive, self.players.values()):
				if is_mafia(i.role):
					await mafia.play_night(self, i)
				elif is_town(i.role):
					await town.play_night(self, i)
				elif is_third_party(i.role):
					await third_party.play_night(self, i)
				
			await self.flush_messages()
			await asyncio.sleep(self.settings['night_duration'] - 15)
			await self.channel.send('15 seconds of night remaining...')
			await asyncio.sleep(15)
			# Town to play first - Return targets which should die if left unprotected
			t = []
			# Play veteran first so they can kill visitors
			for i in self.players.values():
				if i.role == Role.veteran:
					await town.play_night_end(self, i)
			for i in filter(lambda x: is_town(x.role) and x.role != Role.veteran, self.players.values()):
				val = await town.play_night_end(self, i)
				if type(val) == type([]):
					t += val
				else:
					t.append(val)

			# Mafia to play
			for i in filter(lambda x: is_mafia(x.role), self.players.values()):
				val = await mafia.play_night_end(self, i)
				if type(val) == type([]):
					t += val
				else:
					t.append(val)
				
			for i in filter(lambda x: is_third_party(x.role), self.players.values()):
				val = await third_party.play_night_end(self, i)
				# third party may return a list
				if type(val) == type([]):
					t += val
				else:
					t.append(val)
			kill_targets = list(filter(lambda x: x != None, t))
			
			# Check for witch victory condition before continuing
			if await self.check_victory_conditions() != None:
				return

			votes = {}
			# votes[id] = (count, godfather)
			for i in filter(lambda x: x.is_alive and mafia.is_voting_role(x), self.players.values()):
				vote = mafia.get_vote(i)
				vote_id = None
				if vote != None:
					vote_id = vote.id
				if vote_id not in votes:
					votes[vote_id] = (0, False)
				record = votes[vote_id]
				votes[vote_id] = (record[0] + 1, record[1] or i.role == Role.godfather)
			do_not_reveal = []
			if len(votes):
				# (id, vote count, godfather voted)
				vote_count = []
				for i in votes:
					v = votes[i]
					vote_count.append((i, v[0], v[1]))
				vote_count.sort(key = lambda x: x[1], reverse = True)
				
				janitor_alive = Role.janitor in list(map(lambda x: x.role, self.players.values()))
				clean_kill = janitor_alive and self.state['janitor_cleans_remaining'] > 0
				# Delete all non-tied votes
				votes = list(filter(lambda x: x[1] == vote_count[0][1], vote_count))
				target = votes[0][0]
				log_msg(f'votes = {votes}')
				# Check for ties, use godfather as tie-breaker
				if len(votes) > 1 and len(list(filter(lambda x: x.role == Role.godfather, self.players.values()))):
					# if more than one godfather tie vote, random pick
					votes_gf = list(filter(lambda x: x[2], votes))
					if len(votes_gf) != 0:
						random.shuffle(votes_gf)
					target = votes_gf[0][0]
				# Mafia may vote to kill nobody
				if target != None:
					target = self.players[target]
					mafia_tiers = [ Role.mafioso, Role.janitor, Role.consigliere, Role.godfather ]
					protection = util.find_bodyguard_protection(self)
					mafia_dies = False
					if target.id in protection:
						mafia_dies = True
						kill_targets.append(protection[target.id])
						do_not_reveal.append(protection[target.id].id)
					elif target.role == Role.veteran and target.role_data['on_alert']:
						mafia_dies = True
						
					if mafia_dies:
						# Find random member of lowest possible rank
						pl = list(self.players.values())
						random.shuffle(pl)
						for i in mafia_tiers:
							l = list(filter(lambda x: x.role == i and x.is_alive, pl))
							if len(l):
								kill_targets.append(l[0])
								if clean_kill:
									do_not_reveal.append(l[0])
									self.state['janitor_cleans_remaining'] -= 1
								break
					else:
						kill_targets.append(target)
						if clean_kill:
							do_not_reveal.append(target.id)
							self.state['janitor_cleans_remaining'] -= 1

			msg = 'The night is now over.'
			for i in kill_targets:
				if i == None:
					continue
				# Players may be killed multiple ways, check to make sure we don't re-kill them
				if not i.is_alive:
					continue
				# Survivor and serial killer cannot die during night phase
				if i.role == Role.survivor:
					# Only allow one survival
					if 'nerf_survivor' in self.options:
						if 'survived_previously' not in i.role_data:
							i.role_data['survived_previously'] = True
							continue
					else:
						continue
				if i.role == Role.serial_killer:
					continue
				if i.id not in self.doctor_protecting or 'die_next_turn' in i.role_data:
					if i.id in do_not_reveal or not self.settings['enable_role_reveal']:
						msg += f'\n{i.name} was found dead.'
						if i.id in do_not_reveal and janitor_alive:
							msg += ' Their role was not revealed.'
					else:
						msg += f'\n{i.name} was found dead. They were found to be a {get_role_name(i.role)}'
					i.is_alive = False
					await i.send_msg("You are dead. You may continue to listen in, but cannot speak.")
			for i in self.players.values():
				if i.is_alive and i.role == Role.blackmailer:
					if 'blackmail_target' in i.role_data and i.role_data['blackmail_target'] != None:
						msg += f'\n{i.role_data["blackmail_target"].name} has been blackmailed.'
			for i in self.players.values():
				if 'bg_protecting' in i.role_data:
					i.role_data.pop('bg_protecting', None)
			await self.flush_messages()
			await self.channel.send(msg)
			await self.set_state(1)
		else:
			assert(False)
	
	async def flush_messages(self):
		for i in self.players.values():
			await i.flush_buffers()
	
	async def check_victory_conditions(self, jester_executed = None):
		alive_players = list(filter(lambda x: x.is_alive, self.players.values()))
		n_town = len(list(filter(lambda x: is_town(x.role), alive_players)))
		n_mafia = len(list(filter(lambda x: is_mafia(x.role), alive_players)))
		n_third_party = len(list(filter(lambda x: is_third_party(x.role), alive_players)))
		n_bad_third_party = len(list(filter(lambda x: x.role == Role.werewolf or x.role == Role.serial_killer, alive_players)))
		n_survivors = len(list(filter(lambda x: x.role == Role.survivor, alive_players)))
		role_msg = ''
		
		if jester_executed != None and 'hardcore_jester' in self.options:
			await self.original_channel.send('Jester wins!')
			await self.cleanup()
			return True
		
		if len(alive_players) == 0:
			await self.original_channel.send('Draw!')
			await self.cleanup()
			return True
		
		for i in filter(lambda x: x.role == Role.witch, alive_players):
			if len(list(filter(lambda x: i.id in x.role_data['is_cursed'], alive_players))) == len(alive_players) - 1:
				i.role_data['won_game'] = True
				await self.original_channel.send(f'{i.name} (Witch) wins!')
				await self.cleanup()
				return i.id
		
		for i in filter(lambda x: (x.role == Role.werewolf or x.role == Role.serial_killer) and x.is_alive, self.players.values()):
			if len(list(filter(lambda x: x.is_alive, self.players.values()))) <= 2:
				i.role_data['won_game'] = True
				await self.original_channel.send(f'{i.name} ({get_role_name(i.role)}) wins!')
				await self.cleanup()
				return i.id
		
		
		if n_mafia == 0 and n_bad_third_party == 0:
			for i in filter(lambda x: is_town(x.role), self.players.values()):
				i.role_data['won_game'] = True
			try:
				await self.original_channel.send('Town wins!')
				await self.original_channel.send(role_msg)
			except:
				pass
			for i in filter(lambda x: is_town(x.role), self.players.values()):
				i.role_data['won_game'] = True
			await self.cleanup()
			return 1
		if n_mafia >= n_town + n_third_party:
			for i in filter(lambda x: is_mafia(x.role), self.players.values()):
				i.role_data['won_game'] = True
			await self.original_channel.send('Mafia wins!')
			await self.cleanup()
			return 2
		return None
		
	async def cleanup(self, clean_finish = True):
		# delete role and channel
		role = self.new_role
		channel = self.channel
		voice_channel = self.voice_channel
		
		if clean_finish:
			try:
				for i in self.players.values():
					won = 'won_game' in i.role_data
					val = list(filter(lambda x: x[0] == i.role, self.server.settings['role_balance']))
					if len(val) == 0:
						self.server.settings['role_balance'].append((i.role, 0, 0))
						val = (i.role, 0, 0)
					else:
						val = val[0]
					if won:
						val = (val[0], val[1] + 1, val[2])
					else:
						val = (val[0], val[1], val[2] + 1)
					for i2 in range(len(self.server.settings['role_balance'])):
						if self.server.settings['role_balance'][i2][0] == i.role:
							self.server.settings['role_balance'][i2] = val
							break
			except BaseException as e:
				print(f'mm error: {e}')
				
			role_msg = 'Roles:'
			for i in self.players.values():
				await i.flush_buffers()
				role_msg += f'\n{i.name}: {get_role_name(i.role)}'
				if 'won_game' in i.role_data:
					role_msg += ' (Winner)'
			
			await self.original_channel.send(role_msg)
			
			winners = list(map(lambda x: x.id, filter(lambda x: 'won_game' in x.role_data, self.players.values())))
			losers = list(filter(lambda x: x not in winners, self.players))
			
			if len(winners) != 0:
				self.server.update_scores(winners = winners, losers = losers)
		
		# Unmute everyone, then move to old channel
		action_count = 0
		for i in self.players.values():
			await i.clear_nickname()
			try:
				if i.is_muted:
					await i.member.edit(mute = False)
					action_count += 1
			except BaseException as e:
				print(e)
				
		await asyncio.sleep(action_count)
		for i in self.players.values():
			try:
				if i.old_channel != None:
					await i.member.move_to(channel = i.old_channel)
			except BaseException as e:
				print(e)
		
		self.server.end_game(self)
		
		if clean_finish:
			await asyncio.sleep(25)
		
		try:
			await self.new_role.delete(reason='Game finished')
			if 'preserve_channel' not in self.options:
				await self.channel.delete(reason='Game finished')
			await self.voice_channel.delete(reason='Game finished')
		except:
			pass
