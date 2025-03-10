import asyncio
from google import genai
import numpy as np
import sounddevice as sd
from google.genai import types
from dotenv import load_dotenv
import os
import webrtcvad
import queue
import threading
import signal
import bin

load_dotenv()

bin_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="open_bin",
            description="Öffnet den passenden Mülleimer.",
            parameters=types.Schema(
                properties={
                    "bin": types.Schema(
                        type="string",
                        enum=["bio", "rest", "papier", "gelb"]
                    )
                },
                type="OBJECT"

            )
        )
    ]
)

# Google Gemini API Client
client = genai.Client(api_key=os.getenv("GENAI_API_KEY"), http_options={'api_version': 'v1alpha'})
model_id = "gemini-2.0-flash-exp"

config = types.GenerateContentConfig(
    response_modalities=[types.Modality.AUDIO],
    tools=[bin_tool],
    system_instruction=types.Content(
        parts=[
            types.Part(
                text="""
                Du bist ein smarter Mülleimer, entwickelt von Thiébaud Reimann. Wenn ein Nutzer ein Item nennt, musst du:
                    1. Sagen, wo es hingehört (Restmüll, Papier, Gelb, Bio)
                    2. Immer die Funktion open_bin mit dem passenden Mülleimer aufrufen:
                     - 'rest' für Restmüll
                     - 'papier' für Papier
                     - 'gelb' für den gelben Sack
                     - 'bio' für Biomüll
                Lehne unpassende Anfragen freundlich ab.
                Don't output audio of function calls or response.
                Weise bei Pfandflaschen darauf hin das sie in den Pfandautomaten kommen.
                Bei direkten anforderungen wie "Öffne den Restmüll" öffne den Mülleimer und antworte nur mit "Okay".
                """
            )
        ]
    ),
)


SAMPLE_RATE = 16000
FRAME_DURATION = 30  # ms
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION / 1000)
VAD_AGGRESSIVENESS = 0  # 0-3, higher is more aggressive

# Global variables for audio processing
audio_queue = queue.Queue()
is_speaking = False
should_stop = False
is_playing = False

def audio_callback(indata, frames, time, status):
    if status:
        print(f"Status: {status}")
    audio_queue.put(bytes(indata))

class VoiceDetector:
    def __init__(self):
        self.vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)
        self.buffer = b''
        self.speaking_frames = 0
        self.silent_frames = 0
        self.is_speaking = False

    def process_audio(self, audio_chunk):
        self.buffer += audio_chunk
        while len(self.buffer) >= FRAME_SIZE * 2:  # *2 because int16
            frame = self.buffer[:FRAME_SIZE * 2]
            self.buffer = self.buffer[FRAME_SIZE * 2:]

            try:
                is_speech = self.vad.is_speech(frame, SAMPLE_RATE)
            except:
                continue

            if is_speech:
                self.speaking_frames += 1
                self.silent_frames = 0
            else:
                self.silent_frames += 1
                self.speaking_frames = 0

            # State machine for speech detection
            if not self.is_speaking and self.speaking_frames > 3:  # Start of speech
                self.is_speaking = True
                return True, frame
            elif self.is_speaking and self.silent_frames > 10:  # End of speech
                self.is_speaking = False
                return False, frame
            elif self.is_speaking:  # Continuous speech
                return True, frame

            return False, frame
        return False, b''

    def reset(self):
        self.buffer = b''
        self.speaking_frames = 0
        self.silent_frames = 0
        self.is_speaking = False

