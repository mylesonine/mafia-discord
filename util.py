import random
from roles import *

class Object(object):
	pass

# Convert rgb to discord color
def color_rgb(r, g, b):
	return r * 65536 + g * 256 + b
	
	
def at_name(id):
	return f'<@!{id}>'

def generate_translation_list(players, filter_f = None, use_numbers = False):
	available = players
	if filter_f != None:
		available = list(filter(filter_f, players))
	out = {}
	if use_numbers:
		count = 1
		for i in available:
			out[str(count)] = i
			count += 1
		out['0'] = None
	else:
		count = 0
		for i in available:
			out[chr(ord('A') + count)] = i
			count += 1
		out['Z'] = None
	return out
	
def generate_selection_list(tl_list):
	msg = ''
	for i in tl_list.items():
		if i[1] != None:
			msg += f'\n{i[0]}: {i[1].name}'
		else:
			msg += f'\n{i[0]}: Nobody'
	return msg
	
def unique_list(l):
	out = {}
	for i in l:
		out[i] = 0
		
	return list(out.keys())
	
	
def find_bodyguard_protection(game):
	''' Returns { protection target id : bodyguard }'''
	bgs = list(filter(lambda x : x.role == Role.bodyguard, game.players.values()))
	# If two bgs protect the same target, the last one iterated over will be killed on success
	protection = {}
	for i in bgs:
		if 'bg_protecting' in i.role_data:
			protection[i.role_data['bg_protecting']] = i
	return protection