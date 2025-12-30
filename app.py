import os
import requests
import re
from flask import Flask, render_template, request, Response, stream_with_context

app = Flask(__name__)

# Configuration
API_BASE_URL = "https://ai.zht666.dpdns.org/v1/audio/speech"
API_KEY = "sk-zht666"

# Voice mapping to match what Microsoft Edge TTS expects
VOICE_MAP = {
    "shimmer": "zh-CN-XiaoxiaoNeural",
    "alloy": "zh-CN-YunyangNeural",
    "fable": "zh-CN-YunjianNeural",
    "onyx": "zh-CN-XiaoyiNeural",
    "nova": "zh-CN-YunxiNeural",
    "echo": "zh-CN-liaoning-XiaobeiNeural"
}

def clean_text(text, options):
    if not text:
        return text
        
    if options.get('removeMarkdown'):
        # Remove markdown syntax but keep the text
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text) # Links
        text = re.sub(r'(\*\*|__)(.*?)\1', r'\2', text)     # Bold
        text = re.sub(r'(\*|_)(.*?)\1', r'\2', text)       # Italic
        text = re.sub(r'#{1,6}\s?', '', text)              # Headers
        text = re.sub(r'`{1,3}.*?`{1,3}', '', text, flags=re.DOTALL) # Code blocks
        
    if options.get('removeEmoji'):
        # More comprehensive emoji removal
        text = text.encode('utf-16', 'surrogatepass').decode('utf-16')
        text = re.sub(r'[\U00010000-\U0010ffff]', '', text)
        
    if options.get('removeUrl'):
        text = re.sub(r'https?://\S+|www\.\S+', '', text)
        
    if options.get('removeCitations'):
        text = re.sub(r'\[\d+\]', '', text)
        
    if options.get('removeWhitespace'):
        # Remove ALL whitespace including newlines
        text = re.sub(r'\s+', '', text)
    else:
        # Just normalize multiple spaces/newlines if not removing all
        text = re.sub(r' +', ' ', text)
        
    custom_keywords = options.get('customKeywords', '')
    if custom_keywords:
        keywords = [k.strip() for k in custom_keywords.split(',') if k.strip()]
        for kw in keywords:
            text = text.replace(kw, '')
            
    return text.strip()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_speech():
    data = request.json
    text = data.get('input', '')
    voice_key = data.get('voice', 'shimmer')
    speed = float(data.get('speed', 1.0))
    pitch = float(data.get('pitch', 1.0))
    cleaning_options = data.get('cleaningOptions', {})
    
    # Perform advanced text cleaning in Python
    text = clean_text(text, cleaning_options)
    
    if not text:
        return {"error": "清理后的文本为空或输入文本缺失"}, 400

    # Get the actual Microsoft voice name
    final_voice = VOICE_MAP.get(voice_key, voice_key)

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": f"tts-1-{voice_key}", # Using the model format the worker expects
        "input": text,
        "voice": final_voice,
        "speed": speed,
        "pitch": pitch,
        "stream": True
    }

    try:
        # Request to the TTS API
        response = requests.post(API_BASE_URL, json=payload, headers=headers, stream=True)
        
        if response.status_code != 200:
            return {"error": f"API Error: {response.text}"}, response.status_code

        # Stream the response back to the client
        return Response(stream_with_context(response.iter_content(chunk_size=1024)), 
                        content_type=response.headers.get('Content-Type', 'audio/mpeg'))

    except Exception as e:
        return {"error": str(e)}, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
