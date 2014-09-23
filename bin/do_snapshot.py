#!/usr/bin/python
import os
import subprocess
import time
import sys
import datetime
import getopt


from BatPithon import BatPithon

# DEV_SNAPSHOT_ID = '2014-08-29-10-34-08'

# DEV_SNAPSHOT_ID = str(datetime.datetime.now())

ENV = {}
LOG = []
SNAPSHOT_ENV = {}
SNAPSHOT_DATA_DIR = '/home/pi/fromNis/Server/snapshots/'
SERVICE_ENV_DIR = '/home/suas/Services/command/env/'
DEBUG = True

log_file = None

def log(line):
	global log_file
	LOG.append(line)
	if DEBUG:
		print line

	if log_file == None:
		log_file = open(os.path.join(SNAPSHOT_DATA_DIR, 'LOG'), 'a')

	log_file.write(line + '\n')

def write_state(state):
	log('Changing state to "' + state + '"')
	with open(os.path.join(SNAPSHOT_DATA_DIR, 'ENV', 'SNAPSHOT_STATE'), 'w') as f:
		f.write(state)

def read_env(var_name, update = False):
	if update == False and var_name in ENV:
		return ENV[var_name]
	else:
		path = SERVICE_ENV_DIR + var_name
		if os.path.exists(path):
			with open(path, 'r') as f:
				contents = f.read()
			ENV[var_name] = contents.strip()
			return ENV[var_name]
		else:
			return None

def read_snapshot_env(var_name, update = False):
	if update == False and var_name in SNAPSHOT_ENV:
		return SNAPSHOT_ENV[var_name]
	else:
		path = SNAPSHOT_DATA_DIR + 'ENV/' + var_name
		if os.path.exists(path):
			with open(path, 'r') as f:
				contents = f.read()
			SNAPSHOT_ENV[var_name] = contents.strip()
			return SNAPSHOT_ENV[var_name]
		else:
			return None

def read_envs():
	results = []
	results.append(read_snapshot_env('SNAPSHOT_GAIN'))
	results.append(read_snapshot_env('SNAPSHOT_LENGTH'))
	results.append(read_snapshot_env('SNAPSHOT_NAME'))
	results.append(read_snapshot_env('SNAPSHOT_STATE'))
	results.append(read_snapshot_env('SNAPSHOT_ID'))
	if False in results:
		return False
	else:
		return True

def find_data_dir(name):
	result = None
	root = '/mnt/'
	if not os.path.exists(root):
		log('Could not find ' + root)
		sys.exit(2)
	else:
		items = os.listdir(root)
		for i in reversed(items): # Newest first
			cwd = os.path.join(root, i)
			if os.path.isdir(cwd):
				cwd_files = os.listdir(cwd)
				if 'metadata' in cwd_files and 'vars.sh' in cwd_files:
					with open(os.path.join(cwd, 'vars.sh'), 'r') as f:
						contents = f.read()
    					if 'MASTER_UUID="' + name + '"' in contents:
    						result = i
    						break
	return result

