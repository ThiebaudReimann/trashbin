import asyncio
from google import genai
import numpy as np
import sounddevice as sd
from google.genai import types
import time

def open_bin(bin: str) -> str:
    """
    Öffnet den passenden Mülleimer.
    Args:
        bin: ["bio", "rest", "papier", "gelb"]
    """
    print(f"🔄 Mülleimer geöffnet: {bin.upper()}")
    
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
client = genai.Client(api_key="AIzaSyCrx8DF7Bh2moDSiNsOUxHJLY3QCyDlOWE", http_options={'api_version': 'v1alpha'})
model_id = "gemini-2.0-flash-exp"

config = types.GenerateContentConfig(
    response_modalities=[types.Modality.AUDIO],
    tools=[bin_tool],
    system_instruction=types.Content(
        parts=[
            types.Part(
                text="Du bist ein smarter Mülleimer. Wenn mir ein Nutzer ein Item nennt, musst du:\n"
                     "1. Sagen, wo es hingehört (Restmüll, Papier, Gelb, Bio)\n"
                     "2. IMMER die Funktion open_bin mit dem passenden Mülleimer aufrufen\n"
                     "   - Verwende 'rest' für Restmüll\n"
                     "   - Verwende 'papier' für Papiermüll\n"
                     "   - Verwende 'gelb' für den gelben Sack/Wertstofftonne\n"
                     "   - Verwende 'bio' für Biomüll\n"
                     "Lehn unpassende Anfragen freundlich ab. Antworte professionell und freundlich. Halte die antwort sehr kurz. Und mache nur relevante Rückfragen."
                     "Pfand sachen sollten beim Pfandautomaten abgegeben werden. Frage bei Flaschen vorher nach.",
            )
        ]
    ),
    
)

#""" tools=[open_bin],
#    automatic_function_calling=types.AutomaticFunctionCallingConfig(
#        disable=False
#    ),"""

async def main():
    async with client.aio.live.connect(model=model_id, config=config) as session:
        while True:
            message = input("User> ")
            if message.lower() == "exit":
                break
            
            # Roh-Stream für Audio-Wiedergabe öffnen
            stream = sd.RawOutputStream(samplerate=24000, channels=1, dtype='int16', blocksize=1024)
            stream.start()
            
            try:
                # Senden der Nachricht
                await session.send(input=message, end_of_turn=True)
                
                # Empfangen und Verarbeiten der Antwort
                got_response = False
                async for response in session.receive():
                    got_response = True
                    
                    
                    # Tool Calls verarbeiten
                    if response.server_content and response.server_content.model_turn:
                        parts = response.server_content.model_turn.parts
                        if parts:
                            for part in parts:
                                
                                # Audio verarbeiten wenn vorhanden
                                if part.inline_data and part.inline_data.data:
                                    pcm_data = part.inline_data.data
                                    audio_array = np.frombuffer(pcm_data, dtype=np.int16)
                                    
                                    # In Blöcken schreiben
                                    chunk_size = 1024
                                    for i in range(0, len(audio_array), chunk_size):
                                        stream.write(audio_array[i:i+chunk_size].tobytes())
                    else:
                        print("🔊 Keine Audio-Daten in der Antwort enthalten")
                        
                    if response.tool_call:
                        
                        # Extract the function call details
                        function_call = response.tool_call.function_calls[0]
                        
                        if (function_call.name == "open_bin"):
                            
                            if "bin" in function_call.args:
                                open_bin(function_call.args["bin"])
                                
                                # Create a proper function response
                                function_response = types.FunctionResponse(
                                    name=function_call.name,
                                    id=function_call.id
                                )
                                await session.send(input=function_response)
                                # Send the content back to the session with the appropriate parameter name
                                
                            
                        
                    
                    # Prüfen ob dies das Ende der Antwort ist
                    
                
                if not got_response:
                    print("⚠ Keine Antwort vom Modell erhalten")
                
                
                    
            except Exception as e:
                print(f"❌ Fehler: {e}")
            finally:
                # Immer sicherstellen, dass der Stream ordnungsgemäß geschlossen wird
                stream.stop()
                stream.close()
                print("🔄 Bereit für neue Eingabe")

if __name__ == "__main__":
    asyncio.run(main())