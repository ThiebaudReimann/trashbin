import asyncio
from google import genai
from google.genai import types

client = genai.Client(api_key="AIzaSyCrx8DF7Bh2moDSiNsOUxHJLY3QCyDlOWE", http_options={'api_version': 'v1alpha'})
model = "gemini-2.0-flash-exp"

def set_light_values(brightness: int, color_temp: str) -> dict[str, int | str]:
    """Set the brightness and color temperature of a room light. (mock API).

    Args:
        brightness: Light level from 0 to 100. Zero is off and 100 is full brightness
        color_temp: Color temperature of the light fixture, which can be `daylight`, `cool` or `warm`.

    Returns:
        A dictionary containing the set brightness and color temperature.
    """
    return {
        "brightness": brightness,
        "colorTemperature": color_temp
    }

config = types.LiveConnectConfig(
    response_modalities=[types.Modality.TEXT],
    tools=[set_light_values],
    
        
)

async def main():
    async with client.aio.live.connect(model=model, config=config) as session:
        await session.send(input="Turn the lights down to a romantic level. and answer", end_of_turn=True)

        async for response in session.receive():
            print(response)
            #await session.send(input="dimmed successfully", end_of_turn=True)
        print("Done")

if __name__ == "__main__":
    asyncio.run(main())