import picamera
import time
import datetime
import os
import subprocess
import multiprocessing


def convert_to_mp4(input_file, final = False):
    p = multiprocessing.Process(target = converter_process, args = (input_file,))
    p.start()
    if final:
        p.join()

def converter_process(input_file):
    command = f"ffmpeg -i /home/pi/PiBikeCam/output/{input_file}.h264 -codec copy /home/pi/PiBikeCam/videos/{input_file}.mp4"
    #print(f"converting with command {command}\n")
    converter_process = subprocess.run(command, shell = True)
    
    os.remove(f"/home/pi/PiBikeCam/output/{input_file}.h264")
    
def record_video(SEGMENT_LEN = 60):
    
    # Set up the camera
    camera = picamera.PiCamera()
    camera.resolution = (1920, 1080)  # Adjust the resolution as needed
    camera.framerate = 30  # Adjust the framerate as needed

    # Create a file name template for the video segments
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
    output_file_template = f"output/video_{timestamp}.h264"
    file_name = f"video_{timestamp}"



    # Record video continuously with annotation
    try:
        while True:
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

            while (time.time() - start_time) < SEGMENT_LEN:
                #print("recording running")
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
                camera.annotate_text = timestamp
                camera.wait_recording(1)

            camera.stop_recording()
            convert_to_mp4(file_name)
    except KeyboardInterrupt:
        pass
    finally:
        print("Stopping Recording") 
        convert_to_mp4(file_name, final = True)
        camera.close()
        
if __name__ == "__main__":
    record_video()
