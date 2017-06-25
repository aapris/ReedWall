"""
This script connects to (local) MQTT broker and starts listening IoT sensor data events.

If a predefined event occurs, script sends a HTTP request to an ESP8266 running
WS2812 LED strip control application and starts an effect in the strip.
https://github.com/kitesurfer1404/WS2812FX/tree/master/examples/esp8266_webinterface

In the same time scripts plays an audio clip.
"""
import paho.mqtt.client as mqtt
import time
import sys
import os
import random
import simpleaudio
import requests
import glob
import re
import threading
from mqttconfig import MQTT_SERVER_ADDR, MQTT_USERNAME, MQTT_PASSWORD
from mqttconfig import LED_SERVER_ADDR

i = 0
effect_end = time.time()

# Play thunder a bit more rarely
last_thunder = 0
thunder_delay = 90  # seconds

# Store audio files to a dict found in sys.argv[1] directory,
# which must contain 4 wav files which are playable by simpleaudio
# and which are named 010_*.wav, 020_*.wav, 030_*.wav, 040_*.wav
wav_files = {}

# Used to stop base mode thread when some sensor event occurs
basic_mode_running = False

# For some reason current sound card can't open audio device if previous object is still active.
# 'audio_in_use' is a kludge to avoid
# _simpleaudio.SimpleaudioError: Error opening PCM device. -- CODE: -16 -- MSG: Device or resource busy
audio_in_use = False


