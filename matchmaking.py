from roles import *
import mafia
import town
import third_party
import random

# { role : % chance}
def random_by_probability(probs):
	assert(len(probs) != 0)
	pc = probs.copy()
	v = random.randrange(0, 1000) / 10.0
	total = sum(pc.values())
	# normalize to 100%
	adjust = total / 100.0
	for i in pc:
		pc[i] = pc[i] * adjust
	for i in pc:
		if v <= pc[i] + 0.01:
			return i
		v -= pc[i]
	assert(False)
	
def filter_once(list, target):
	for i in range(len(list)):
		if list[i] == target:
			return list[0:i+1] + list(filter(lambda x: x != target, target[i+1:]))
	return list

def gen_game_comp(game):	
	required_roles = game.server.settings['required_roles']
	banned_roles = game.server.settings['banned_roles']
	
	town_roles = [ Role.bodyguard, Role.survivor, Role.deputy, Role.sheriff, Role.doctor, Role.investigator, Role.mayor, Role.medium, Role.politician, Role.sheriff, Role.veteran, Role.vigilante, Role.basic_town ]
	town_probability = { Role.bodyguard : 10, Role.survivor : 5, Role.deputy : 10, Role.sheriff : 20,
		Role.doctor : 10, Role.investigator : 20, Role.mayor : 10, Role.medium : 10, Role.politician : 15,
		Role.vigilante : 10, Role.basic_town : 15 }
	
	mafia_roles = [ Role.blackmailer, Role.consigliere, Role.janitor, Role.mafioso ]
	mafia_probability = { Role.blackmailer : 20, Role.consigliere : 25, Role.janitor : 35, Role.mafioso : 20 }
	
	third_party = [ Role.executioner, Role.jester, Role.serial_killer, Role.witch, Role.werewolf ]
	third_party_probability = { Role.executioner : 25, Role.serial_killer : 8, Role.werewolf : 5, 
		Role.witch : 12, Role.jester : 40 }
	
	unique_roles = [ Role.godfather, Role.serial_killer, Role.witch, Role.werewolf, Role.vigilante ]

	n_mafia = len(game.players) // random.randrange(5,8) + 1
	n_third_party = len(game.players) // random.randrange(5, 12)
	if 'no_third_party' in game.options:
		n_third_party = 0
	n_town = len(game.players) - n_mafia - n_third_party
	
	print(f'{n_town} town, {n_mafia} mafia, {n_third_party} third party')
	
	game_comp = required_roles.copy()
	while len(game_comp) < len(game.players):
		while len(list(filter(lambda x: is_mafia(x), game_comp))) < n_mafia:
			game_comp.append(random_by_probability(mafia_probability))
		while len(list(filter(lambda x: is_third_party(x), game_comp))) < n_third_party:
			game_comp.append(random_by_probability(third_party_probability))
		while len(list(filter(lambda x: is_town(x), game_comp))) < n_town:
			game_comp.append(random_by_probability(town_probability))
		for i in unique_roles:
			#filter_once(game_comp, i)
			pass
		# Filter banned roles
		game_comp = list(filter(lambda x : x not in banned_roles, game_comp))
		# Don't enable medium in games without role reveal and no janitor
		n_janitors = len(list(filter(lambda x: x == Role.janitor, game_comp)))
		if n_janitors and 'enable_role_reveal' in game.settings and not game.settings['enable_role_reveal']:
			game_comp = list(filter(lambda x: x != Role.medium, game_comp))
	
	print(f'Game comp = {game_comp}')
	#random.shuffle(game_comp)
	p = random.shuffle(list(range(len(game.players))))
	for x in p:
		game.players[x].role = game_comp[0]
		game_comp = game_comp[1:]