import re
import subprocess

from scipy.io import wavfile
import wave
import asyncio
import glob
import time
import struct
import random
import aiohttp
import json
import os.path
from os import system
from enum import Enum
from scramjet.streams import Stream
from serial_asyncio import open_serial_connection

# Regular expression to find MCU devices with UART
DEVICE_REGEXP = '/dev/ttyAC?[0-9]*'

# Single chunk size for read. In bytes.
CHUNK_SIZE = 128

# UART baudrate
BAUDRATE = 115200

# List of required MCUs names
REQUIRED_MCU_NAMES = ['PicoMic#000', 'PicoLED#000']

TEST_DURATION_IN_SEC = 900

RECORDING_TIME = 1

FRAME_RATE = 8000

STH_INSTANCE_INPUT_URL = ""

STH_INSTANCE_OUTPUT_URL = ""


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


def find_usb_devices_serials():
    df = subprocess.check_output(["lsusb", "-v"], stderr=subprocess.DEVNULL)
    devices = []

    for i in df.split(b'\n'):
        if not i:
            continue

        if i.find(b'iSerial') == -1:
            continue

        serial_line = i.decode("utf-8").split()
        if len(serial_line) >= 3:
            devices.append(serial_line[2])
    return devices


def has_required_usb_devices(serials: [str]):
    devices = find_usb_devices_serials()
    for serial in serials:
        if not any(serial == device for device in devices):
            print(f'Device id not found {serial}')
            return False

    return True


def parse_context(context):
    context = json.loads(json.dumps(context.config))
    serials = []
    devices = []
    elfs = []
    post_data_url = context["post_data_url"] or ""
    get_data_url = context["get_data_url"] or ""
    elfs_folder = os.getcwd() + "/elfs/"
    for device in context["devices"]:
        if device["name"] and device["probe"] and device["elf"]:
            serials.append(device["probe"])
            elf_path = elfs_folder + device["elf"]
            elfs.append(elf_path)
            device["elf"] = elf_path
            devices.append(device)
            print(device)

    return serials, devices, elfs, post_data_url, get_data_url


def has_required_elf_files(elfs: [str]):
    for elf in elfs:
        if not os.path.isfile(elf):
            print(f'Unable to find: {elf}')
            return False
    return True


def program_devices(devices):
    for device in devices:

        args = ['sudo', 'openocd', '-f', 'interface/cmsis-dap.cfg', '-f', 'target/rp2040.cfg',
                '-c', f'adapter serial {device["probe"]}', '-c', 'adapter speed 5000',
                '-c', f'program {device["elf"]} verify reset exit']

        try:
            df = subprocess.run(args, capture_output=True, text=True)
            print(df.stdout)
            print(df.stderr)
            df.check_returncode()
            print(f'{os.path.basename(device["elf"])} successfully programmed on MCU with probe {device["probe"]}')

        except subprocess.CalledProcessError as e:
            print(f'{os.path.basename(device["elf"])} failed programing on MCU with probe {device["probe"]}')
            print(f'Error: {e}')
            return False
        time.sleep(1)
    return True


async def run(context, input, *args) -> Stream:
    serials, devices, elfs, post_data_url, get_data_url = parse_context(context)
    global STH_INSTANCE_INPUT_URL
    global STH_INSTANCE_OUTPUT_URL
    STH_INSTANCE_INPUT_URL = post_data_url
    STH_INSTANCE_OUTPUT_URL = get_data_url

    print(devices)

    stream = Stream()

    if (not has_required_usb_devices(serials) or not has_required_elf_files(elfs)
            or not post_data_url or not get_data_url):
        print("Missing required context data")
        stream.end()
        return stream

    print("Required devices found")
    if not program_devices(devices):
        print("Failed programming devices")
        stream.end()
        return stream

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


class Context:
    def __init__(self):
        self.config = {
            "devices": [
                {
                    "name": "PicoMic",  # 1
                    "probe": "E6616407E3515229",
                    "elf": "zephyr_mic.elf"
                    # "elf": "zephyr_blinky.elf"
                },
                {
                    "name": "PicoLED",  # 2
                    "probe": "E6616407E3542629",
                    "elf": "zephyr_led.elf"
                    # "elf": "zephyr_blinky.elf"
                }
            ],
            "post_data_url": "some_fake_url",
            "get_data_url": "some_fake_url"
            }


test_context = Context()


async def run_without_sth():
    async for chunk in await run(context=test_context, input=Stream()):
        print(chunk) 

if __name__ == "__main__":
    asyncio.run(run_without_sth())