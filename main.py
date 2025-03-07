import asyncio
from google import genai
import numpy as np
import sounddevice as sd

# Google Gemini API Client
client = genai.Client(api_key="AIzaSyCrx8DF7Bh2moDSiNsOUxHJLY3QCyDlOWE", http_options={'api_version': 'v1alpha'})
model_id = "gemini-2.0-flash-exp"
config = {
    "response_modalities": ["AUDIO"],
}

async def main():
    async with client.aio.live.connect(model=model_id, config=config) as session:
        while True:
            message = input("User> ")
            if message.lower() == "exit":
                break
            await session.send(input=message, end_of_turn=True)

            # Roh-Stream für Audio-Wiedergabe öffnen
            stream = sd.RawOutputStream(samplerate=24000, channels=1, dtype='int16')
            stream.start()

            async for response in session.receive():
                if not response.server_content or not response.server_content.model_turn:
                    #print("Fehler: Keine gültigen Audiodaten erhalten.")
                    continue

                parts = response.server_content.model_turn.parts
                if not parts or not parts[0].inline_data:
                    #print("Fehler: Keine Inline-Audio-Daten vorhanden.")
                    continue

                if parts[0].inline_data.data:
                    pcm_data = parts[0].inline_data.data  # PCM-Daten direkt verwenden

                    stream.write(pcm_data)  # Direkt an den Sound-Stream senden

            stream.stop()
            stream.close()

if __name__ == "__main__":
    asyncio.run(main())
