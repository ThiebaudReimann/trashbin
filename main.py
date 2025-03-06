import asyncio
from google import genai
import pyttsx3

client = genai.Client(api_key="AIzaSyCrx8DF7Bh2moDSiNsOUxHJLY3QCyDlOWE", http_options={'api_version': 'v1alpha'})
model_id = "gemini-2.0-flash-exp"
config = {"response_modalities": ["TEXT"]}

engine = pyttsx3.init()

async def main():
    async with client.aio.live.connect(model=model_id, config=config) as session:
        while True:
            message = input("User> ")
            if message.lower() == "exit":
                break
            await session.send(input=message, end_of_turn=True)

            async for response in session.receive():
                if response.text is None:
                    continue
                print(response.text, end="")
                engine.say(response.text)
                engine.runAndWait()

if __name__ == "__main__":
    asyncio.run(main())
