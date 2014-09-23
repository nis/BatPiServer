#!/usr/bin/python
from flask import Flask, render_template, request, redirect, url_for, flash, make_response
import datetime
import os
import shutil
import subprocess

app = Flask(__name__)
app.secret_key = 'rsgpj7rstdhst5dnh4s'

config = {
	'server_root_path': '/home/pi/fromNis/Server',
	'snapshot_data_dir': 'snapshots',
	'recordings_dir': '/mnt'
}

@app.route('/sapi/status')
def sapi_status():
	p = subprocess.Popen(['sv', 'status', '/home/suas/Services/command'], stdout=subprocess.PIPE)
	out, err = p.communicate()

	status = None
	if out.strip().lower().startswith('run'):
		status = 'Running'
	elif out.strip().lower().startswith('down'):
		status = 'Down'
	else:
		status = 'Unknown: ' + out.strip()
	return status

@app.route('/sapi/start')
def sapi_start():
	return_code = subprocess.call('sv o /home/suas/Services/command', shell=True)
	return 'Start command sent to service.'

@app.route('/sapi/stop')
def sapi_stop():
	return_code = subprocess.call('sv d /home/suas/Services/command', shell=True)
	return 'Stop command sent to service.'

@app.route('/sapi/quit')
def sapi_quit():
	import socket
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	s.sendto('quit', ('127.0.0.1', 2468))
	return 'Quit command sent to service.'

@app.route("/")
def hello():
	return "Hello World!"
	# now = datetime.datetime.now()
	# timeString = now.strftime("%Y-%m-%d %H:%M")
	# templateData = {
	#    'title' : 'HELLO!',
	#    'time': timeString
	#    }
	# return render_template('snapshot_form.html', **templateData)

def get_snapshot_list():
	snapshots_path = os.path.join(config['server_root_path'], config['snapshot_data_dir'])
	snapshots = []
	items = os.listdir(snapshots_path)
	for i in items: # Newest first
		snapshot = {}
		snapshot['path'] = os.path.join(snapshots_path, i)
		if os.path.isdir(snapshot['path']):
			snapshot_files = os.listdir(snapshot['path'])
			if 'LOG' in snapshot_files and 'ENV' in snapshot_files:
				snapshot['env_path'] = os.path.join(snapshot['path'], 'ENV')
				env_files = os.listdir(snapshot['env_path'])
				if 'SNAPSHOT_STATE' in env_files and 'SNAPSHOT_NAME' in env_files and 'SNAPSHOT_LENGTH' in env_files and 'SNAPSHOT_ID' in env_files and 'SNAPSHOT_GAIN' in env_files:
					with open(os.path.join(snapshot['env_path'], 'SNAPSHOT_STATE'), 'r') as f:
						snapshot['SNAPSHOT_STATE'] = f.read().strip()

					with open(os.path.join(snapshot['env_path'], 'SNAPSHOT_NAME'), 'r') as f:
						snapshot['SNAPSHOT_NAME'] = f.read().strip()

					with open(os.path.join(snapshot['env_path'], 'SNAPSHOT_LENGTH'), 'r') as f:
						snapshot['SNAPSHOT_LENGTH'] = f.read().strip()

					with open(os.path.join(snapshot['env_path'], 'SNAPSHOT_ID'), 'r') as f:
						snapshot['SNAPSHOT_ID'] = f.read().strip()

					with open(os.path.join(snapshot['env_path'], 'SNAPSHOT_GAIN'), 'r') as f:
						snapshot['SNAPSHOT_GAIN'] = f.read().strip()

				if 'SNAPSHOT_RECORDING' in env_files:
					with open(os.path.join(snapshot['env_path'], 'SNAPSHOT_RECORDING'), 'r') as f:
						snapshot['SNAPSHOT_RECORDING'] = f.read().strip()

 				snapshots.append(snapshot)
 	return sorted(snapshots, key=lambda k: k['SNAPSHOT_ID'], reverse = True)

def get_snapshot_dict(snapshots = False):
	if snapshots == False:
		snapshots = get_snapshot_list()

	results = {}
	for s in snapshots:
		results[s['SNAPSHOT_ID']] = s
	return results

def get_snapshot(sid):
	snapshots = get_snapshot_dict()
	if sid in snapshots:
		return snapshots[sid]
	else:
		return None