class baseThread(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        global basic_mode_running, audio_in_use
        basic_mode_running = True
        print ("Starting ")
        set_color_and_mode('000000', 1)  # blink turns off all led for 0.5 secs
        set_color_and_mode('666633', 42, 25)  # fireworks
        if audio_in_use:
            print("ERROR: audio in use")
            return
        audio_in_use = True
        wave_obj = simpleaudio.WaveObject.from_wave_file(wav_files['030'])
        play_obj = wave_obj.play()
        while basic_mode_running and play_obj.is_playing():
            time.sleep(0.01)
        play_obj.stop()
        play_obj.wait_done()
        audio_in_use = False
        basic_mode_running = False
        del play_obj
        del wave_obj


def check_args():
    global wav_dir
    if len(sys.argv) > 1:
        wav_dir = sys.argv[1]
    else:
        print("Give directory name containing wav files as an argument!")
        exit(1)
    if os.path.isdir(wav_dir) is False:
        print("Give VALID directory name containing wav files as an argument!")
        exit(2)
    files = glob.glob(os.path.join(wav_dir, '[0-9][0-9][0-9]_*.wav'))
    num_re = re.compile('(\d{3})_.*wav')
    for f in files:
        m = num_re.search(os.path.basename(f))
        if m is not None:
            wav_files[m.group(1)] = f


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("#")


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    global i, last_thunder, effect_end, basic_mode_running
    msg_data = msg.payload.decode('utf-8')
    i += 1
    topic_path = msg.topic.split('/')
    if topic_path[0] == 'ping' or len(topic_path) != 3:  # ignore pings and other garbage
        return
    _, box, sensor = topic_path

    if sensor == 'lux' and float(msg_data) > 200:
        print("LUX")
        if time.time() - effect_end < 10:
            return
        basic_mode_running = False
        # time.sleep(2.1)
        while audio_in_use:  # wait until other players release the sound
            pass
        effect_raisingsun()
        effect_silence(0.5)

        while audio_in_use:  # wait until other players release the sound
            pass
        effect_ripple()
        effect_silence(0.5)
        return

    if box == 'rgt' and sensor == 'pir' and msg_data == '1':
        print("PIR")
        if time.time() - last_thunder < thunder_delay:
            print("Not yet thunder")
            return
        last_thunder = time.time()

        basic_mode_running = False
        while audio_in_use:  # wait until other players release the sound
            pass

        effect_thunder(20.0)
        # effect_silence(1)
        return

    if audio_in_use is False and basic_mode_running is False:
        print("BASE")
        bt = baseThread()
        bt.start()  # Start base mode if nothing is running


# Effects

def set_color_and_mode(color=None, mode=None, speed=None):
    if color is not None:
        url_c = 'http://{}/set?c={}'.format(LED_SERVER_ADDR, color)
        requests.get(url_c)
    if mode is not None:
        url_m = 'http://{}/set?m={}'.format(LED_SERVER_ADDR, mode)
        # print(url_m)
        requests.get(url_m)
    if speed is not None:
        url_t = 'http://{}/set?t={}'.format(LED_SERVER_ADDR, speed)
        requests.get(url_t)


def get_random_time_or_max(_min, _max, endtime):
    t = random.random() * (_max - _min) + _min
    now = time.time()
    # print(t)
    if t > endtime - now:
        t = endtime - now
        print("time exceeded", endtime, now)
    return t


def effect_silence(length_sec):
    set_color_and_mode('000000', 0)  # static
    time.sleep(length_sec)


def effect_thunder(length_sec):
    global audio_in_use, effect_end
    endtime = time.time() + length_sec
    if audio_in_use:
        print("ERROR: audio in use")
        return
    audio_in_use = True
    wave_obj = simpleaudio.WaveObject.from_wave_file(wav_files['010'])
    play_obj = wave_obj.play()
    while play_obj.is_playing():
        set_color_and_mode('ffffcc', 25)  # strobe
        t = get_random_time_or_max(0, 0.4, endtime)
        if t <= 0:
            break
        time.sleep(t)

        set_color_and_mode('0d0e10', 0)  # static
        t = get_random_time_or_max(0.5, 1.0, endtime)
        if t <= 0:
            break
        time.sleep(t)

        set_color_and_mode('d6d9dc', 20)  # sparkle
        t = get_random_time_or_max(0.5, 2.5, endtime)
        if t <= 0:
            break
        time.sleep(t)
    play_obj.wait_done()
    play_obj.stop()
    audio_in_use = False
    # set_color_and_mode('0d0e10', 0)  # static
    set_color_and_mode('000000', 0)  # static
    time.sleep(0.5)
    del play_obj
    del wave_obj
    effect_end = time.time()


def effect_ripple():
    global audio_in_use, effect_end
    set_color_and_mode('000000', 1)  # blink turns off all led for 0.5 secs
    if audio_in_use:
        print("ERROR: audio in use")
        return
    audio_in_use = True
    wave_obj = simpleaudio.WaveObject.from_wave_file(wav_files['020'])
    play_obj = wave_obj.play()
    # set_color_and_mode('f9f356', 11, 200)  # dualscan
    set_color_and_mode('fbf43e', 11, 200)  # dualscan
    play_obj.wait_done()
    play_obj.stop()
    audio_in_use = False

    del play_obj
    del wave_obj
    effect_end = time.time()


def effect_raisingsun():
    global audio_in_use, effect_end
    set_color_and_mode('000000', 1)  # blink turns off all led for 0.5 secs
    if audio_in_use:
        print("ERROR: audio in use")
        return
    audio_in_use = True
    wave_obj = simpleaudio.WaveObject.from_wave_file(wav_files['040'])
    play_obj = wave_obj.play()
    set_color_and_mode('ffc013', 3, 50)
    # set_color_and_mode('fbf43e', 3, 50)
    # set_color_and_mode('f9f356', 3, 50)
    play_obj.wait_done()
    play_obj.stop()
    set_color_and_mode('000000', 0)
    time.sleep(0.38)
    audio_in_use = False
    del play_obj
    del wave_obj
    effect_end = time.time()


client = mqtt.Client()
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
client.on_connect = on_connect
client.on_message = on_message

client.connect(MQTT_SERVER_ADDR, 1883, 60)

# Blocking call that processes network traffic, dispatches callbacks and
# handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a
# manual interface.
try:
    check_args()
    bt_main = baseThread()
    bt_main.start()  # Start base mode on start
    client.loop_forever()
except KeyboardInterrupt:
    basic_mode_running = False
    print("Bye bye!")