def main(argv):
	global SNAPSHOT_DATA_DIR
	global log_file
	help_line = 'do_snapshot.py -s <SNAPSHOT_ID>'
	sname = False
	try:
		opts, args = getopt.getopt(argv,"hs:",["snapshotid="])
	except getopt.GetoptError:
		print help_line
		sys.exit(2)

	for opt, arg in opts:
		if opt == '-h':
			print help_line
			sys.exit()
		elif opt in ("-s", "--snapshotid"):
			sname = arg

	if not sname:
		log('Snapshot id argument required and not given.')
		sys.exit(2)
	else:
		SNAPSHOT_ID = str(sname)
		SNAPSHOT_DATA_DIR = SNAPSHOT_DATA_DIR + SNAPSHOT_ID + '/'
		log('SNAPSHOT_DATA_DIR set to: ' + SNAPSHOT_DATA_DIR)


	write_state('Setting up recorder')

	log('Checking snapshot directory: ' + read_env('SNAPDIR'))
	if not os.path.exists('/mnt/samples'):
		log('Mounting external HD')
		return_code = subprocess.call('mount /dev/sda1 /mnt', shell=True)
		if return_code == 0 and os.path.exists('/mnt/samples'):
			log('Mounting successfull')
			log('Snapshot directory available')
		else:
			log('Mounting unsuccessfull')
			log('Snapshot directory not available')
			log('Exiting...')
			sys.exit(1)
	else:
		log('Snapshot directory available')
	
	log('Importing snapshot parameters')
	if read_envs() == False:
		log('Snapshot parameters could not be read')
		log('Exiting...')
		sys.exit(4)
	
	
	log('Starting service')
	return_code = subprocess.call('sv o /home/suas/Services/command', shell=True)
	time.sleep(1)
	count = 0
	running = False
	while running == False and count < 10:
		count += 1
		p = subprocess.Popen(['sv', 'status', '/home/suas/Services/command'], stdout=subprocess.PIPE)
		out, err = p.communicate()
		if out.strip().lower().startswith('run'):
			running = True
		else:
			time.sleep(1)
	
	if running == False:
		log('Service could not be started')
		log('Exiting...')
		sys.exit(2)
	else:
		log('Service started')
		log('Sleeping for initialisation')
		time.sleep(5)
	
	batpi = BatPithon.BatPithon('127.0.0.1', 2468)
	connected = False
	count = 0
	while connected == False and count < 20:
		count += 1
		batpi.connect()
		if batpi.status == 'Connected':
			connected = True
		else:
			log('Not connected. Retrying...')
			time.sleep(1)
	
	if connected == False:
		log('Could not connect to service')
		log('Exiting')
		sys.exit(3)
	
	log('Connected to service')
	
	log('Getting channels')
	channels = batpi.get_channels()
	for i in channels:
		log('Channel: ' + str(i['channel']) + ' Type: ' + str(i['type']) + ' Name: ' + str(i['name']) + ' Gain: ' + str(i['gain']))
	
	log('Setting gain on channels to: ' + str(int(read_snapshot_env('SNAPSHOT_GAIN'))))
	for i in channels:
		if batpi.set_gain(i['index'], int(read_snapshot_env('SNAPSHOT_GAIN'))) == False:
			log('Error when setting gain on channel: ' + str(i['channel']))
			print batpi.errors[-1]
	
	log('Sending run/run start commands')
	batpi.start()
	
	write_state('Recording')

	log('Starting snapshot')
	batpi.msnap(SNAPSHOT_ID, nfiles = 3250)
	return_code = subprocess.call('su suas -c "/home/suas/Scripts/rand-sync &"', shell=True)
	
	start = datetime.datetime.now()
	
	log('Waiting till snapshot finishes recording')
	while int((datetime.datetime.now() - start).seconds) < int(read_snapshot_env('SNAPSHOT_LENGTH')):
		time.sleep(1)
	
	log('Snapshot done')
	log('Quitting service')
	batpi.quit()

	time.sleep(2)

	log('Finding snapshot recording data dir')
	rec_dir = find_data_dir(SNAPSHOT_ID)
	if rec_dir == False:
		log('Could not find the recording dir: ' + SNAPSHOT_IDN)
		sys.exit(2)
	
	log('Found recording in: ' + rec_dir)
	log('Creating snapshot ENV variable for recording dir')
	with open(os.path.join(SNAPSHOT_DATA_DIR + 'ENV/' + 'SNAPSHOT_RECORDING'), 'w') as f:
		f.write(rec_dir)

	write_state('Recorded')

	write_state('Processing')

	time.sleep(2)

	rec_path = os.path.join('/mnt/', rec_dir)

	# Joining files
	cmd = 'cat ' + rec_path + '/' + rec_dir + '.* > ' + rec_path + '/' + rec_dir + '_full.raw'
	# print cmd
	subprocess.call(cmd, shell=True)
	cmd = 'rm ' + rec_path + '/' + rec_dir + '.*'
	# print cmd
	subprocess.call(cmd, shell=True)

	# Converting to FLAC
	cmd = 'sox -r 100000 -c 8 -b 16 -e signed-integer ' + rec_path + '/' + rec_dir + '_full.raw ' + rec_path + '/' + rec_dir + '_full.flac'
	# print cmd
	subprocess.call(cmd, shell=True)

	cmd = 'sox ' + rec_path + '/' + rec_dir + '_full.flac -n remix 1 spectrogram -o ' + rec_path + '/' + rec_dir + '_spectrogram.png'
	subprocess.call(cmd, shell=True)

	write_state('Processed')

	log('All done')

	if log_file != None:
		log('Closing log file')
		log_file.close()

	
	





if __name__ == "__main__":
	# print find_data_dir()
	main(sys.argv[1:])
