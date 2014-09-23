class BatPithon():
	"""Communicates with a BatPi"""
	def __init__(self, server_ip, server_port):
		self.server_ip = server_ip
		self.server_port = server_port
		self.status = 'Not connected'
		self.ready = True
		self.errors = []
		self.channels = None
		
		# self.connect()
		
		# if self.status != 'Connected':
		# 	return None

	def  quit(self):
		msg = 'quit'
		reply = self.send_message(msg)
	
	def msnap(self, name, nfiles = 3250):
		msg = 'msnap #0 #0x100000 ' + str(int(nfiles)) + ' ' + str(name)
		reply = self.send_message(msg)


	def start(self):
		msg = 'start'
		reply = self.send_message(msg)

		msg = 'start run'
		reply = '/t>', self.send_message(msg)

	def set_gain(self, channel, gain):
		msg = 'gain ' + str(channel) + ' ' + str(int(gain))
		# print msg
		reply = self.send_message(msg)
		if reply.strip() == 'Gain set to ' + hex(int(gain)) + ' on channel ' + str(channel):
			return True
		else:
			self.errors.append('Gain not set. Message: "' + reply.strip() + '"')
			return False
	
	def get_channels(self):
		if self.channels == None:
			self.retrieve_channels_info()
			
		return self.channels
	
	def retrieve_channels_info(self):
		scan = self.send_message('scan', '1-wire rescan completed')
		if scan:
			reply = self.send_message('chan')
			if reply.strip().startswith('begin channel list') and reply.strip().endswith('end channel list'):
				self.channels = []
				l = reply.strip().split('begin channel list')[1].strip().split('end channel list')[0].strip().split('\n')
				for i in l:
					c = i.split(':')
					if len(c) == 6:
						channel = {}
						channel['channel'] = int(c[1])
						channel['index'] = int(c[2]) + 1
						channel['gain'] = float(c[3])
						channel['type'] = str(c[4])
						channel['name'] = str(c[5])
						self.channels.append(channel)
			else:
				self.errors.append('Strange reply: ' + reply)
				return False
		else:
			self.errors.append('Strange reply from scan: ' + reply)
			return False
	
	def control_led(self, color, state):
		color = color.lower()
		on_states = ['on', True, 1]
		off_states = ['off', False, 0]
		if self.status == 'Connected':
			if color in ['green', 'red', 'yellow']:
				if state in on_states:
					if self.send_message('led ' + color + ' ' + 'on', '\'' + color + '\' is now \'on\''):
						return True
					else:
						self.errors.append('Strange reply: ' + reply)
						return False
				elif state in off_states:
					if self.send_message('led ' + color + ' ' + 'off', '\'' + color + '\' is now \'off\''):
						return True
					else:
						self.errors.append('Strange reply: ' + reply)
						return False
				else:
					self.errors.append('State parameter not understood: ' + str(state))
					return False
			else:
				self.errors.append('Color parameter not understood: ' + color)
				return False
			
		else:
			self.errors.append('Not connected')
			return False
			
	def send_message(self, message, good_reply = False):
		self.s.sendto(message, (self.server_ip, self.server_port))
		d = self.s.recvfrom(1024)
		reply = d[0]
		addr = d[1]
		
		if good_reply != False:
			return reply.strip() == good_reply
		else:
			return reply
	
	def connect(self):
		import socket
		if self.status == 'Not connected':
			try:
				self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
				self.s.settimeout(2)
			except socket.error:
				self.errors.append('Failed to create socket')
			except socket.timeout:
				self.errors.append('Failed to create socket: Timeout')
			else:
				self.status = 'Socket created'
		
		if self.status == 'Socket created':
			try:
				self.s.sendto('ping', (self.server_ip, self.server_port))
				d = self.s.recvfrom(1024)
				reply = d[0]
				addr = d[1]
			except socket.error, msg:
				self.errors.append('Error Code: ' + str(msg))
				self.status = 'Not connected'
			else:
				if reply.strip() == 'pong':
					self.status = 'Connected'
				else:
					self.status = 'Not connected'
					self.errors.append('Strange reply: ' + reply)
					
		return self.status == 'Connected'