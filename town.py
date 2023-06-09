from roles import *
import util
import generic
from log import *

vote_addendum = ' Only the final vote will count.'

async def doctor_play_night(game, player):
	pass

async def play_night(game, player):
	player.translation_list = {}
	if not player.is_alive:
		return
	player.recent_msgs = [] # Reset recent messages so we don't re-vote accidentally
	if player.role == Role.veteran:
		player.role_data['on_alert'] = False
		if 'alert_remaining' not in player.role_data:
			player.role_data['alert_remaining'] = 2 + len(game.players) // 8
		if player.role_data['alert_remaining'] > 0:
			n = player.role_data['alert_remaining']
			msg = f'Would you like to go on alert tonight? Respond with "yes" or "no". You have {n} alerts remaining.'
			await player.send_msg(msg)
		return
	if player.role == Role.doctor:
		already_self_protected = False
		if 'already_self_protected' in player.role_data:
			already_self_protected = True
			
		players = list(filter(lambda x: x.is_alive and (x.id != player.id or (x.id == player.id and not already_self_protected)), game.players.values()))
		players = list(filter(lambda x: 'revealed_mayor' not in x.role_data, players))
		#players = list(filter(lambda x: x.role == Role.mayor and x.role_data == None, players))
		tl = util.generate_translation_list(players)
		if len(tl) <= 1:
			return
		player.translation_list = tl
		msg = 'Who would you like to protect tonight?'
		msg += util.generate_selection_list(tl)
		msg += '\n\nRespond with the letter corresponding to the person you wish to protect.' + vote_addendum
		await player.send_msg(msg)
		return
	if player.role == Role.bodyguard:
		if 'bg_protecting' in player.role_data:
			del player.role_data['bg_protecting']
		players = filter(lambda x: x.id != player.id and x.is_alive, game.players.values())
		tl = util.generate_translation_list(players)
		if len(tl) <= 1:
			return
		player.translation_list = tl
		msg = 'Who would you like to protect tonight?'
		msg += util.generate_selection_list(tl)
		msg += '\n\nRespond with the letter corresponding to the person you wish to protect.' + vote_addendum
		await player.send_msg(msg)
		return
	if player.role == Role.deputy:
		if 'upgraded' not in player.role_data:
			player.role_data['upgraded'] = False
		sheriffs = list(filter(lambda x: x.role == Role.sheriff, game.players.values()))
		for i in sheriffs:
			if i.is_alive:
				return
		if player.role_data['upgraded'] == False:
			player.role_data['upgraded'] = True
			await player.send_msg('All sheriffs are dead. You have been promoted to a sheriff.')
		# fall through to next condition
	if player.role == Role.sheriff or (player.role == Role.deputy and player.role_data['upgraded']):
		tl = util.generate_translation_list(game.players.values(), lambda x: x.id != player.id and x.is_alive)
		if len(tl) <= 1:
			return
		player.translation_list = tl
		msg = 'Who would you like to look at tonight?'
		msg += util.generate_selection_list(tl)
		msg += '\n\nRespond with the letter corresponding to the person you wish to investigate.' + vote_addendum
		await player.send_msg(msg)
		return
	if player.role == Role.investigator:
		if 'investigation_count' not in player.role_data:
			player.role_data['investigation_count'] = 1 + len(game.players) // 6
		# 0-5 = 1, 6-11 = 2, 12-17 = 3
		if player.role_data['investigation_count'] == 0:
			#await player.send_msg('You cannot investigate any more people.')
			return
		tl = util.generate_translation_list(game.players.values(), lambda x: x.id != player.id and x.is_alive)
		if len(tl) <= 1:
			return
		player.translation_list = tl
		msg = 'Who would you like to investigate tonight?'
		msg += util.generate_selection_list(tl)
		msg += '\n\nRespond with the letter corresponding to the person you wish to investigate.' + vote_addendum
		await player.send_msg(msg)
		return
	if player.role == Role.medium:
		if 'investigation_count' not in player.role_data:
			player.role_data['investigation_count'] = 1 + len(game.players) // 6
		if player.role_data['investigation_count'] == 0:
			#await player.send_msg('You cannot investigate any more people.')
			return
		tl = util.generate_translation_list(game.players.values(), lambda x: not x.is_alive)
		if len(tl) <= 1:
			return
		player.translation_list = tl
		msg = f'Who would you like to investigate tonight? You have {player.role_data["investigation_count"]} investigations remaining.'
		msg += util.generate_selection_list(tl)
		msg += '\n\nRespond with the letter corresponding to the person you wish to investigate.' + vote_addendum
		await player.send_msg(msg)
		return
	if player.role == Role.vigilante:
		if 'die_next_turn' in player.role_data and not game.players[player.role_data['die_next_turn']].is_alive:
			name = game.players[player.role_data['die_next_turn']].name
			await player.send_msg(f'You discovered that {name} was good and will commit suicide tonight.')
			return
		if 'bullets_remaining' not in player.role_data:
			player.role_data['bullets_remaining'] = 1 + len(game.players) // 8
		if 'bullets_remaining' in player.role_data and player.role_data['bullets_remaining'] == 0:
			return
		tl = util.generate_translation_list(game.players.values(), lambda x: x.id != player.id and x.is_alive)
		if len(tl) <= 1:
			return
		player.translation_list = tl
		rem = player.role_data['bullets_remaining']
		msg = f'Who would you like to kill tonight? You have {rem} bullet remaining.'
		msg += util.generate_selection_list(tl)
		msg += '\n\nRespond with the letter corresponding to the person you wish to kill.'
		await player.send_msg(msg)
		return
	if player.role == Role.basic_town:
		# Role does nothing during night
		return
	if player.role == Role.politician:
		# no role
		return
	if player.role == Role.mayor:
		# no role
		return
	if player.role == Role.survivor:
		# no actions
		return
	await player.send_msg('Your role is not implemented')
	
