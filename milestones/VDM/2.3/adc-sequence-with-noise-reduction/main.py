provides = {
   'contentType': 'application/octet-stream'
}

from scipy.io import wavfile
import noisereduce as nr
import string
import wave
import asyncio
import glob
import time
import struct
import random
import pickle 

from os import system
from enum import Enum
from scramjet.streams import Stream
from serial_asyncio import open_serial_connection

#Regular expression to find MCU devices with UART
DEVICE_REGEXP = '/dev/ttyAC?[0-9]*'

#Single chunk size for read. In bytes.
CHUNK_SIZE = 128

#UART baudrate
BAUDRATE  = 115200 

#List of required MCUs names
REQUIRED_MCU_NAMES = ['PicoMic#000', 'PicoLED#000']

TEST_DURATION_IN_SEC = 30

RECORDING_TIME = 3

FRAME_RATE = 8000

TEMP_DIR = "/tmp/"

NOISE_FILENAME_PATH = '/tmp/noise.wav'

class ScramjetMCUProtocol:

    class _Commands(Enum):
        Ping = 0,
        Pong = 1,
        NameRequest = 2,
        NameResponse = 3,
        Input = 6,
        Output = 7,
        Error = 8,
        Undefined = 9 

    @staticmethod
    async def send_request(dev, command, param=None):
        
        writer = dev["writer"]

        # requests with 2-byte param
        if command in [ScramjetMCUProtocol._Commands.Ping]:
            writer.write(struct.pack("!BH",command.value[0], param))
            await writer.drain()

        # requests without 2-byte param
        if command in [ScramjetMCUProtocol._Commands.NameRequest]:
            writer.write(struct.pack("!B", command.value[0]))
            await writer.drain()

    @staticmethod
    async def get_response(dev):
        
        reader = dev['reader']
        try:
            command = ScramjetMCUProtocol._Commands(struct.unpack("!B", await asyncio.wait_for(reader.read(1),1)))
        except asyncio.TimeoutError:
            return ScramjetMCUProtocol._Commands.Error, 'Command waiting timeout'

        # response without 2-byte param, *without* size and payload
        if command in [ScramjetMCUProtocol._Commands.Pong]:
            return command, struct.unpack("!H",await reader.read(2))[0]

        # response without 2-byte param, *with* size and payload
        if command in [ScramjetMCUProtocol._Commands.NameResponse, ScramjetMCUProtocol._Commands.Error]:
            size = struct.unpack("!H",await reader.read(2))[0]
            payload = (struct.unpack( ("!%ds" % size), await reader.read(size))[0]).decode(encoding="ascii")
            return command, payload

class Peripherals:
    @staticmethod
    async def turnMicOn(dev):
        dev['writer'].write(struct.pack("!BHb", 6, 1, 1))
        await dev['writer'].drain()

    @staticmethod
    async def turnMicOff(dev):
        dev['writer'].write(struct.pack("!BHb", 6, 1, 0))
        await dev['writer'].drain()

    @staticmethod
    async def turnLedOn(dev):
        dev['writer'].write(struct.pack("!BHb", 6, 1, 3))
        await dev['writer'].drain()

    @staticmethod
    async def turnLedOff(dev):
        dev['writer'].write(struct.pack("!BHb", 6, 1, 2))
        await dev['writer'].drain()


class DataProcessing:

    async def read_adc(self, dev: dict, stop_event: asyncio.Event, saved_files: list):
        await Peripherals.turnMicOn(dev)

        while not stop_event.is_set():
            filename = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8)) + ".wav"
            inputFilePath = TEMP_DIR + filename
            wavWrite = self.openAndSetInputFile(inputFilePath, 2 * FRAME_RATE)
            await self.gatherAdcSamples(dev, FRAME_RATE * RECORDING_TIME, wavWrite)
            wavWrite.close()
            await saved_files.put(filename)
        await Peripherals.turnMicOff(dev)

    async def denoise_and_send(self, stop_event: asyncio.Event, captured_files:list, stream: Stream):
        noiseRate, noiseData = wavfile.read(NOISE_FILENAME_PATH)

        while not stop_event.is_set():
            try:
                captured_file = await asyncio.wait_for(captured_files.get(),2)
            except asyncio.TimeoutError:
                await asyncio.sleep(0)
                continue

            rate, data = wavfile.read(TEMP_DIR + captured_file)
            reduced_noise = nr.reduce_noise(y=data, sr=rate, y_noise=noiseData, time_constant_s= 1)
            #wavfile.write(outputFilename, rate, reduced_noise)
            stream.write('1337')
            serialized = pickle.dumps(reduced_noise)
            stream.write(len(serialized))
            stream.write(serialized)
            await captured_files.task_done()
    
    async def only_send(self, stop_event: asyncio.Event, captured_files: list, stream: Stream):
        while not stop_event.is_set():
            try:
                captured_file = await asyncio.wait_for(captured_files.get(),2)
            except asyncio.TimeoutError:
                await asyncio.sleep(0)
                continue

            rate, data = wavfile.read(TEMP_DIR + captured_file)
            #wavfile.write(outputFilename, rate, reduced_noise)
            stream.write('1337')
            serialized = pickle.dumps(data)
            stream.write(len(serialized))
            stream.write(serialized)
            await captured_files.task_done()

    async def manage_led(self, dev: dict, stop_event: asyncio.Event, input: Stream):
        while not stop_event.is_set():
            try:
                response = await asyncio.wait_for(input.read(),2)
            except asyncio.TimeoutError:
                await asyncio.sleep(0)
                continue

            if response == 'On':
                await Peripherals.turnLedOn(dev)

            if response == 'Off':
                await Peripherals.turnLedOff(dev)

    def openAndSetInputFile(self, filePath: str, frameRate: int):
        wavWrite = wave.open(filePath, "wb")
        wavWrite.setnchannels(1)
        wavWrite.setsampwidth(2)
        wavWrite.setframerate(frameRate)
        wavWrite.setcomptype('NONE', 'not compressed')
        return wavWrite

    async def gatherAdcSamples(self, dev, framesCount: int, outputFile: wave.Wave_write): 
        no_frames = 0
        previousFrame = 0
        s = dev['reader']

        while (True):
            header = await s.read(1)
            if (header == b''):
                continue
            if (header != b'\x07'):
                continue

            try:
                sizeRaw = await s.read(2)
                size = struct.unpack("!H", sizeRaw)[0]
                data = await s.read(size)
                frame = struct.unpack("!h", data)[0]
                fakeFrame = int((previousFrame + frame)/2)

            except struct.error:
                print('Wrong frame size, use previous again')
                frame = previousFrame
                fakeFrame = frame

            outputFile.writeframes(struct.pack("!h", fakeFrame))
            previousFrame = frame
            outputFile.writeframes(data)
            no_frames += 1
            if (no_frames >= framesCount): break

