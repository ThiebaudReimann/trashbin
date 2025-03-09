import asyncio
from google import genai
import numpy as np
import sounddevice as sd
from google.genai import types

def open_bin(bin: str) -> bool:
    """
    Öffnet den passenden Mülleimer.
    Args:
        bin: ["bio", "rest", "papier", "gelb", "none"]
    """
    print(f"🔄 Mülleimer geöffnet: {bin.upper()}")
    return True

# Google Gemini API Client
client = genai.Client(api_key="AIzaSyCrx8DF7Bh2moDSiNsOUxHJLY3QCyDlOWE", http_options={'api_version': 'v1alpha'})
model_id = "gemini-2.0-flash-exp"

config = {
    "response_modalities": ["AUDIO"],
    "system_instruction": types.Content(
        parts=[
            types.Part(
                text="Du bist ein smarter Mülleimer. Wenn ich dir ein Item nenne, sagst du mir, wo es hingehört "
                     "(Restmüll, Papier, Gelb, Bio). Danach öffnest du automatisch den passenden Mülleimer mit `open_bin`. "
                     "Antworte cool und lässig. Lehn unpassende Anfragen freundlich ab."
            )
        ]
    ),
    "tools": [open_bin],
    "speech_config": types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Kore")
        )
    ),
}

async def main():
    async with client.aio.live.connect(model=model_id, config=config) as session:
        while True:
            message = input("User> ")
            if message.lower() == "exit":
                break
            await session.send(input=message, end_of_turn=True)

            # Roh-Stream für Audio-Wiedergabe öffnen
            stream = sd.RawOutputStream(samplerate=24000, channels=1, dtype='int16', blocksize=1024)
            stream.start()

            async for response in session.receive():
                print("Checkpoint 1")
                # 🔹 Falls keine gültige Antwort vorhanden ist, überspringen
                if not response.server_content or not response.server_content.model_turn:
                    print("⚠ Fehler: Keine gültigen Audiodaten erhalten.")
                    continue

                print("Checkpoint 2")
                parts = response.server_content.model_turn.parts
                if not parts or not parts[0].inline_data:
                    print("⚠ Fehler: Keine Inline-Audio-Daten vorhanden.")
                    continue

                print("Checkpoint 3")
                if response.tool_call:
                    print("Tool Call")
                    for function_call in response.tool_call.function_calls:
                        print(f"🔧 Tool-Funktion: {function_call.name}")
                        if function_call.name == "open_bin":
                            print("🔄 Mülleimer öffnen")
                            bin_type = function_call.args.get("bin", "none")
                            open_bin(bin_type)
                    continue  # Schleife weiterführen, damit Audio nicht blockiert wird


                print("Checkpoint 4")
                # 🔹 PCM-Daten für die Audioausgabe verarbeiten
                if parts[0].inline_data.data:
                    pcm_data = parts[0].inline_data.data
                    audio_array = np.frombuffer(pcm_data, dtype=np.int16)

                    # In Blöcken schreiben, falls nötig
                    chunk_size = 1024
                    for i in range(0, len(audio_array), chunk_size):
                        stream.write(audio_array[i:i+chunk_size].tobytes())



            print("🔴 Gespräch beendet.")
            stream.stop()
            stream.close()

if __name__ == "__main__":
    asyncio.run(main())
