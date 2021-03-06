from stmpy import Machine, Driver
from os import system
import os
import time

import pyaudio
import wave
import pyttsx3

#standard values
FILENAME = "output_tmp.wav"
CHANNELS = 2
SAMPLEFORMAT = pyaudio.paInt16
CHUNK = 1024
SAMPLEFREQUENCY = 44100        
SAMPLEWIDTH = pyaudio.get_sample_size(pyaudio.paInt16)
latest_samples = []
class Recorder:
    def __init__(self):
        self.recording = False
        self.chunk = 1024  # Record in chunks of 1024 samples
        self.sample_format = pyaudio.paInt16  # 16 bits per sample
        self.channels = 2
        self.fs = 44100  # Record at 44100 samples per second
        self.p = pyaudio.PyAudio()
        self.frames = []
        self.record_running = False

    def record(self):
        print("Recording...")
        self.finished_recording = True
        stream = self.p.open(format=self.sample_format,
                channels=self.channels,
                rate=self.fs,
                frames_per_buffer=self.chunk,
                input=True)
        self.recording = True
        self.frames = []
        while self.recording:
            data = stream.read(CHUNK)
            self.frames.append(data)
        print("done recording")
        # Stop and close the stream
        stream.stop_stream()
        stream.close()
        # Terminate the PortAudio interface
        self.p.terminate()
        
        
    def stop_recording(self):
        print("stop")
        self.recording = False


    def getFrames(self):
        return self.frames


def process_audio(data, filename = FILENAME):
        """ Saves the recorded samples stored in data in a .wav file with the name filename
            Default filename is used for just temporaray storage, will be overwritten
            next time the funtion is called without a filename parameter  """
        wf = wave.open(filename, 'wb')
        wf.setnchannels(CHANNELS)
        p = pyaudio.PyAudio()
        wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
        wf.setframerate(SAMPLEFREQUENCY)
        wf.writeframes(data)
        wf.close()
        
class Player:
    def __init__(self):
        self.playing = True        
    def play(self, filename): 
        # Open the sound file 
        wf = wave.open(filename, 'rb')

        # Create an interface to PortAudio
        p = pyaudio.PyAudio()

        # Open a .Stream object to write the WAV file to
        # 'output = True' indicates that the sound will be played rather than recorded
        stream = p.open(format = p.get_format_from_width(wf.getsampwidth()),
                        channels = wf.getnchannels(),
                        rate = wf.getframerate(),
                        output = True)

        # Read data in chunks
        data = wf.readframes(CHUNK)
        self.playing = True
        # Play the sound by writing the audio data to the stream
        while (data != b'') and self.playing:
            stream.write(data)
            data = wf.readframes(CHUNK)
        # Close and terminate the stream
        stream.close()
        p.terminate()

    def stop_playing(self):
        self.playing = False

class Speaker:
    def __init__(self):
        self.engine = pyttsx3.init()
        engine = pyttsx3.init()

    def speak(self, text):
        self.engine.say(text)
        self.engine.runAndWait()

class AudioHelper:
    def __init__(self):


        self.recorder = Recorder()
                
        t0_r = {'source': 'initial',                                    'target': 'ready'}
        t1_r = {'trigger': 'start_recording',   'source': 'ready',      'target': 'recording'}
        t2_r = {'trigger': 'done',              'source': 'recording',  'target': 'ready'}
        s_ready = {'name': 'ready'}
        s_recording = {'name': 'recording', 'do': 'record()', "stop" : "stop_recording()"}
        self.stm_recording = Machine(name='stm_recording', transitions=[t0_r, t1_r, t2_r], states=[s_ready, s_recording], obj=self.recorder)
        self.recorder.stm = self.stm_recording

        self.speaker = Speaker()
        t0_s = {'source': 'initial',                            'target': 'ready'}
        t1_s = {'trigger': 'speak',     'source': 'ready',      'target': 'speaking'}
        t2_s = {'trigger': 'done',      'source': 'speaking',   'target': 'ready'}


        s1_s = {'name': 'speaking', 'do': 'speak(*)', 'speak': 'defer'}

        self.stm_speaker = Machine(name='stm_speaker', transitions=[t0_s, t1_s, t2_s], states=[s1_s], obj=self.speaker)
        self.speaker.stm = self.stm_speaker

        self.driver = Driver()
        self.driver.add_machine(self.stm_recording)
        self.driver.add_machine(self.stm_speaker)
        self.driver.start()
        print('Audio Module ready')

    def play_audio_noStm(self, filename): 
        # Open the sound file 
        wf = wave.open(filename, 'rb')

        # Create an interface to PortAudio
        p = pyaudio.PyAudio()

        # Open a .Stream object to write the WAV file to
        # 'output = True' indicates that the sound will be played rather than recorded
        stream = p.open(format = p.get_format_from_width(wf.getsampwidth()),
                        channels = wf.getnchannels(),
                        rate = wf.getframerate(),
                        output = True)

        # Read data in chunks
        data = wf.readframes(CHUNK)
        #self.playing = True
        # Play the sound by writing the audio data to the stream
        while (data != b''): #and self.playing:
            stream.write(data)
            data = wf.readframes(CHUNK)
        # Close and terminate the stream
        stream.close()
        p.terminate()
    
    def start_recording(self):
        #print("driver started")
        self.last_record = []
        self.stm_recording.send('start_recording')
        
    def stop_recording(self):
        self.stm_recording.send("stop")

    def get_tmp_filename(self):
        #Returns the filename that is used for temp storage
        return FILENAME

    def get_recorded_samples(self):
        return b''.join(self.stm_recording._obj.getFrames())
    
    def text_to_speech(self, text):
        self.stm_speaker.send('speak', args=[text])
