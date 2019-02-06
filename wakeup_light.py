#!/usr/bin/python3

import paho.mqtt.client as mqtt
import time
import threading
import datetime

sequence_duration = 20*60 # in sec
seconds_between_updates = 4 # sampling time of the sequence
seconds_pill2kill_check = 0.1 # how often to check to abort
seconds_after_alarm = 10 # how long to stay on after alarm rings

mqtt_broker_addr = "192.168.0.10"
mqtt_client_name = "wakeup_light_script"
mqtt_topic = "wakeup_light"
qos = 1


zigbee_device1 = "0x0017880104727af9" # philips hue ambiance
color_temp1 = 400
max_brightness1 = 255

wakeup_running = False
light_on = False

def publish_(state, rel_brightness=0): # brightness in 0-1
  global light_on 
  if state = "ON":
    light_on = True
  else:
    light_on = False
  # device 1
  topic = "zigbee2mqtt/"+zigbee_device1+"/set"
  payload='{ "state": "%s", "brightness": %f, "color_temp": %d}'%(state,max_brightness1*rel_brightness,color_temp1)
  print("PUBLISH to topic: "+topic+", payload: "+payload)
  client.publish(topic=topic, payload=payload, qos=qos, retain=False)
  
  
def switch_off_all_lights():
  print("switch_off_all_lights")
  publish_("OFF")
  
  
def do_wakeup(pill2kill,seconds_to_sequence):
  global wakeup_running
  wakeup_running = True
  print("do_wakeup")
  print("seconds to light sequence: %d"%seconds_to_sequence)
  t = time.time()
  
  while t+seconds_to_sequence > time.time():
    if pill2kill.is_set():
      print("wakeup aborted")
      wakeup_running = False
      publish_("OFF")  
      return
    time.sleep(seconds_pill2kill_check)
      
  print("start of sequence")
  for i in range(0,int(sequence_duration/seconds_between_updates)):
    publish_("ON",i*seconds_between_updates/sequence_duration)
    t = time.time()
    while time.time() < t+seconds_between_updates:
      time.sleep(seconds_pill2kill_check)
      if pill2kill.is_set():
        print("wakeup aborted")
        wakeup_running = False
        publish_("OFF")  
        return
      
  print("start time after alarm: %d seconds"%seconds_after_alarm)
  t = time.time()
  while time.time() < t+seconds_after_alarm:
    time.sleep(seconds_pill2kill_check)
    if pill2kill.is_set():
      print("wakeup aborted")
      wakeup_running = False
      publish_("OFF")  
      return
     
  print("end of do_wakeup function, go up lazy bastard") 
  publish_("OFF")

  return
 

def on_connect(client, userdata, flags, rc):
  print("Connected to mqtt broker with result code "+str(rc))
  switch_off_all_lights()
  client.subscribe(mqtt_topic)
  
  
def on_message(client, userdata, msg):
  
  global pill2kill, wakeup_running, light_on
  
  payload = msg.payload.decode("utf-8")
  print("MSG TO SUSCRIBED TOPIC, topic: "+msg.topic+", payload: "+payload)
  cmd = (payload.split(','))[0]
  print("cmd: %s"%(cmd))

  if cmd == "set_wakeup":
    
    arg = (payload.split(','))[1]  
    if arg.startswith("%") or arg.startswith("-"):
      print("no valid data")
      return
    print("valid data") 
    if wakeup_running:
      print("already running, set new time")
      pill2kill.set()
       
    seconds_to_sequence = int(arg) - sequence_duration 
    print("seconds to start of light sequence: %d"%seconds_to_sequence)
    print("corresponding to %s"%(datetime.datetime.now()+datetime.timedelta(seconds=seconds_to_sequence)))
    
    pill2kill = threading.Event()  
    threading.Thread(target=do_wakeup, args=(pill2kill,seconds_to_sequence,)).start()      
   
  elif cmd == "do_wakeup":
    if wakeup_running == True:
      print("already running, start from begin")
      pill2kill.set()
      
    pill2kill = threading.Event()  
    threading.Thread(target=do_wakeup, args=(pill2kill,0,)).start() 

  elif cmd == "stop_wakeup":
    if wakeup_running == False:
      print("nothing to stop")
    pill2kill.set()
    wakeup_thread.join()

  elif cmd == "toggle":
    if not light_on: 
      print("switch on light")
      publish_("ON",0.5)
    else:
      print("switch off light")
      publish_("OFF")
  else:

    print("unknown command")
  
    
    
if __name__ == "__main__":

  client = mqtt.Client(mqtt_client_name)
  client.connect(mqtt_broker_addr)

  client.on_connect = on_connect
  client.on_message = on_message

  threading.Thread(client.loop_forever()).start()

