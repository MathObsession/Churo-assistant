import json
import time
import requests

COMFY_URL = "http://127.0.0.1:8188"

PROMPT = """
cinematic drone shot of a futuristic city at sunset,
volumetric lighting, highly detailed, smooth camera movement
"""

workflow = {
    "1": {
        "inputs": {
            "text": PROMPT
        },
        "class_type": "CLIPTextEncode"
    }
}

def queue_prompt(prompt):
    r = requests.post(
        f"{COMFY_URL}/prompt",
        json={"prompt": prompt}
    )
    return r.json()

result = queue_prompt(workflow)
print("Queued:", result)

while True:
    time.sleep(2)
    try:
        history = requests.get(
            f"{COMFY_URL}/history/{result['prompt_id']}"
        ).json()

        if history:
            print("Finished.")
            break
    except:
        pass

print("Video generation complete.")