class MCUManager:

    async def ping_device(self, dev):
        
        await self.flush_mcu_buffers(dev)

        ping_request = random.randint(0, 10)
        
        await ScramjetMCUProtocol.send_request(dev,ScramjetMCUProtocol._Commands.Ping,ping_request)
        
        command, ping_response = await ScramjetMCUProtocol.get_response(dev)

        if command == ScramjetMCUProtocol._Commands.Pong and ping_request == ping_response:
            print(f'Device {dev["tty"]} OK')
            return True 
                     
        print(f'Ping failed. Device {dev["tty"]} returned an error: {ping_response}')
        return False


    async def identify_device(self, dev):
        await ScramjetMCUProtocol.send_request(dev,ScramjetMCUProtocol._Commands.NameRequest)
            
        command, name = await ScramjetMCUProtocol.get_response(dev)
        
        if command == ScramjetMCUProtocol._Commands.NameResponse:
            dev['name'] = name
            self.mcu.append(dev)
            print(f'Device {dev["tty"]} identified as {dev["name"]}')
            return True

        print(f'Identify failed. Device {dev["tty"]} returned an error: {name}')
        return False

    async def close_connections(self):
        for dev in self.mcu:

            dev['writer'].close()
            await dev['writer'].wait_closed()
            print(f'Connection with device {dev["tty"]} closed')

    async def prepare_connections(self):

        # Kill descriptors, sometimes it helps :D
        for port in glob.glob(DEVICE_REGEXP):
            system(f'fuser -k {port}')

        time.sleep(1)

        for port in glob.glob(DEVICE_REGEXP):
            reader, writer = await open_serial_connection(url=port, baudrate=BAUDRATE)

            dev = {'reader': reader, 'writer': writer, 'tty' : port}

            if not await self.ping_device(dev):
                continue

            if not await self.identify_device(dev):
                continue

    def __init__(self, expected_mcus):

        self.stop_event = asyncio.Event()
        self.start_event = asyncio.Event()
        self.start_time = None
        self.expected_mcus = expected_mcus

        self.mcu = []
        self.throughput = {}

    @property
    def undetected_devices(self):
        return self.expected_mcus

    async def flush_mcu_buffers(self, dev, timeout=1):
        while True:
            try:
                chunk = await asyncio.wait_for(dev['reader'].read(CHUNK_SIZE),timeout)
                if not chunk:
                    break
            except asyncio.TimeoutError:
                break

async def _watchdog(manager, stream, duration):

    manager.start_event.set()
    await asyncio.sleep(duration)
    manager.stop_event.set()
    stream.end()

async def run(context, input, *args) -> Stream:

    stream = Stream()
    manager = MCUManager(REQUIRED_MCU_NAMES)
    dp = DataProcessing()
    captured_files = asyncio.Queue()
    stop_event = asyncio.Event()

    await manager.prepare_connections()

    for dev in manager.mcu:

        if dev['name'] == 'PicoMic#000':
            asyncio.create_task(dp.read_adc(dev, stop_event, captured_files))
            #asyncio.create_task(dp.denoise_and_send(stop_event, captured_files, stream))
            asyncio.create_task(dp.only_send(stop_event, captured_files, stream))

        if dev['name'] == 'PicoLed#000':
            asyncio.create_task(dp.manage_led(dev, stop_event, input))
    
    asyncio.create_task(_watchdog(manager, stream, TEST_DURATION_IN_SEC))
    
    return stream

async def run_without_sth():
    async for chunk in await run(context=None,input=None):
        print(chunk) 

if __name__ == "__main__":
    asyncio.run(run_without_sth())