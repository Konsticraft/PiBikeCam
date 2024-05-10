from flask import Flask, render_template, send_file, request, Response, url_for, send_from_directory, redirect, current_app
import os
import subprocess
import multiprocessing
import signal
import datetime
import configparser
import battery #only works on PI
import sys
import cam
import time
import shutil
import threading
from gpiozero import Button, TonalBuzzer
from gpiozero.tones import Tone

app = Flask(__name__)
# Directory where your recorded videos are stored
video_dir = "videos"
thumb_dir = "thumbs"
highlight_dir = "highlights"
output_dir = "output"
temp_dir = "temp"
highlight_thumb_dir = "highlight_thumbs"
config_path = "config.ini"
recording_running = False
recording_process = None
config = {}
recording_process = None
parser = None
battery_percentage = -1
camera_thread = None
button = Button(14)
buzzer = TonalBuzzer(25)
count = 0

def buttonpress():
    global button_press_start_time
    button_press_start_time = time.time()

def buttonrelease():
    global button_press_start_time
    global count
    press_duration = time.time()-button_press_start_time
    print(f'Press Duration: {press_duration}')
    if press_duration > 0.01 :
        if press_duration > 0.5 :
            print(f'Long Press {count}')
            if recording_running:
                camera_thread.save(int(config["highlight_before"]), int(config["highlight_after"]))
                buzzer.play(Tone("C4"))
                time.sleep(0.2)
                buzzer.play(Tone("D4"))
                time.sleep(0.2)
                buzzer.play(Tone("E4"))
                time.sleep(0.2)
                buzzer.play(Tone("A4"))
                time.sleep(0.2)
                buzzer.stop()
        else:
            print(f'Short Press {count}')
        button_press_start_time = None
        count+= 1

def set_config():
    print("reading config file")
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
    rec_bef = config["highlight_before"]
    rec_aft = config["highlight_after"]
    return render_template('settings.html', auto_rec = auto_rec, port = port, seg_len = seg_len, battery_percentage=battery_percentage, rec_bef = rec_bef, rec_aft = rec_aft)

