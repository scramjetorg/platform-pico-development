provides = {
   'contentType': 'application/octet-stream'
}

from scipy.io import wavfile
import string
import wave
import asyncio
import glob
import time
import struct
import random
import pickle 
import aiohttp


import json
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

TEST_DURATION_IN_SEC = 900

RECORDING_TIME = 1

FRAME_RATE = 8000

TEMP_DIR = "/tmp/"

NOISE_FILENAME_PATH = '/tmp/noise.wav'

HOST = "192.168.0.5"

STH_INSTANCE_INPUT_URL = f"http://{HOST}:8000/api/v1/instance/2bf167a6-a9e4-4b78-b9bb-046c52b570d7/input"

STH_INSTANCE_OUTPUT_URL = f"http://{HOST}:8000/api/v1/instance/2bf167a6-a9e4-4b78-b9bb-046c52b570d7/output"

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
        dev['writer'].write(struct.pack("!BHb", 6, 1, 2))
        await dev['writer'].drain()

    @staticmethod
    async def turnLedOff(dev):
        dev['writer'].write(struct.pack("!BHb", 6, 1, 3))
        await dev['writer'].drain()


class DataProcessing:

    async def get_data_over_http(self, url):
        chunk = bytes()
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as resp:
                    async for data, endOfChunk in resp.content.iter_chunks():
                        chunk += data
                        if endOfChunk:
                            break
            except Exception as e:
                return ''                
        return chunk
                
    async def read_adc(self, dev: dict, stop_event: asyncio.Event, captured_audio: asyncio.Queue):
        await Peripherals.turnMicOn(dev)

        while not stop_event.is_set():
            outputDataRAW = []
            await self.gatherAdcSamples(dev, FRAME_RATE * RECORDING_TIME, outputDataRAW)
            await captured_audio.put(outputDataRAW)
        await Peripherals.turnMicOff(dev)

    async def _prepare_data(self, stop_event, captured_audio):
        LIST_CHUNK_SIZE = 1024
        while not stop_event.is_set():
            audio_data = await captured_audio.get()

            # name = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(8))
            # fd = self.openAndSetInputFile(f'/tmp/dump_rpi4_{name}.wav',16000)
            # for frame in audio_data:
            #     fd.writeframes(struct.pack("!h", frame))
            # fd.close()
            
            yield (json.dumps({"cmd": "1337"}) + '\n').encode(encoding="utf-8")
            yield (json.dumps({"cmd": len(audio_data)}) + '\n').encode(encoding="utf-8")
            
            for i in range(0,len(audio_data),LIST_CHUNK_SIZE):
                sub = audio_data[i:i+LIST_CHUNK_SIZE]
                yield (json.dumps({"cmd": [int(x) for x in sub]}) + '\n').encode(encoding="utf-8")
            captured_audio.task_done()            
            await asyncio.sleep(0)

    async def only_send(self, stop_event: asyncio.Event, session: aiohttp.ClientSession, captured_audio: asyncio.Queue):        
        async with session.post(STH_INSTANCE_INPUT_URL, data=self._prepare_data(stop_event, captured_audio), headers={'content-type': 'text/plain'}) as resp:
            await resp.text()

    
    async def manage_led(self, dev: dict, stop_event: asyncio.Event, dp):
        while not stop_event.is_set():
            try:
                response = await asyncio.wait_for(dp.get_data_over_http(STH_INSTANCE_OUTPUT_URL),2)
            except asyncio.TimeoutError:
                await asyncio.sleep(0)
                continue

            detected_words = response.decode().split('\n')[:-1]
            print(f'Detected words: {detected_words}')

            if 'on' in detected_words:
                await Peripherals.turnLedOn(dev)
                await asyncio.sleep(0.5)
                print("LED is ON")

            if 'off' in detected_words:
                await Peripherals.turnLedOff(dev)
                await asyncio.sleep(0.5)
                print("LED is OFF")     

    def openAndSetInputFile(self, filePath: str, frameRate: int):
        wavWrite = wave.open(filePath, "wb")
        wavWrite.setnchannels(1)
        wavWrite.setsampwidth(2)
        wavWrite.setframerate(frameRate)
        wavWrite.setcomptype('NONE', 'not compressed')
        return wavWrite

    async def gatherAdcSamples(self, dev, framesCount: int, outputDataRAW: list): 
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
                #print('Wrong frame size, use previous again')
                frame = previousFrame
                fakeFrame = frame

            outputDataRAW.append(fakeFrame)
            previousFrame = frame
            outputDataRAW.append(frame)

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

async def _watchdog(manager, stream, session, duration):

    manager.start_event.set()
    await asyncio.sleep(duration)
    manager.stop_event.set()
    await session.close()
    stream.end()

async def run(context, input, *args) -> Stream:

    stream = Stream()
    manager = MCUManager(REQUIRED_MCU_NAMES)
    dp = DataProcessing()
    captured_audio = asyncio.Queue()
    stop_event = asyncio.Event()
    session = aiohttp.ClientSession()

    await manager.prepare_connections()

    for dev in manager.mcu:

        if dev['name'] == 'PicoMic#000':
            asyncio.create_task(dp.read_adc(dev, stop_event, captured_audio))
            
            asyncio.create_task(dp.only_send(stop_event, session, captured_audio))

        if dev['name'] == 'PicoLed#000':
            await Peripherals.turnLedOn(dev)
            await asyncio.sleep(0.5)
            print("LED is ON")

            asyncio.create_task(dp.manage_led(dev, stop_event, dp))
    
    asyncio.create_task(_watchdog(manager, stream, session, TEST_DURATION_IN_SEC))
    
    return stream

async def run_without_sth():
    async for chunk in await run(context=None, input=Stream()):
        print(chunk) 

if __name__ == "__main__":
    asyncio.run(run_without_sth())