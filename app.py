from flask import Flask, render_template, send_file, request, Response
import os
import subprocess
import multiprocessing
import signal

app = Flask(__name__)
video_dir = "/home/pi/PiBikeCam/videos"  # Directory where your recorded videos are stored
recording_running = False
recording_process = None

def start_recording():
	recording_process = subprocess.Popen(["python3", "/home/pi/PiBikeCam/cam.py"])
	
def signal_handler(sig, frame):
	print("shutting down server")
	global recording_running
	global recording_process
	if recording_running:
	    recording_process.send_signal(signal.SIGINT)
	    recording_running = False
	sys.exit(0)

@app.route('/start_recording')
def start_recording_route():
	global recording_running
	global recording_process
	if not recording_running:
		recording_running = True
		recording_process = multiprocessing.Process(target=start_recording)
		recording_process.start()
		return "Recording started"
	else:
		recording_process.send_signal(signal.SIGINT)
		recording_running = False
		return "stopped recording"

@app.route('/')
def index():
    video_files = [file for file in os.listdir(video_dir) if file.endswith('.mp4')]
    return render_template('index.html', video_files=video_files)

@app.route('/video/<path:video_name>')
def serve_video(video_name):
    video_path = os.path.join(video_dir, video_name)
    return send_file(video_path, mimetype='video/mp4')

@app.route('/stream/<path:video_name>')
def stream_video(video_name):
    def generate():
        video_path = os.path.join(video_dir, video_name)
        with open(video_path, 'rb') as video_file:
            while True:
                data = video_file.read(1024)
                if not data:
                    break
                yield data

    return Response(generate(), mimetype='video/mp4')

if __name__ == '__main__':
    start_recording_route()
    signal.signal(signal.SIGINT, signal_handler)
    app.run(host='0.0.0.0', port=8080)
