import util

def get_vote(player):
	for i in reversed(player.recent_msgs):
		if i.upper() in player.translation_list.keys():
			return player.translation_list[i.upper()]
	return None
	
def get_multi_vote(player):
	found_abc = None
	found_num = None
	for i in reversed(player.recent_msgs):
		s = i.upper()
		if s in player.translation_list.keys():
			if len(s) == 1 and s[0] >= 'A' and s[0] <= 'Z' and found_abc == None:
				found_abc = player.translation_list[s]
			elif found_num == None:
				try:
					num = int(s)
					if num >= 1 and num <= 99 and s in player.translation_list.keys():
						found_num = player.translation_list[s]
				except:
					pass
				
	return (found_abc, found_num)