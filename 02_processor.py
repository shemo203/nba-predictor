
import json
import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

with open("data.json") as data_file:
    history = json.load(data_file)

headlines_block = history[-1]["action_list"]

system_prompt = """
You are an expert NBA sports betting analyst focusing ONLY on SHORT-TERM impact (Next 24-48 hours).

For EACH headline provided, return a JSON object with:
- "headline": The original text
- "team": The 3-letter NBA abbreviation (e.g., "LAL").
- "sentiment": "POSITIVE", "NEGATIVE", or "NEUTRAL".
- "score": Float (-1.0 to 1.0) representing impact on WINNING THE NEXT GAME.
    * CRITICAL RULES:
    * OFFSEASON/FUTURE NEWS: Score MUST be 0.0. (e.g., "Trade talks for summer", "Draft picks").
    * TRADE RUMORS: Score 0.0 UNLESS the player is "Sitting Out" or "Distracted".
    * INJURIES/SUSPENSIONS: These are the only high scores (>0.5 or <-0.5).
- "reasoning": Brief explanation. If 0.0, say "Future event" or "Rumor only".

Output a valid JSON object with a key "analysis" containing the list.
"""

client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)
completion = client.chat.completions.create(
    messages=[
        {
            "role": "system",
            "content": system_prompt
        },
        {
            "role": "user",
            "content": f"Analyze these headlines:\n{headlines_block}"
        }
    ],
    model="llama-3.3-70b-versatile", # The model from your snippet
    response_format={"type": "json_object"}, # <--- CRITICAL: Forces valid JSON return
    temperature=0.1 # Low temperature = More math/logic, less creativity
)

ai_response_text = completion.choices[0].message.content
ai_text = json.loads(ai_response_text)
history[-1]["analytic"] = ai_text["analysis"]

with open("data.json", "w") as data_file:
    json.dump(history, data_file, indent = -4)