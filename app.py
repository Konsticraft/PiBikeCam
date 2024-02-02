from flask import Flask, render_template, send_file, request, Response, url_for, send_from_directory, redirect
import os
import subprocess
import multiprocessing
import signal
import datetime
import configparser
import battery #only works on PI

app = Flask(__name__)
# Directory where your recorded videos are stored
video_dir = os.path.abspath("PiBikeCam/videos")
thumb_dir = os.path.abspath("PiBikeCam/thumbs")
config_path = os.path.abspath("PiBikeCam/config.ini")
recording_running = False
recording_process = None
config = {}
parser = None


def set_config():
    global config
    global parser
    global config_path
    parser = configparser.ConfigParser()
    parser.read(config_path)
    config = parser["DEFAULT"]





@app.route('/settings')
def settings_route():
    auto_rec = config["recording_autostart"]
    port = config["port"]
    seg_len = config["segment_length"]
    return render_template('settings.html', auto_rec=auto_rec, port=port, seg_len=seg_len)


@app.route('/update_settings', methods=['POST'])
def update_settings():
    rec_auto = "True" if request.form.get('Autostart') else "False"
    seg_len = request.form.get('seg_len')
    port = request.form.get('port')
    global config
    config = {
        "recording_autostart": rec_auto,
        "segment_length": seg_len,
        "port": port
    }
    global parser
    parser["DEFAULT"] = config
    with open(config_path, 'w') as configfile:
        parser.write(configfile)

    return redirect(url_for('settings_route'))


def start_recording():
    global recording_process
    recording_process = subprocess.Popen(
        ["python3", os.path.abspath("PiBikeCam/cam.py")])


def get_videos():
    videos = []
    for file in os.listdir(video_dir):
        filename = file
        time = datetime.datetime.strptime(file, "video_%Y-%m-%d_%H_%M_%S.mp4")
        timestr = datetime.datetime.strftime(time, "%d.%m.%Y %H:%M")
        date = datetime.datetime.strftime(time, "%Y-%m-%d")
        # thumb = os.path.join(thumb_dir,file.replace("mp4", "png")).replace("\\","/")
        thumb = file.replace("mp4", "png")
        videos.append({
            "filename": file,
            "timestamp": time,
            "date": date,
            "timestr": timestr,
            "thumb_path": thumb
        })
    return videos


@app.route('/exit')
def shutdown_server():
    if recording_running:
        recording_process.send_signal(signal.SIGINT)
    os.kill(os.getpid(), signal.SIGINT)
    return "Shutting down server ..."


def signal_handler(a, b):
    print("shutting down server")
    global recording_running
    global recording_process
    if recording_running:
        recording_process.send_signal(signal.SIGINT)
    return "interrupt signal"


@app.route('/start_recording')
def start_recording_route():
    global recording_running
    global recording_process
    if not recording_running:
        recording_running = True
        recording_process = multiprocessing.Process(target=start_recording)
        recording_process.start()
        return redirect(url_for('index'))
    else:
        recording_process.send_signal(signal.SIGINT)
        recording_running = False
        return redirect(url_for('index'))


@app.route('/home')
@app.route('/')
def index():
    video_list = get_videos()
    battery_percentage = battery.get_battery() #only works on PI
    # battery_percentage = 100
    return render_template('home.html',
                           video_list=video_list,
                           recording_running=recording_running,
                           battery_percentage=battery_percentage)


@app.route('/video/<path:video_name>')
def serve_video(video_name):
    return send_from_directory("videos", video_name)
    # video_path = os.path.join(video_dir, video_name)
    # return send_file(video_path, mimetype='video/mp4')


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
    set_config()
    if config["recording_autostart"] == "True":
        start_recording_route()
    get_videos()
    signal.signal(signal.SIGINT, signal_handler)
    print("INIT complete, starting server________________")
    app.run(host='0.0.0.0', port=config["port"], debug=True)
