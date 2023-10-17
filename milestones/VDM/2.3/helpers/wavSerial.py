import wave
import serial
import struct
import noisereduce as nr
from scipy.io import wavfile
import time

print("WavSerial:")

def turnMicOn(s: serial):
     s.write(struct.pack("!BHb", 6, 1, 1))
    
def turnMicOff(s:serial):
    s.write(struct.pack("!BHb", 6, 1, 0))

def turnLedOn(s: serial):
     s.write(struct.pack("!BHb", 6, 1, 3))
    
def turnLedOff(s:serial):
    s.write(struct.pack("!BHb", 6, 1, 2))

def openAndSetInputFile(filePath: str, frameRate: int):
    wavWrite = wave.open(filePath, "wb")
    wavWrite.setnchannels(1)
    wavWrite.setsampwidth(2)
    wavWrite.setframerate(frameRate)
    wavWrite.setcomptype('NONE', 'not compressed')
    return wavWrite

def gatherAdcSamples(s:serial, framesCount: int, outputFile: wave.Wave_write): 
    no_frames = 0
    previousFrame = 0

    while(True):
        header = s.read(1)
        if(header == b''):
                print("empty read")
                continue
        if(header != b'\x07'): 
            print(f"Unknown cmd: {header}")
            continue
        sizeRaw = s.read(2)
        size = struct.unpack("!H", sizeRaw)[0]
        data = s.read(size)
        frame = struct.unpack("!h", data)[0]
        fakeFrame = int((previousFrame + frame)/2)
        outputFile.writeframes(struct.pack("!h", fakeFrame))
        previousFrame = frame
        outputFile.writeframes(data)
        no_frames += 1
        print(f"Frame val: {frame} number: {no_frames}")
        if(no_frames >= framesCount): break
    
def denoise(inputFilename: str, noiseFilename: str, outputFilename: str):
    noiseRate, noiseData = wavfile.read(noiseFilename)
    rate, data = wavfile.read(inputFilename)
    reduced_noise = nr.reduce_noise(y=data, sr=rate, y_noise=noiseData, time_constant_s= 1)
    wavfile.write(outputFilename, rate, reduced_noise)

t0 = time.time()
frameRate = 8000
recordingTimeSec = 3
dir = "./milestones/VDM/2.3/helpers/"
inputFilePath = dir + "testSound.wav"
serialDevice = "/dev/ttyACM0"
wavWrite = openAndSetInputFile(inputFilePath, 2* frameRate)
s = serial.Serial(serialDevice, baudrate=115200, timeout=1)

turnMicOn(s)
gatherAdcSamples(s, frameRate * recordingTimeSec, wavWrite)
turnMicOff(s)

wavWrite.close()
t1 = time.time()
noiseFilePath = dir + "noise.wav"
outputFilePath = dir + "output.wav"
denoise(inputFilePath, noiseFilePath, outputFilePath)
t2 = time.time()

print(f"Time total: {round((t2 - t0)*1000)}ms")
print(f"Time acquisition: {(round(t1 - t0)*1000)}ms")
print(f"Time denoise: {round((t2 - t1)*1000)}ms")