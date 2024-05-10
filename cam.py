import picamera
import time
import datetime
import os
import subprocess
import multiprocessing
import threading

def convert_to_mp4(input_file, timestamp, highlights, final = False):
    p = multiprocessing.Process(target = converter_process, args = (input_file, highlights, timestamp))
    p.start()
    if final:
        p.join()
        
def converter_process(input_file, highlights, timestamp):
    #command = f"ffmpeg -i /home/pi/PiBikeCam/output/{input_file}.h264 -b 4000k -c:v h264_omx /home/pi/PiBikeCam/videos/{input_file}.mp4"
    command = f"ffmpeg -i /home/pi/PiBikeCam/output/{input_file}.h264 -c:v copy -r 30 /home/pi/PiBikeCam/videos/{input_file}.mp4"
    #print(f"converting with command {command}\n")
    converter_process = subprocess.run(command, shell = True)
    os.remove(f"/home/pi/PiBikeCam/output/{input_file}.h264")
    for time, before, after in highlights:
        start = max(0, time - timestamp - before)
        time = datetime.datetime.fromtimestamp(time-before).strftime("%Y-%m-%d_%H:%M:%S")
        name = f'highlight_{time}'
        command = f"ffmpeg -ss {start} -i /home/pi/PiBikeCam/videos/{input_file}.mp4 -t {after + before} -map 0 -c:v copy -r 30 /home/pi/PiBikeCam/highlights/{name}.mp4"
        converter_process = subprocess.run(command, shell = True)
        command_thumb = f'ffmpeg -ss {before} -i /home/pi/PiBikeCam/videos/{input_file}.mp4 -vframes 1 /home/pi/PiBikeCam/highlight_thumbs/{name}.png'
        converter_process = subprocess.run(command_thumb, shell = True)
        
        
        
class Camera(threading.Thread):
    
    def __init__(self, SEGMENT_LEN):
        super(Camera, self).__init__()
        self.SEGMENT_LEN = SEGMENT_LEN
        self.stop_event = threading.Event()
        self.highlights = []    # [(timestamp, duration)]
        self.min_time = time.time()
    
    
    def stop(self):
        self.stop_event.set()
        
    def save(self, dur_before, dur_after):
        print(f'saving from -{dur_before} to {dur_after}')
        self.highlights.append((time.time(), dur_before, dur_after))
        self.min_time = time.time() + dur_after + 5
        
        
    
    def run(self):
        
        # Set up the camera
        camera = picamera.PiCamera()
        camera.resolution = (1920, 1080)  # Adjust the resolution as needed
        camera.framerate = 30  # Adjust the framerate as needed

        # Create a file name template for the video segments
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
        output_file_template = f"output/video_{timestamp}.h264"
        file_name = f"video_{timestamp}"



        # Record video continuously with annotation
        while not self.stop_event.is_set():
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
            camera.annotate_text = timestamp
            output_file_template = f"output/video_{timestamp}.h264"
            print("starting recording " + output_file_template)
            file_name = f"video_{timestamp}"
            #TODO: add thumbnail creation
            thumb_file = f"thumbs/video_{timestamp}.png"
            camera.capture(thumb_file)
            camera.start_recording(output_file_template)
            start_time = time.time()

            while ((time.time() - start_time) < self.SEGMENT_LEN or self.min_time > time.time()) and not self.stop_event.is_set():
                #print("recording running")
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
                camera.annotate_text = timestamp
                camera.wait_recording(1)

            camera.stop_recording()
            convert_to_mp4(file_name, start_time, self.highlights.copy(), self.stop_event.is_set())
            self.highlights = []
        camera.close()
            