async def play_night_end(game, player):
	if not player.is_alive:
		return
	if player.role == Role.veteran:
		go_on_alert = False
		if player.role_data['alert_remaining'] <= 0:
			return
		for i in reversed(player.recent_msgs):
			if i.lower() == 'yes':
				go_on_alert = True
				player.role_data['alert_remaining'] -= 1
				break
			elif i.lower() == 'no':
				go_on_alert = False
				break
		player.role_data['on_alert'] = go_on_alert
		if go_on_alert:
			await player.send_msg('You went on alert tonight.')
		return
	if player.role == Role.sheriff or (player.role == Role.deputy and player.role_data['upgraded']):
		target = get_vote(player)
		if target == None:
			await player.send_msg('You did not investigate anyone this night.')
			return
		if target != None:
			name = target.name
			# Godfather comes up as good, politician as bad
			# Werewolf is good on odd days
			good_day = game.turn_number % 2 == 0 and target.role == Role.werewolf
			good = target.role == Role.godfather or (is_town(target.role) and target.role != Role.politician) or good_day
			await player.send_msg(f'You investigated {name} and they came up as {"Good" if good else "Bad"}')
			if target.role == Role.veteran and target.role_data['on_alert']:
				return player
			return
	if player.role == Role.doctor:
		target = get_vote(player)
		if target == None:
			await player.send_msg('You did not protect anyone this night.')
			return
		if target != None:
			# Only allow self protection once
			if target == player:
				player.role_data['already_self_protected'] = True
			elif target.role == Role.veteran and target.role_data['on_alert']:
				# veteran can't die anyway
				return player
			log_msg(f'{player.name} chose to protect {target.name}')
			if target not in game.protected_players:
				game.protected_players.append(target)
			name = target.name
			await player.send_msg(f'You chose to protect {name} tonight.')
			game.doctor_protecting.append(target.id)
			return
	if player.role == Role.bodyguard:
		target = get_vote(player)
		if target == None:
			await player.send_msg('You did not protect anyone this night.')
			#player.role_data['bg_protecting'] = 0
			if 'bg_protecting' in player.role_data:
				del player.role_data['bg_protecting']
			return
		if target != None:
			if target not in game.protected_players:
				game.protected_players.append(target)
			name = target.name
			await player.send_msg(f'You chose to protect {name} tonight.')
			player.role_data['bg_protecting'] = target.id
			if target.role == Role.veteran and target.role_data['on_alert']:
				return player
		return
	if player.role == Role.investigator:
		target = get_vote(player)
		c = player.role_data['investigation_count']
		if target == None:
			if c != 0:
				await player.send_msg('You did not investigate anyone this night.')
			return
		player.role_data['investigation_count'] -= 1
		c = player.role_data['investigation_count']
		msg = f'{target.name} came up as a {get_role_name(target.role)}. You have {c} investigations remaining.'
		await player.send_msg(msg)
		if target.role == Role.veteran and target.role_data['on_alert']:
			log_msg(f'{player.name} investigated veteran on alert and died.')
			return player
		return
	if player.role == Role.medium:
		target = get_vote(player)
		c = player.role_data['investigation_count']
		if target == None:
			if c != 0:
				await player.send_msg('You did not investigate anyone this night.')
			return
		player.role_data['investigation_count'] -= 1
		c = player.role_data['investigation_count']
		msg = f'{target.name} came up as a {get_role_name(target.role)}. You have {c} investigations remaining.'
		await player.send_msg(msg)
		return
	if player.role == Role.vigilante:
		if 'die_next_turn' in player.role_data:
			if not game.players[player.role_data['die_next_turn']].is_alive:
				return player
			return
		else:
			vote = get_vote(player)
			if vote != None:
				player.role_data['bullets_remaining'] -= 1
				print(f'Vigilante {player.name} chose to kill {vote.name}.')
				await player.send_msg(f'You chose to kill {vote.name}.')
				protection = util.find_bodyguard_protection(game)
				if vote.id in protection:
					return [player, protection[vote.id]]
				if is_town(vote.role) and vote.role != Role.veteran:
					print(f'Vigilante {player.name} will die next turn.')
					player.role_data['die_next_turn'] = vote.id
					
				elif vote.role == Role.veteran and vote.role_data['on_alert']:
					print(f'Vigilante {player.name} visited veteran on alert and died.')
					return player
				return vote
			else:
				await player.send_msg(f'You chose to kill nobody.')
	
def get_vote(player):
	return generic.get_multi_vote(player)[0]
