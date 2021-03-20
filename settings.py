import util
command_prefix = '!'
bot_token = ''

help_message = '''help menu:
!help 
!setup - creates a party
!start - starts a game
!join - join a party in progress'''

town_color = util.color_rgb(0, 0, 180)
mafia_color = util.color_rgb(180, 0, 0)
third_color = util.color_rgb(0, 180, 0)

min_players = 5
max_players = 25

# Delay between day and night cycles in seconds
night_duration = 35
day_duration = 180

start_emoji = '🦆'