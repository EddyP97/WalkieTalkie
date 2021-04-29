import paho.mqtt.client as mqtt
import stmpy
import logging
import json
import os
import AudioModule
import time

# MQTT broker address
MQTT_BROKER = 'mqtt.item.ntnu.no'
MQTT_PORT = 1883

MQTT_TOPIC_SEND = ''
MQTT_TOPIC_RECEIVE = ''
MQTT_TOPIC_COMMANDSENDER = ''

channel = ''
state = 'idle'

class WalkieLogic:
    """
    This is the support object for a state machine that models a walkie talkie.
    """
    def __init__(self, name):
        """
        ## Start of MQTT
        We subscribe to the topic(s) the component listens to.
        The client is available as variable `self.client` so that subscriptions
        may also be changed over time if necessary.
        The MQTT client reconnects in case of failures.
        ## State Machine driver
        We create a single state machine driver for STMPY. This should fit
        for most components. The driver is available from the variable
        `self.driver`. You can use it to send signals into specific state
        machines, for instance.
        """
        # get the logger object for the component
        self._logger = logging.getLogger(__name__)
        print('logging under name {}.'.format(__name__))
        self._logger.info('Starting Component')

        self.name = name

        # broker and port
        thisWalkie = "1"
        otherWalkie = name
        if thisWalkie == "1": otherWalkie = "2"

        # topics for communication
        self.MQTT_TOPIC_RECEIVE = 'ttm4115/team_15/walkie' + thisWalkie
        self.MQTT_TOPIC_SEND = 'ttm4115/team_15/walkie' + otherWalkie
        self.MQTT_TOPIC_COMMANDSENDER = 'ttm4115/team_15/answer' + name
        
        # create a new MQTT client
        self._logger.debug('Connecting to MQTT broker {} at port {}'.format(MQTT_BROKER, MQTT_PORT))
        self.mqtt_client = mqtt.Client()
        # callback methods
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        # Connect to the broker
        self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
        # subscribe to proper topic(s) of your choice
        self.mqtt_client.subscribe(self.MQTT_TOPIC_RECEIVE)
        # start the internal loop to process MQTT messages
        self.mqtt_client.loop_start()
        
        self.message_count = 0
        self.state = 'idle'
        self.last_message_content = b''
        self.last_emergency_message = ''
        self.list_of_messages= []

        #Audio stuff
        self.audioHelper = AudioModule.AudioHelper()

    #send text to commandsender
    def publish_command(self, command):
            payload = json.dumps(command)
            self._logger.info(command)
            self.mqtt_client.publish(self.MQTT_TOPIC_COMMANDSENDER, payload=payload, qos=2)

    def on_connect(self, client, userdata, flags, rc):
        self._logger.debug('MQTT connected to {}'.format(client))
        
    def store_message(self, message):
        file_name = 'message_' + str(self.message_count) + ".wav"
        
        AudioModule.process_audio(message, file_name)
        self.list_of_messages.append(file_name)
        self.message_count += 1
    
    def send_message(self, payload, channel):
        try:
            topic = 'ttm4115/team_15/walkie' + channel
            #payload = json.dumps(payload)
            self.mqtt_client.publish(topic, payload, qos = 2)
        except Exception as e:
            print(e)

    def playback_emergency(self):
        self.state = 'emergency_message_received'
        print('State walkie ' + self.name + ': emergency_message_received')
        self.audioHelper.text_to_speech(self.last_emergency_message)
        self.stm.send('message_played')
        

    def emergency_state(self):
        self.state = 'emergency_broadcasting'
        print('State walkie ' + self.name + ': emergency_broadcasting')
        
    
    def idle_state(self):
        self.state = 'idle'
        print('State walkie ' + self.name + ': idle')
    
    def send_emergency(self):
        #sending to the other walkie
        message = {'command': 'emergency_received', 'message': "Worker " + self.name + " is in danger. Please send help!"}

        payload = json.dumps(message)
        self._logger.info(message)
        self.mqtt_client.publish(self.MQTT_TOPIC_SEND, payload=payload, qos=2)
        

    def prompt_listen(self):
        self.state = 'message_received'
        print('State walkie ' + self.name + ': message_received')
        message = {'command': 'text', 'message': 'You have received a message. Do you want to listen to it now?'}
        self.publish_command(message)
        

    def playback_message(self):
        self.state = 'playback_message'
        print('State walkie ' + self.name + ': playback_message')
        message = self.last_message_content
        AudioModule.process_audio(message)
        self.audioHelper.play_audio(AudioModule.FILENAME)
        self.stm.send('message_played') #TODO Message is not yet completely played here
        
    
    def listen_stored(self):
        self.state = 'playback_stored'
        print('State walkie ' + self.name + ': playback_stored')

        for msg in self.list_of_messages:
            self.audioHelper.play_audio_noStm(msg)
            os.remove(msg)
            self.list_of_messages.remove(msg)
        self.stm.send('playback_finished')

    
    def prompt_choose(self):
        self.state = 'choose_recipients'
        print('State walkie ' + self.name + ': choose_recipients')
        try:
            message = {'command': 'text', 'message': 'What channel do you want to send to?'}
            self.publish_command(message)
        except Exception as e:
            print(e)
        
        return None

    def prompt_record(self):
        self.state = 'record_message'
        print('State walkie ' + self.name + ': record_message')
        try:
            message = {'command': 'text', 'message': 'What is the message to send?'}
            self.publish_command(message)
        except Exception as e:
            print(e)
        return None

    def delete_messages(self):
        for msg in self.list_of_messages:
            print(msg)
            os.remove(msg)
        self.list_of_messages.clear()
        return None
    
    def on_message(self, client, userdata, msg):
        # encdoding from bytes to string.
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            
        except Exception as err:
            payload = {'command' : 'message_received', 'message' : msg.payload}
            #self._logger.error('Message sent to topic {} had no valid JSON. Message ignored. {}'.format(msg.topic, err))
            #return
        command = payload.get('command')
        
        if self.state == 'idle':

            if self.check_emergency(payload): return

            elif command == 'send_message':
                try:
                    self.stm.send('send_message')
                except Exception as err:
                    self._logger.error('Invalid arguments to command. {}'.format(err))
                    
            elif command == 'playback':
                try:
                    self.stm.send('playback')
                except Exception as err:
                    self._logger.error('Invalid arguments to command. {}'.format(err))
                
            elif command == 'message_received':
                try:
                    self.last_message_content = payload.get('message')
                    self.stm.send('message_received')
                except Exception as err:
                    self._logger.error('Invalid arguments to command. {}'.format(err))

            elif command == 'delete_stored':
                try:
                    self.stm.send('delete_stored')
                except Exception as err:
                    self._logger.error('Invalid arguments to command. {}'.format(err))

            else:
                self._logger.error('Unknown command {}. Message ignored.'.format(command))
            return None

        elif self.state == 'choose_recipients':
            if self.check_emergency(payload): return
            
            elif command == 'abort':
                print("Non chosen, aborted")
                self.stm.send('abort_choosing')
                
            elif command == 'chosen':
                self.channel = payload.get('channel')
                print('Channel chosen: ' + self.channel)
                self._logger.debug('Channel is {}'.format(command))
                self.stm.send('chosen')
            
            else:
                self._logger.error('Unknown command {}. Message ignored.'.format(command))
            return None
        

        elif self.state == 'record_message':
            if self.check_emergency(payload): return

            elif command == 'abort':
                print('Message sending aborted.')
                self.stm.send('abort_sending')   

            elif command == 'start_recording':
                self.audioHelper.start_recording()

            elif command == 'stop_recording':
                print("Stopping the recording from main logic")
                self.audioHelper.stop_recording()
                #time.sleep(1)
                record = self.audioHelper.get_recorded_samples()
                payload = record#{'command': 'message_received', 'message': record}
                self.send_message(payload, self.channel)
                self.stm.send('done_recording')
                return

            else:
                self._logger.error('Unknown command {}. Message ignored.'.format(command))
            return None

        elif self.state == 'playback_stored':
            if self.check_emergency(payload): return 

            elif command == 'abort':
                print("Aborted playing")
                self.audioHelper.stop_audio()
                self.stm.send('abort')

            else:
                self._logger.error('Unknown command {}. Message ignored.'.format(command))
            return None

        elif self.state == 'playback_message':
            if self.check_emergency(payload):
                #self.store_message(self.last_message_content)
                return
            
            else:
                self._logger.error('Unknown command {}. Message ignored.'.format(command))
            return None

        elif self.state == 'message_received':
            if self.check_emergency(payload):
                #self.store_message(self.last_message_content)
                return

            else:
                print('Command in message is {}'.format(command))
                if command == 'listen_later':
                    print('Message stored for later')
                    self.stm.send('listen_later', args = [self.last_message_content])
                
                elif command == 'listen_to_message':
                    self.stm.send('listen_to_message')
                
                else:
                    self._logger.error('Unknown command {}. Message ignored.'.format(command))
                return None
        
        elif self.state == 'emergency_broadcasting':
            if command == 'abort':
                print("Emergency broadcast aborted")
                self.stm.send('abort')
            else:
                self._logger.error('Unknown command {}. Message ignored.'.format(command))
            return None
        
    
    def check_emergency(self, payload):
        command = payload.get('command')
        
        if command == 'emergency_received':
            try:
                print(payload.get('message'))
                self.last_emergency_message = payload.get('message')
                self.stm.send('emergency_received')
                return True
            except Exception as err:
                self._logger.error('Invalid arguments to command. {}'.format(err))
                
        elif command == 'emergency_broadcast':
            try:
                print("Emergency broadcast activated")
                self.stm.send('emergency_broadcast', args=[self.last_message_content])
                return True
            except Exception as err:
                self._logger.error('Invalid arguments to command. {}'.format(err))

        else: return False


    def create_machine(name):
        walkie_logic = WalkieLogic(name=name)
        #initial
        t0 = {'source': 'initial', 'target': 'idle'}
        #from idle
        t1 = {'source': 'idle', 'target': 'message_received',                           'trigger': 'message_received'}
        t2 = {'source': 'idle', 'target': 'playback_stored',                            'trigger': 'playback'}
        t3 = {'source': 'idle', 'target': 'choose_recipients',                          'trigger': 'send_message'}
        t4 = {'source': 'idle', 'target': 'emergency_broadcasting',                     'trigger': 'emergency_broadcast'}
        t5 = {'source': 'idle', 'target': 'emergency_message_received',                 'trigger': 'emergency_received'}
        t6 = {'source': 'idle', 'target': 'idle',                                       'trigger': 'delete_stored',         'effect': 'delete_messages'}
        
        #from message received
        t7 = {'source': 'message_received', 'target': 'idle',                           'trigger': 'listen_later',          'effect': 'store_message(*)'}
        t8 = {'source': 'message_received', 'target': 'playback_message',               'trigger': 'listen_to_message'}
        t9 = {'source': 'message_received', 'target': 'emergency_broadcasting',         'trigger': 'emergency_broadcast',   'effect': 'store_message(*)'}
        t10 = {'source': 'message_received', 'target': 'emergency_message_received',     'trigger': 'emergency_received',   'effect': 'store_message(*)'}

        #from playback_stored
        t11 = {'source': 'playback_stored', 'target': 'idle',                           'trigger': 'playback_finished'}
        t12 = {'source': 'playback_stored', 'target': 'emergency_broadcasting',         'trigger': 'emergency_broadcast'}
        t13 = {'source': 'playback_stored', 'target': 'emergency_message_received',     'trigger': 'emergency_received'}
        t14 = {'source': 'playback_stored', 'target': 'idle',                           'trigger': 'abort'}
        
        #from choose_recipients
        t15 = {'source': 'choose_recipients', 'target': 'idle',                         'trigger': 'abort_choosing'}
        t16 = {'source': 'choose_recipients', 'target': 'emergency_broadcasting',       'trigger': 'emergency_broadcast'}
        t17 = {'source': 'choose_recipients', 'target': 'emergency_message_received',   'trigger': 'emergency_received'}
        t18 = {'source': 'choose_recipients', 'target': 'record_message',               'trigger': 'chosen'}   

        # from playback_message
        t19 = {'source': 'playback_message', 'target': 'emergency_broadcasting',        'trigger': 'emergency_broadcast',   'effect': 'store_message(*)'}
        t20 = {'source': 'playback_message', 'target': 'emergency_message_received',    'trigger': 'emergency_received',    'effect': 'store_message(*)'}
        t21 = {'source': 'playback_message', 'target': 'idle',                          'trigger': 'message_played'}
        
        #from emergency_broadcasting 
        t22 = {'source': 'emergency_broadcasting', 'target': 'idle',                    'trigger': 'abort',               'effect': 'stop_timer("t")'}
        t23 = {'source': 'emergency_broadcasting', 'target': 'idle',                    'trigger': 't',                   'effect': 'send_emergency; stop_timer("t")'}
        
        #from emergency_message_received
        t24 = {'source': 'emergency_message_received', 'target': 'idle',                'trigger': 'message_played'}

        #from record_message 
        t25 = {'source': 'record_message', 'target': 'idle',                            'trigger': 'abort_sending'}
        t26 = {'source': 'record_message', 'target': 'idle',                            'trigger': 'done_recording'}
        t27 = {'source': 'record_message', 'target': 'emergency_broadcasting',          'trigger': 'emergency_broadcast'}
        t28 = {'source': 'record_message', 'target': 'emergency_message_received',      'trigger': 'emergency_received'}

        #states 
        idle = {'name': 'idle',
                'entry': 'idle_state'}
        emergency_received = { 'name': 'emergency_message_received',
                            'entry': 'playback_emergency',
                            'message_received': 'defer',
                            'emergency_broadcast': 'defer'}
        emergency_broadcasting = {'name': 'emergency_broadcasting',
                            'entry': 'emergency_state; start_timer("t", 5000)',
                            'message_received': 'defer', 
                            'emergency_received': 'defer'}
        message_received = {'name': 'message_received',
                        'entry': 'prompt_listen',
                        'message_received': 'defer'}
        playback_message = {'name': 'playback_message',
                        'entry': 'playback_message',
                        'message_received': 'defer'}
        playback_stored = {'name': 'playback_stored',
                        'entry': 'listen_stored',
                        'message_received': 'defer'}
        choose_recipients = {'name': 'choose_recipients',
                        'entry': 'prompt_choose', 
                        'message_received': 'defer'}
        record_message = {'name': 'record_message',
                        'entry': 'prompt_record',
                        'message_received': 'defer'}
        
        walkie_stm = stmpy.Machine(name=name, transitions=[t0, t1, t2, t3, t4, t5, t6, t7, t8, t9, t10, t11, t12, t13, t14, t15, t16, t17, t18, t19,
        t20, t21, t22, t23, t24, t25, t26, t27, t28], obj=walkie_logic, states=[idle, emergency_received, emergency_broadcasting,
        message_received, playback_message, playback_stored, choose_recipients, record_message])
        walkie_logic.stm = walkie_stm
        return walkie_stm

    
