from roles import *
import util
import generic

vote_addendum = ' Only the final vote will count.'

async def play_night(game, player):
	if not player.is_alive:
		return
	player.translation_list = {}
	player.recent_msgs = [] # Reset recent messages so we don't re-vote accidentally
	if player.role == Role.blackmailer:
		player.role_data['blackmail_target'] = None
		banned_targets = []
		if 'previous_blackmail_target' in player.role_data:
			banned_targets.append(player.role_data['previous_blackmail_target'])
			player.role_data['previous_blackmail_target'] = 0
		tl = util.generate_translation_list(game.players.values(), use_numbers = True, filter_f = lambda x: x.is_alive and x.id not in banned_targets)
		if len(tl) > 1:
			player.translation_list = tl
			msg = f'Who would you like to blackmail? You have {game.settings["night_duration"]} seconds to respond.'
			msg += util.generate_selection_list(tl)
			msg += '\n\nRespond with the letter corresponding to the person you wish to blackmail.' + vote_addendum
			await player.send_msg(msg)
	if player.role == Role.consigliere:
		if 'investigation_count' not in player.role_data:
			player.role_data['investigation_count'] = 1 + len(game.players) // 6
		# 0-5 = 1, 6-11 = 2, 12-17 = 3
		if player.role_data['investigation_count'] > 0:
			tl = util.generate_translation_list(game.players.values(), filter_f = lambda x: x.id != player.id and x.is_alive, use_numbers = True)
			if len(tl) > 1:
				player.translation_list = tl
				msg = 'Who would you like to investigate tonight?'
				msg += util.generate_selection_list(tl)
				msg += '\n\nRespond with the number corresponding to the person you wish to investigate.\n' + vote_addendum
				await player.send_msg(msg)
			
		
	# Other mafia members:
	
	if is_voting_role(player):
		# Mafia may vote to kill anyone including themselves
		tl = util.generate_translation_list(game.players.values(), filter_f = lambda x: x.is_alive)
		if len(tl) <= 1:
			return
		for i in tl:
			player.translation_list[i] = tl[i]
		msg = f'Who would you like to kill? You have {game.settings["night_duration"]} seconds to respond.'
		msg += util.generate_selection_list(tl)
		msg += '\n\nRespond with the letter corresponding to the person you wish to kill.' + vote_addendum
		player.recent_msgs = [] # Reset recent messages so we don't re-vote accidentally
		await player.send_msg(msg)
		return
	await player.send_msg('Your role is not implemented')
	
	
async def play_night_end(game, player):
	if not player.is_alive:
		return
	if player.role == Role.blackmailer:
		vote = get_votes(player)[1]
		player.role_data['blackmail_target'] = vote
		
		if vote != None:
			player.role_data['previous_blackmail_target'] = vote.id
			await player.send_msg(f'You chose to blackmail {vote.name}.')
			if vote.role == Role.veteran and vote.role_data['on_alert']:
				return player
		return
	if player.role == Role.consigliere:
		target = get_votes(player)[1]
		c = player.role_data['investigation_count']
		if target == None:
			if c > 0:
				await player.send_msg('You did not investigate anyone this night.')
			return
		player.role_data['investigation_count'] -= 1
		c = player.role_data['investigation_count']
		msg = f'{target.name} came up as a {get_role_name(target.role)}. You have {c} investigations remaining.'
		await player.send_msg(msg)
		return
	
def get_votes(player):
	return generic.get_multi_vote(player)
	
def get_vote(player):
	return generic.get_multi_vote(player)[0]

# all mafia vote
def is_voting_role(player):
	#return player.role in [ Role.godfather, Role.mafioso ]
	return is_mafia(player.role)