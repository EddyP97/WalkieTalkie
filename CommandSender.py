import paho.mqtt.client as mqtt
import logging
from threading import Thread
import json
from appJar import gui
import AudioModule

# MQTT broker address
MQTT_BROKER = 'mqtt.item.ntnu.no'
MQTT_PORT = 1883


class CommandSenderComponent:
    """
    The component to send voice commands.
    """
    
    def __init__(self, walkieNumber):
        self.MQTT_TOPIC_COMMANDSENDER = 'ttm4115/team_15/answer' + walkieNumber
        self.MQTT_TOPIC_WALKIE = 'ttm4115/team_15/walkie' + walkieNumber

        # get the logger object for the component
        self._logger = logging.getLogger(__name__)
        print('logging under name {}.'.format(__name__))
        self._logger.info('Starting Component')

        # create a new MQTT client
        self._logger.debug('Connecting to MQTT broker {} at port {}'.format(MQTT_BROKER, MQTT_PORT))
        self.mqtt_client = mqtt.Client()
        # callback methods
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        # Connect to the broker
        self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
        self.mqtt_client.subscribe(self.MQTT_TOPIC_COMMANDSENDER)
        # start the internal loop to process MQTT messages
        self.mqtt_client.loop_start()
        self.audioHelper = AudioModule.AudioHelper()

        self.create_gui()


    def on_connect(self, client, userdata, flags, rc):
        # we just log that we are connected
        self._logger.debug('MQTT connected to {}'.format(client))

    def on_message(self, client, userdata, msg):
        # encdoding from bytes to string. This
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except Exception as err:
            self._logger.error('Message sent to topic {} had no valid JSON. Message ignored. {}'.format(msg.topic, err))
            return

        command = payload.get('command')
        if command == 'text':
            print(payload.get('message'))
            self.audioHelper.text_to_speech(payload.get('message')) #tried to implement text-to-speach

    
    def create_gui(self):
        self.app = gui("Walkie Talkie")
        self.app.setBg("SkyBlue")
        self.app.setFg("Azure")
        def publish_command(command):
            payload = json.dumps(command)
            self._logger.info(command)
            self.mqtt_client.publish(self.MQTT_TOPIC_WALKIE, payload=payload, qos=2)

        self.app.startLabelFrame('Sending messages:')
        def on_button_pressed_send(title):
            command = {"command": "send_message"}
            publish_command(command)
        def on_button_pressed_record(title):
            command = {"command": "start_recording"}
            publish_command(command)
        def on_button_pressed_stop_record(title):
            command = {"command": "stop_recording"}
            publish_command(command)
        self.app.addButton('Send message', on_button_pressed_send)
        self.app.addButton('Record the message', on_button_pressed_record)
        self.app.addButton('Stop the recording', on_button_pressed_stop_record)
        self.app.stopLabelFrame()

        self.app.startLabelFrame('Choosing a channel:')
        def on_button_pressed_channel(title):
            channel = title[-1]
            command = {"command": "chosen", "channel": channel}
            publish_command(command)
        self.app.startFrame("LEFT", row=0, column=0)
        self.app.addButton('Select channel 1', on_button_pressed_channel)
        self.app.addButton('Select channel 2', on_button_pressed_channel)
        self.app.addButton('Select channel 3', on_button_pressed_channel)
        self.app.stopFrame()
        self.app.startFrame("RIGHT", row=0, column=1)
        self.app.addButton('Select channel 4', on_button_pressed_channel)
        self.app.addButton('Select channel 5', on_button_pressed_channel)
        self.app.addButton('Select channel 6', on_button_pressed_channel)
        self.app.stopFrame()
        self.app.stopLabelFrame()

        self.app.startLabelFrame('Emergency Broadcast:')
        def on_button_pressed_emergency(title):
            command = {"command": "emergency_broadcast"}
            publish_command(command)
        def on_button_pressed_emergency_abort(title):
            command = {"command": "abort"}
            publish_command(command)
        self.app.addButton('Send Emergency Broadcast', on_button_pressed_emergency)
        self.app.addButton('Abort', on_button_pressed_emergency_abort)
        self.app.stopLabelFrame()

        self.app.startLabelFrame('Stored messages:')
        def on_button_pressed_play_messages(title):
            command = {"command": "playback"}
            publish_command(command)
        def on_button_pressed_delete_messages(title):
            command = {"command": "delete_stored"}
            publish_command(command)
        self.app.addButton('Playback stored messages', on_button_pressed_play_messages)
        self.app.addButton('Delete stored messages', on_button_pressed_delete_messages)
        self.app.stopLabelFrame()

        self.app.startLabelFrame('What do you want to do with the received message?:')
        def on_button_pressed_listen_messages(title):
            command = {"command": "listen_to_message"}
            publish_command(command)
        def on_button_pressed_listen_later_messages(title):
            command = {"command": "listen_later"}
            publish_command(command)
        self.app.addButton('Listen to the message', on_button_pressed_listen_messages)
        self.app.addButton('Store message for later', on_button_pressed_listen_later_messages)
        self.app.stopLabelFrame()
        self.app.go()


    def stop(self):
        """
        Stop the component.
        """
        # stop the MQTT client
        self.mqtt_client.loop_stop()


# logging.DEBUG: Most fine-grained logging, printing everything
# logging.INFO:  Only the most important informational log items
# logging.WARN:  Show only warnings and errors.
# logging.ERROR: Show only error messages.
debug_level = logging.WARN
logger = logging.getLogger(__name__)
logger.setLevel(debug_level)
ch = logging.StreamHandler()
ch.setLevel(debug_level)
formatter = logging.Formatter('%(asctime)s - %(name)-12s - %(levelname)-8s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

#CommandSenderComponent()
