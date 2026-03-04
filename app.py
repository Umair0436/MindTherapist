from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder='.')
CORS(app)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

def get_groq_response(messages, system_prompt):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    groq_messages = []

    if system_prompt:
        groq_messages.append({"role": "system", "content": system_prompt})

    for m in messages:
        role = "assistant" if m['role'] == 'patient' else "user"
        groq_messages.append({"role": role, "content": m['message']})

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": groq_messages,
        "temperature": 0.9,
        "max_tokens": 500,
        "top_p": 0.95
    }

    try:
        res = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
        result = res.json()

        if 'error' in result:
            return None, result['error']['message']

        text = result['choices'][0]['message']['content']
        return text, None

    except Exception as e:
        return None, str(e)


@app.route('/')
def index():
    return send_from_directory('.', 'index.html')


@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    messages = data.get('messages', [])
    system_prompt = data.get('system_prompt', '')

    reply, error = get_groq_response(messages, system_prompt)

    if error:
        return jsonify({'error': error}), 500

    return jsonify({'reply': reply})


if __name__ == '__main__':
    print(f"\n✅ MindTherapist running with Groq (llama-3.3-70b)")
    print(f"🌐 Open: http://localhost:5000\n")
    app.run(debug=True, port=5000)