async def process_audio_stream(session):
    global is_playing
    voice_detector = VoiceDetector()
    accumulated_audio = b''

    with sd.InputStream(channels=1,
                       samplerate=SAMPLE_RATE,
                       dtype=np.int16,
                       callback=audio_callback):
        print("🎤 Listening... (Press Ctrl+C to stop)")

        while not should_stop:
            if not audio_queue.empty() and not is_playing:  # Only process input when not playing response
                audio_chunk = audio_queue.get()
                is_speech, frame = voice_detector.process_audio(audio_chunk)

                if is_speech:
                    accumulated_audio += frame
                    if len(accumulated_audio) >= SAMPLE_RATE:  # Send every 1 second of audio
                        try:
                            await session.send(
                                input=types.LiveClientRealtimeInput(
                                    media_chunks=[
                                        types.Blob(
                                            mime_type="audio/pcm;rate=16000",
                                            data=accumulated_audio
                                        )
                                    ]
                                ),
                                end_of_turn=False
                            )
                            accumulated_audio = b''
                        except Exception as e:
                            print(f"Error sending audio: {e}")

                elif voice_detector.is_speaking == False and len(accumulated_audio) > 0:
                    # Send final chunk and end turn
                    try:
                        await session.send(
                            input=types.LiveClientRealtimeInput(
                                media_chunks=[
                                    types.Blob(
                                        mime_type="audio/pcm;rate=16000",
                                        data=accumulated_audio
                                    )
                                ]
                            ),
                            end_of_turn=True
                        )
                        accumulated_audio = b''
                        voice_detector.reset()  # Reset detector for next utterance
                    except Exception as e:
                        print(f"Error sending final audio: {e}")

            await asyncio.sleep(0.01)

async def handle_responses(session):
    global is_playing
    playback_stream = sd.RawOutputStream(
        samplerate=24000,
        channels=1,
        dtype='int16',
        blocksize=1024
    )
    playback_stream.start()

    try:
        while not should_stop:
            async for response in session.receive():

                if response.tool_call:

                    # Extract the function call details
                    function_call = response.tool_call.function_calls[0]

                    if (function_call.name == "open_bin"):

                        if "bin" in function_call.args:
                            bin.open_bin(bin.binTypes.from_string(function_call.args["bin"]))

                            # Create a proper function response
                            function_response = types.FunctionResponse(
                                name=function_call.name,
                                id=function_call.id
                            )

                            await session.send(input=function_response)
                            # Send the content back to the session with the appropriate parameter name
                            continue


                if response.server_content and response.server_content.model_turn:
                    is_playing = True  # Start of response playback
                    parts = response.server_content.model_turn.parts
                    if parts:
                        for part in parts:
                            if part.inline_data and part.inline_data.data:
                                pcm_data = part.inline_data.data
                                audio_array = np.frombuffer(pcm_data, dtype=np.int16)

                                chunk_size = 1024
                                for i in range(0, len(audio_array), chunk_size):
                                    if should_stop:
                                        break
                                    playback_stream.write(audio_array[i:i+chunk_size].tobytes())
                    is_playing = False  # End of response playback

                    # Clear the audio queue after playing response
                    while not audio_queue.empty():
                        audio_queue.get()

    except Exception as e:
        print(f"Error in response handling: {e}")
    finally:
        playback_stream.stop()
        playback_stream.close()

def signal_handler(sig, frame):
    global should_stop
    print("\nStopping...")
    should_stop = True

async def main():
    global should_stop

    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)

    while True:  # Main conversation loop
        try:
            should_stop = False
            print("\nStarting new conversation session...")

            async with client.aio.live.connect(model=model_id, config=config) as session:
                # Create tasks for audio processing and response handling
                audio_task = asyncio.create_task(process_audio_stream(session))
                response_task = asyncio.create_task(handle_responses(session))

                # Wait for both tasks
                await asyncio.gather(audio_task, response_task)

                if should_stop:
                    user_input = input("\nWould you like to start a new conversation? (y/n): ")
                    if user_input.lower() != 'y':
                        break

        except Exception as e:
            print(f"Error in conversation session: {e}")
            user_input = input("\nWould you like to restart the conversation? (y/n): ")
            if user_input.lower() != 'y':
                break

    print("Goodbye!")

if __name__ == "__main__":
    asyncio.run(main())
