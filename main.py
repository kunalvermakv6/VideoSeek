from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import yt_dlp
import os
import re

app = FastAPI()

class AskRequest(BaseModel):
    video_url: str
    topic: str

def seconds_to_hhmmss(seconds: float) -> str:
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

def extract_subtitles(video_url: str):
    ydl_opts = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitlesformat": "vtt",
        "subtitleslangs": ["en"],
        "outtmpl": "temp"
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=True)
        return info.get("requested_subtitles")

def parse_vtt_find_timestamp(vtt_file, topic):
    with open(vtt_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Split into caption blocks
    blocks = re.split(r"\n\n+", content)

    topic_lower = topic.lower()

    for block in blocks:
        lines = block.split("\n")
        if len(lines) >= 2 and "-->" in lines[0]:
            timestamp_line = lines[0]
            text = " ".join(lines[1:]).lower()

            if topic_lower in text:
                start_time = timestamp_line.split("-->")[0].strip()
                # Convert HH:MM:SS.mmm → HH:MM:SS
                return start_time.split(".")[0]

    return None

@app.post("/ask")
def ask(req: AskRequest):
    try:
        subs = extract_subtitles(req.video_url)
        if not subs or "en" not in subs:
            raise HTTPException(status_code=404, detail="No English subtitles found")

        vtt_path = subs["en"]["filepath"]

        timestamp = parse_vtt_find_timestamp(vtt_path, req.topic)

        # Cleanup
        if os.path.exists(vtt_path):
            os.remove(vtt_path)

        if not timestamp:
            raise HTTPException(status_code=404, detail="Topic not found")

        return {
            "timestamp": timestamp,
            "video_url": req.video_url,
            "topic": req.topic
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

import os

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)