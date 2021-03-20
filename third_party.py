from roles import *
import util
import generic
import random
from log import *

vote_addendum = ' Only the final vote will count.'

async def play_night(game, player):
	player.translation_list = {}
	player.recent_msgs = [] # Reset recent messages so we don't re-vote accidentally
	if not player.is_alive:
		return
	if player.role == Role.serial_killer:
		tl = util.generate_translation_list(game.players.values(), filter_f = lambda x: x.id != player.id and x.is_alive)
		if len(tl) > 1:
			player.translation_list = tl
			msg = f'Who would you like to kill? You have {game.settings["night_duration"]} seconds to respond.'
			msg += util.generate_selection_list(tl)
			msg += '\n\nRespond with the letter corresponding to the person you wish to kill.' + vote_addendum
			await player.send_msg(msg)
		return
	if player.role == Role.witch:
		for i in game.players.values():
			if 'is_cursed' not in i.role_data:
				i.role_data['is_cursed'] = {}
		f = lambda x: x.id != player.id and player.id not in x.role_data['is_cursed'] and x.is_alive
		tl = util.generate_translation_list(game.players.values(), filter_f = f)
		if len(tl) > 1:
			player.translation_list = tl
			msg = f'Who would you like to curse? You have {game.settings["night_duration"]} seconds to respond.'
			msg += util.generate_selection_list(tl)
			msg += '\n\nRespond with the letter corresponding to the person you wish to curse.' + vote_addendum
			await player.send_msg(msg)
		return
	if player.role == Role.werewolf:
		if game.turn_number % 2 == 1:
			# night turn
			tl = util.generate_translation_list(game.players.values(), lambda x: x.is_alive and x.id != player.id)
			if len(tl) > 1:
				player.translation_list = tl
				msg = f'Who would you like to kill? You have {game.settings["night_duration"]} seconds to respond.'
				msg += util.generate_selection_list(tl)
				msg += '\n\nRespond up to two times with the letter corresponding to the player you wish to kill.'
				await player.send_msg(msg)
		else:
			# day turn
			await player.send_msg('Tonight you are a basic town')
		return
	if player.role == Role.executioner:
		if 'marked_player' not in player.role_data:
			tl = util.generate_translation_list(game.players.values(), lambda x: x.id != player.id)
			if len(tl) > 1:
				player.translation_list = tl
				msg = f'Who would you like to mark for death? You have {game.settings["night_duration"]} seconds to respond.'
				msg += util.generate_selection_list(tl)
				msg += '\n\nRespond up to two times with the letter corresponding to the player you wish to mark.'
				await player.send_msg(msg)
				player.role_data['marked_player'] = 0
			player.role_data['is_jester'] = False
		
async def play_night_end(game, player):
	if not player.is_alive:
		return
	if player.role == Role.serial_killer:
		vote = get_vote(player)
		
		if vote != None:
			protection = util.find_bodyguard_protection(game)
			if vote.id in protection:
				log_msg(f'Serial killer {player.name} targeted protected player {vote.name}.')
				return [player, protection[vote.id]]
			await player.send_msg(f'You chose to kill {vote.name}.')
			if vote.role == Role.veteran and vote.role_data['on_alert']:
				log_msg(f'Serial killer {player.name} targeted veteran on alert {vote.name}.')
				return player
			log_msg(f'Serial killer {player.name} targeted {vote.name}.')
		return vote
	if player.role == Role.witch:
		vote = get_vote(player)
		if vote != None:
			await player.send_msg(f'You chose to curse {vote.name}.')
			log_msg(f'Witch {player.name} cursed {vote.name}.')
			if vote.role == Role.veteran and vote.role_data['on_alert']:
				log_msg(f'Witch {player.name} targeted veteran on alert {vote.name}.')
				return player
			vote.role_data['is_cursed'].append(player.id)
		return
	if player.role == Role.werewolf:
		if game.turn_number % 2 == 1:
			# find last 2 votes
			votes = []
			for i in reversed(player.recent_msgs):
				if i.upper() in player.translation_list.keys():
					votes.append(player.translation_list[i.upper()])
					if len(votes) == 2:
						break
			votes = list(filter(lambda x: x != None and x != 0, votes))
			names = 'Nobody'
			if len(votes):
				names = ' and '.join(map(lambda x: x.name, votes))
			await player.send_msg(f'You chose to kill {names} tonight.')
			
			protection = util.find_bodyguard_protection(game)
			# find veterans on alert
			for x in range(len(votes)):
				log_msg(f'Werewolf {player.name} targeted {votes[x].name}.')
				target = votes[x]
				if target.id in protection:
					log_msg(f'Werewolf {player.name} targeted guarded {votes[x].name} and will die.')
					# attach bodyguard and werewolf
					votes.append(protection[target.id])
					votes.append(player)
				if target.role == Role.veteran and target.role_data['on_alert']:
					log_msg(f'Werewolf {player.name} targeted veteran {votes[x].name} and will die.')
					votes[x] = player
			return list(set(votes))
		return
	if player.role == Role.executioner:
		if 'marked_player' in player.role_data:
			return
		vote = get_vote(player)
		random_roll = False
		if vote == None:
			targets = list(filter(lambda x: x.id != player.id, game.players.values()))
			random.shuffle(targets)
			if len(targets) > 0:
				vote = targets[0]
				random_roll = True
		if vote != None:
			if not random_roll:
				await player.send_msg(f'You chose to mark {vote.name}.')
			else:
				await player.send_msg(f'You did not vote and have marked {vote.name} by random.')
			#if vote.role == Role.veteran and vote.role_data['on_alert']:
			#	log_msg(f'Executioner {player.name} marked {vote.name} (veteran) on alert and will die.')
			#	return player
			log_msg(f'Executioner {player.name} marked {vote.name}.')
			player.role_data['marked_player'] = vote.id
		return
		
def get_vote(player):
	return generic.get_multi_vote(player)[0]