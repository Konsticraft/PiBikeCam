from flask import Flask, render_template, send_file, request, Response, url_for, send_from_directory
import os
import subprocess
import multiprocessing
import signal
import datetime

app = Flask(__name__)
# Directory where your recorded videos are stored
video_dir = os.path.abspath("PiBikeCam/videos")
thumb_dir = os.path.abspath("PiBikeCam/thumbs")
recording_running = False
recording_process = None


def start_recording():
	recording_process = subprocess.Popen(
	    ["python3", os.path.abspath("PiBikeCam/cam.py")])


def get_videos():
    videos = []
    for file in os.listdir(video_dir):
        filename = file
        time = datetime.datetime.strptime(file, "video_%Y-%m-%d_%H_%M_%S.mp4")
        timestr = datetime.datetime.strftime(time, "%d.%m.%Y %H:%M")
        #thumb = os.path.join(thumb_dir,file.replace("mp4", "png")).replace("\\","/")
        thumb = file.replace("mp4", "png")
        videos.append({
              "filename" : file,
              "timestamp" : time,
              "timestr" : timestr,
              "thumb_path" : thumb
		})
    return videos


def signal_handler(sig, frame):
	print("shutting down server")
	global recording_running
	global recording_process
	if recording_running:
		recording_process.send_signal(signal.SIGINT)
		recording_running = False
	exit()


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


@app.route('/home')
@app.route('/')
def index():
    # video_files = [file for file in os.listdir(
    #     video_dir) if file.endswith('.mp4')]
    video_list = get_videos()
    return render_template('home.html', video_list=video_list)


@app.route('/video/<path:video_name>')
def serve_video(video_name):
    video_path = os.path.join(video_dir, video_name)
    return send_file(video_path, mimetype='video/mp4')

@app.route('/thumbs/<path:thumb_name>')
def serve_thumb(thumb_name):
    return send_from_directory("thumbs", thumb_name)

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
    # start_recording_route()
    get_videos()
    signal.signal(signal.SIGINT, signal_handler)
    app.run(host='0.0.0.0', port=8080, debug=True)
    
