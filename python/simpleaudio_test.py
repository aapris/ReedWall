import simpleaudio as sa
import time
import sys

wave_obj = sa.WaveObject.from_wave_file(sys.argv[1])
#for i in range(1000):
    #play_obj = wave_obj.play()
    #time.sleep(0.001)

play_obj = wave_obj.play()
play_obj.wait_done()