@app.route('/update_settings', methods=['POST'])
def update_settings():
    rec_auto = "True" if request.form.get('Autostart') else "False"
    seg_len = request.form.get('seg_len')
    port = request.form.get('port')
    rec_bef = request.form.get('rec_bef')
    rec_aft = request.form.get('rec_aft')
    global config
    config = {
         "recording_autostart" : rec_auto,
         "segment_length" : seg_len,
         "port" : port,
         "highlight_before" : rec_bef,
         "highlight_after" : rec_aft
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
        time = datetime.datetime.strptime(file, "video_%Y-%m-%d_%H:%M:%S.mp4")
        timestr = datetime.datetime.strftime(time, "%d.%m.%Y %H:%M")
        date = datetime.datetime.strftime(time, "%Y-%m-%d")
        #thumb = os.path.join(thumb_dir,file.replace("mp4", "png")).replace("\\","/")
        thumb = file.replace("mp4", "png")
        videos.append({
              "filename" : file,
              "timestamp" : time,
              "date" : date,
              "timestr" : timestr,
              "thumb_path" : thumb
		})
    videos = sorted(videos, key = lambda d: d["timestamp"], reverse = True)
    return videos

def get_highlights():
    videos = []
    for file in os.listdir(highlight_dir):
        filename = file
        time = datetime.datetime.strptime(file, "highlight_%Y-%m-%d_%H:%M:%S.mp4")
        timestr = datetime.datetime.strftime(time, "%d.%m.%Y %H:%M")
        date = datetime.datetime.strftime(time, "%Y-%m-%d")
        #thumb = os.path.join(thumb_dir,file.replace("mp4", "png")).replace("\\","/")
        thumb = file.replace("mp4", "png")
        videos.append({
              "filename" : file,
              "timestamp" : time,
              "date" : date,
              "timestr" : timestr,
              "thumb_path" : thumb
		})
    videos = sorted(videos, key = lambda d: d["timestamp"], reverse = True)
    return videos

@app.route('/exit')
def shutdown_server():
    if recording_running:
        #recording_process.send_signal(signal.SIGINT)
        camera_thread.stop()
        camera_thread.join()
    os.kill(os.getpid(), signal.SIGINT)
    return "Shutting down server ..."


def signal_handler(a,b):
    print("signal handler triggered")
    global recording_running
    global recording_process
    global camera_thread
    if recording_running:
        # recording_process.send_signal(multiprocessing.signal.SIGINT)
        camera_thread.stop()
        camera_thread.join()
    os.kill(os.getpid(), signal.SIGINT)
    return "interrupt signal"

def start_recording_noroute():
    global camera_thread
    global recording_running
    if not recording_running:
        camera_thread = cam.Camera(int(config["segment_length"]))
        camera_thread.start()
        recording_running = True
    else:
        print("stopping camera thread")
        camera_thread.stop()
        camera_thread.join()
        recording_running = False


@app.route('/start_recording')
def start_recording_route():
    start_recording_noroute()
    return redirect(url_for('index'))

@app.route('/home')
@app.route('/')
def index():
    highlight_list = get_highlights()
    video_list = get_videos()
    global battery_percentage
    battery_percentage = battery.get_battery() #only works on PI
    # battery_percentage = 100
    return render_template('home.html',
                           video_list=video_list,
                           highlight_list = highlight_list,
                           recording_running=recording_running,
                           battery_percentage=battery_percentage)


@app.route('/video/<path:video_name>')
def serve_video(video_name):
    return send_from_directory("videos", video_name)
    # video_path = os.path.join(video_dir, video_name)
    # return send_file(video_path, mimetype='video/mp4')

@app.route('/thumbs/<path:thumb_name>')
def serve_thumb(thumb_name):
    if thumb_name.startswith("highlight"):
        return send_from_directory(highlight_thumb_dir, thumb_name)
    else:
        return send_from_directory(thumb_dir, thumb_name)

@app.route('/thumbs/<path:thumb_name>')
def serve_highlight_thumb(thumb_name):
    return send_from_directory(highlight_thumb_dir, thumb_name)


@app.route('/stream/<path:video_name>')
def stream_video(video_name):
    if video_name.startswith("highlight"):
        video_path = os.path.join(highlight_dir, video_name)
    else:
        video_path = os.path.join(video_dir, video_name)
    size = os.stat(video_path)
    size = size.st_size
    
    chunk_size = (10 ** 6) * 5
    #start = int(re.sub("\D","", headers["range"]))
    #end = min(start + chunk_size, size-1)
    start, end = parse_range_header(request.headers.get('Range'), size)
    content_length = end - start + 1
    
    def generate(video_path, start, chunk_size):
        with open(video_path, 'rb') as video_file:
            video_file.seek(start)
            chunk = video_file.read(chunk_size)
        return chunk
    
    #response = Response(generate(), mimetype='video/mp4')
    
    headers = {
        "Content-Range" : f'bytes {start}-{end}/{size}',
        'Accept-Ranges' : 'bytes',
        "Content-Length" : content_length,
        "Content-Type":"video/mp4",
        }
        
    return current_app.response_class(generate(video_path, start, chunk_size), 206, headers)
    #file_size = os.path.getsize(video_path)
    #response.headers.add('Content-Length', str(file_size))
    
    #range_header = request.headers.get('Range')
    if False:
        start, end = parse_range_header(range_header, file_size)
        print(f'start: {start} end: {end}')
        if start is not None and end is not None:
            response.status_code = 206
            response.headers.add('Content-Range', f'bytes {start}-{end}/{file_size}')
            response.headers.add('Content-Length', str(end-start+1))
            response.headers.add('Accept-Ranges', 'bytes')
            with open(video_path, 'rb') as video_file:
                video_file.seek(start)
                return response

    return response

def parse_range_header(range_header, file_size):
    ranges = range_header.split('=')[1].split('-')
    start = int(ranges[0]) if ranges[0] else 0
    end = int(ranges[1]) if ranges[1] else file_size -1
    return start, end
    
def convert_old_files():
    files = os.listdir(output_dir)
    for file in files:
        src_path = os.path.join(output_dir, file)
        dest_path = os.path.join(temp_dir, file)
        shutil.move(src_path, dest_path)
    temp_files = os.listdir(temp_dir)
    files.extend(temp_files)
    thread = threading.Thread(target=convert_from_temp, args=(files,))
    thread.start()
    
    
def convert_from_temp(files):
    print("convert")
    for file in files:
        file = file[:-5]
        print(f"converting old file {file}")
        command = f"ffmpeg -i /home/pi/PiBikeCam/temp/{file}.h264 -c:v copy -r 30 /home/pi/PiBikeCam/videos/{file}.mp4"
        subprocess.run(command, shell = True)
        os.remove(f"/home/pi/PiBikeCam/temp/{file}.h264")
        
    

if __name__ == '__main__':
    button.when_pressed = buttonpress
    button.when_released = buttonrelease
    set_config()
    convert_old_files()
    if config["recording_autostart"] == "True":
        start_recording_noroute()
    get_videos()
    #signal.signal(signal.SIGINT, signal_handler)
    print("INIT complete, starting server________________")
    buzzer.play(Tone("C4"))
    time.sleep(0.4)
    buzzer.play(Tone("A4"))
    time.sleep(0.6)
    buzzer.stop()
    try:
        app.run(host='0.0.0.0', port=config["port"], debug=True, threaded=True)
    except KeyboardInterrupt:
        pass
    finally:
        print("shut down")
    
