def log_msg(msg):
	print(msg)
	with open('log.txt', 'a') as f:
		f.write(msg + '\r\n')