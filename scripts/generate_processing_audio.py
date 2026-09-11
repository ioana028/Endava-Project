from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "frontend" / "public" / "audio"

load_dotenv(PROJECT_ROOT / ".env")

client = OpenAI()

messages = {
    "calculating-route.mp3": (
        "I'm calculating your route now, give me just a few seconds."
    ),
    "checking-route.mp3": (
        "I'm checking the distance and travel time, I'll be right with you."
    ),
    "route-error.mp3": (
        "Unable to calculate your route right now, let me try again."
    )
}

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

for filename, text in messages.items():
    output_path = OUTPUT_DIR / filename

    response = client.audio.speech.create(
    model="gpt-4o-mini-tts",
    voice="nova",
    input=text,
    instructions=(
    "Speak warmly, naturally, and efficiently, like a friendly in-car assistant. "
    "Use a slightly brisk pace with short pauses. Avoid stretching words or "
    "dramatic pauses. Keep an upbeat, ongoing tone."
),
    response_format="mp3",
)

    response.stream_to_file(output_path)
    print(f"Generated {output_path}")