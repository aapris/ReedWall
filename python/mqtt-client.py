import paho.mqtt.client as mqtt
import datetime
import time
import json
import sys
import random
import simpleaudio as sa
import simpleaudio
import requests
from mqttconfig import MQTT_SERVER_ADDR, MQTT_USERNAME, MQTT_PASSWORD
from mqttconfig import LED_SERVER_ADDR
fn = sys.argv[1]
wave_obj = simpleaudio.WaveObject.from_wave_file(fn)
# sa.WaveObject.from_wave_read()
i = 0

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("#")


last_thunder = 0


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    global i, last_thunder
    #msg_data = int(msg.payload.decode('utf-8'))
    msg_data = msg.payload.decode('utf-8')
    #print(msg_data)
    i += 1
    #print(i, end='\n')
    print('{} {} {}'.format(i, msg.topic, msg_data))
    #if msg.topic == 'sensor/lux' and float(msg_data) > 200:
    if msg.topic == 'sensor/lux' and float(msg_data) > 200:
        print("LUX")
        url_m = 'http://{}/set?m={}'.format(LED_SERVER_ADDR, 11)  # liplatus
        # cfe2dc
        url_c = 'http://{}/set?c={}'.format(LED_SERVER_ADDR, 'ffffcc')  # liplatus
        requests.get(url_m)
        requests.get(url_c)
        play_obj = wave_obj.play()

    if msg.topic == 'sensor/pir' and msg_data == '1':
        if time.time() - last_thunder < 40:
            return
        last_thunder = time.time()
        print("PIR")
        play_obj = wave_obj.play()
        effect_ripple(15)
        effect_raisingsun(20)
        effect_thunder(15)



#        print(requests.get(url_m))
#        print(requests.get(url_m))
    #print(".", end='\n')
#    if msg_data < 50:
#        try:
#            play_obj = wave_obj.play()
#        #except simpleaudio._simpleaudio.SimpleaudioError as err:
#        except Exception as err:
#            print("ERRORIA PUKKKAA", err)


# Effects

def set_color_and_mode(color=None, mode=None, speed=None):
    if color != None:
        url_c = 'http://{}/set?c={}'.format(LED_SERVER_ADDR, color)  # liplatus
        requests.get(url_c)
    if mode != None:
        url_m = 'http://{}/set?m={}'.format(LED_SERVER_ADDR, mode)  # strobe
        requests.get(url_m)
    if speed != None:
        url_t = 'http://{}/set?t={}'.format(LED_SERVER_ADDR, speed)  # strobe
        requests.get(url_t)


def get_random_time_or_max(_min, _max, endtime):
    t = random.random() * (_max - _min) + _min
    now = time.time()
    print(t)
    if t > endtime - now:
        t = endtime - now
        print("time exceeded", endtime, now)
    return t


def effect_thunder(length_sec):
    endtime = time.time() + length_sec
    while time.time() < endtime:
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

        set_color_and_mode('d6d9dc', 20)  # static
        t = get_random_time_or_max(0, 5.0, endtime)
        if t <= 0:
            break
        time.sleep(t)


def effect_ripple(length_sec):
    endtime = time.time() + length_sec
    while time.time() < endtime:
        set_color_and_mode('ebf2f0', 11, 200)  # dualscan
        time.sleep(length_sec)
        #t = get_random_time_or_max(15, 1, endtime)
        #if t <= 0:
        #    break
        #time.sleep(t)


def effect_raisingsun(length_sec):
    endtime = time.time() + length_sec
    while time.time() < endtime:
        set_color_and_mode('ffc013', 3, 50)  # strobe
        time.sleep(length_sec)
        #t = get_random_time_or_max(15, 1, endtime)
        #if t <= 0:
        #    break
        #time.sleep(t)



# The callback for when a PUBLISH message is received from the server.
def xon_message(client, userdata, msg):
    global i
    msg_data = json.loads(msg.payload.decode('utf-8'))
    now = datetime.datetime.utcnow()
    msg_data['timestamp'] = now.strftime('%Y-%m-%dT%H:%M:%SZ')
    #print(msg_data)
    #print(msg.topic+" "+str(msg.payload))
    i += 1
    print(i, end='\n')
    #print(".", end='\n')
    try:
        play_obj = wave_obj.play()
    #except simpleaudio._simpleaudio.SimpleaudioError as err:
    except Exception as err:
        print("ERRORIA PUKKKAA", err)
        #raise



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
    client.loop_forever()
except KeyboardInterrupt:
    print("bye bye")