@app.route('/see/<sid>')
def see(sid):
	with open(os.path.join('/mnt', sid, sid + '_spectrogram.png'), 'r') as f:
		data = f.read()

	response = make_response(data)
	response.headers["Content-Disposition"] = "inline; filename=" + sid + '_spectrogram.png'
	response.headers["Content-Type"] = 'image/png'
	return response

@app.route('/delete/<sid>')
def delete(sid):
	snapshot = get_snapshot(sid)

	if snapshot == None:
		flash('Snapshot with ID "' + sid + '" could not be found.', 'danger')
		return redirect(url_for('snapshots'))
 
	shutil.rmtree(os.path.join(config['server_root_path'], config['snapshot_data_dir'], snapshot['SNAPSHOT_ID']))

	if 'SNAPSHOT_RECORDING' in snapshot:
		shutil.rmtree(os.path.join(config['recordings_dir'], snapshot['SNAPSHOT_RECORDING']))


	flash('Snapshot "' + snapshot['SNAPSHOT_NAME'] + ' (' + snapshot['SNAPSHOT_ID'] + ')" was deleted.', 'success')
	return redirect(url_for('snapshots'))

@app.route('/snapshots/')
def snapshots():
	templateData = {
		'title' : 'Snapshots'
		}
	
 	templateData['snapshots'] = get_snapshot_list()
	return render_template('snapshots_list.html', **templateData)
	
@app.route('/new_snapshot/', methods=['GET', 'POST'])
def new_snapshot():
	import os
	now = datetime.datetime.now()
	timeString = now.strftime("%Y-%m-%d-%H-%M-%S")
	templateData = {
		'title' : 'New snapshot',
		'time': timeString
		}
	if request.method == 'POST':
		snapshot_name = request.form['snapshot_name']
		snapshot_length = request.form['length_seconds']
		snapshot_gain = request.form['gain']
		strings = 'str '
		
		# snapshot_path = config['server_root_path'] + config['snapshot_data_dir'] + timeString + '/'
		snapshot_path = os.path.join(config['server_root_path'], config['snapshot_data_dir'], timeString)
		if not os.path.exists(snapshot_path):
			os.makedirs(snapshot_path)

		# env_path = snapshot_path + 'ENV'
		env_path = os.path.join(snapshot_path, 'ENV')
		if not os.path.exists(env_path):
			os.makedirs(env_path)

		with open(os.path.join(env_path, 'SNAPSHOT_NAME'), 'w') as f:
			f.write(snapshot_name)

		with open(os.path.join(env_path, 'SNAPSHOT_ID'), 'w') as f:
			f.write(timeString)

		with open(os.path.join(env_path, 'SNAPSHOT_LENGTH'), 'w') as f:
			f.write(snapshot_length)

		with open(os.path.join(env_path, 'SNAPSHOT_GAIN'), 'w') as f:
			f.write(snapshot_gain)

		with open(os.path.join(env_path, 'SNAPSHOT_STATE'), 'w') as f:
			f.write('Parameters saved')

		with open(os.path.join(snapshot_path, 'LOG'), 'a') as f:
			f.write(now.strftime("%Y-%m-%d %H:%M:%S") + ' ' + 'Parameters saved')
		# return 
		# return "Hello World!" + snapshot_name + ' ' + snapshot_length + ' ' + snapshot_gain

		# Call processing script
		# ./do_snapshot.py -s "2014-09-09-11-00-56"
		processor_script_path = os.path.join(config['server_root_path'], 'bin/do_snapshot.py')
		return_code = subprocess.call(processor_script_path + ' -s "' + str(timeString) + '" &', shell=True)

		flash('Snapshot "' + snapshot_name + '" was initialized.', 'success')

		return redirect(url_for('snapshots'))
	else:
		return render_template('snapshot_form.html', **templateData)

# Static files

@app.route('/js/jquery.min.js')
def jquery_file():
	return redirect(url_for('static', filename = 'js/jquery.min.js'))

@app.route('/js/bootstrap.min.js')
def bootstrap_js_file():
	return redirect(url_for('static', filename = 'js/bootstrap.min.js'))

@app.route('/css/bootstrap.min.css')
def bootstrap_css_file():
	return redirect(url_for('static', filename = 'css/bootstrap.min.css'))

if __name__ == "__main__":
	app.run(host='', port=80, debug=True)