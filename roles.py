class Role:
	default_unknown = 0
	# town
	bodyguard = 1
	deputy = 2
	doctor = 3
	investigator = 4
	mayor = 5
	medium = 11
	politician = 6
	sheriff = 7
	survivor = 12
	veteran = 8
	vigilante = 9
	basic_town = 10
	
	#mafia
	blackmailer = 100
	consigliere = 101
	godfather = 102
	janitor = 103
	mafioso = 104
	
	# third party
	executioner = 200
	jester = 201
	serial_killer = 202
	witch = 203
	werewolf = 204

class Role_desc:
	description = ''
	embed = ''
	name = ''
	def __init__(self, name_str = '', description = '', embed = ''):
		self.name = name_str
		self.description = description
		self.embed = embed

role_defs = [ [Role.bodyguard, 'Bodyguard', 'You choose someone to protect at night. You will protect your target from one physical attack, taking the attacker down with you, you die as well on successful guard', 'embed_file' ],
	[Role.deputy, 'Deputy', 'You gain the powers of the Sheriff when a Sheriff dies. Allowing you to investigate people', 'embed_file' ],
	[Role.doctor, 'Doctor', 'You Heal one person each night. Your job is to save people. You may only heal yourself once per game', 'embed_file' ],
	[Role.investigator, 'Investigator', 'Each night you may choose a player to investigate, revealing their exact role. You can only do this twice a game.', 'embed_file' ],
	[Role.mayor, 'Mayor', 'You may reveal yourself as the mayor at any time. Once reveal your vote counts as two or mote vote but the doctor can not heal you.', 'embed_file' ],
	[Role.medium, 'Medium','Can reveal a role of someone who has died in a no role reveal game or reveal the role of someone who was cleaned by the janitor', 'embed_file' ],
	[Role.politician, 'Politician', 'You are a part of the town but when the sheriff investigates you it will come up as bad.', 'embed_file' ],
	[Role.sheriff, 'Sheriff', 'Each night you can check one player you will know if they come up as good or bad. (Godfather comes up as good and politician comes up as bad)', 'embed_file' ],
	[Role.survivor, 'Survivor', 'You can not be killed at night but have no other powers.', 'embed_file' ],
	[Role.veteran, 'Veteran', 'Each night you may choose to go on alert. While on alert you can not be killed and you will kill ANYONE who visits you that night.', 'embed_file' ],
	[Role.vigilante, 'Vigilante', 'You are the only town with night killing powers. Each night you may choose a player to shoot, killing them. If you kill a someone who is apart of the town you will kill your self next night', 'embed_file' ],
	[Role.basic_town, 'Basic Town', 'You are a basic town, You have no abilities and are a part of the town.', 'embed_file' ],
	# mafia
	[Role.blackmailer, 'Blackmailer', 'Each night you may choose a player to blackmail and they cannot speak the following day.', 'embed_file' ],
	[Role.consigliere, 'Consigliere', 'Each night you may choose a player to investigate, revealing their exact role. You can do this two times per game.', 'embed_file' ],
	[Role.godfather, 'Godfather', 'You are a mafia member but when the sheriff visits you, you come up as good.', 'embed_file' ],
	[Role.janitor, 'Janitor', 'If you are alive the first two mafia kills will not reveal role.', 'embed_file' ],
	[Role.mafioso, 'Mafioso', 'You have no abilities besides helping vote on who to kill.', 'embed_file' ],
	# third party
	[Role.executioner, 'Executioner', 'On the first night choose the target you want to be hanged. You win if the target you chose is hanged. If your target is killed from a shooting you become a jester.', 'embed_file' ],
	[Role.jester, 'Jester', 'You win if you are hanged', 'embed_file' ],
	[Role.serial_killer, 'Serial Killer', ' Each night you may choose to kill one person. You cannot be killed at night', 'embed_file' ],
	[Role.witch, 'Witch', 'Every person who is alive is cursed the witch wins the game.', 'embed_file' ],
	[Role.werewolf, 'Werewolf', 'They kill two targets every time they become a werewolf. During Odd nights they come up as good even nights they come up as bad.', 'embed_file' ],
	
]

role_defs_anime = [ [ Role.basic_town, 'Protagonist' ]
	]

_r = {}
for i in role_defs:
	_r[i[0]] = Role_desc(i[1], i[2], i[3])
	
def get_role_name(role_id):
	if role_id in _r:
		return _r[role_id].name
	return ''

def get_role_description(role_id):
	if role_id in _r:
		return _r[role_id].description
	return None

def get_role_embed(role_id):
	if role_id in _r:
		# todo: remove conditional and just return
		e = _r[role_id].embed
		if e == 'embed_file':
			e = ''
		return e
	return None
	
def is_mafia(role_id):
	return role_id >= 100 and role_id < 200
	
def is_town(role_id):
	return role_id < 100
	
def is_third_party(role_id):
	return role_id >= 200