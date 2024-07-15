from flask import Flask, request, jsonify, send_from_directory
import ffmpeg
import os
import requests
import time
import logging

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'
ASSEMBLYAI_API_KEY = os.getenv('ASSEMBLYAI_API_KEY', 'default_assemblyai_key')
ASSEMBLYAI_TRANSCRIPT_ENDPOINT = 'https://api.assemblyai.com/v2/transcript'
ASSEMBLYAI_UPLOAD_ENDPOINT = 'https://api.assemblyai.com/v2/upload'
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', 'default_openai_key')
MAX_TOKENS = 2048

logging.basicConfig(level=logging.DEBUG, filename='app.log', filemode='w',
                    format='%(name)s - %(levelname)s - %(message)s')

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

if not os.path.exists(PROCESSED_FOLDER):
    os.makedirs(PROCESSED_FOLDER)

def download_m3u8(m3u8_url, output_path):
    try:
        ffmpeg.input(m3u8_url).output(output_path, format='mp3', audio_bitrate='320k').run(overwrite_output=True)
        return output_path
    except ffmpeg.Error as e:
        logging.error(f'Erro: {e.stderr.decode()}')
        return None

def upload_audio(file_path):
    with open(file_path, 'rb') as f:
        response = requests.post(
            ASSEMBLYAI_UPLOAD_ENDPOINT,
            headers={'authorization': ASSEMBLYAI_API_KEY},
            files={'file': f}
        )
    if response.status_code == 200:
        return response.json().get('upload_url')
    else:
        logging.error(f'Erro no upload: {response.status_code} - {response.text}')
        return None

def request_transcription(audio_url):
    response = requests.post(
        ASSEMBLYAI_TRANSCRIPT_ENDPOINT,
        headers={
            'authorization': ASSEMBLYAI_API_KEY,
            'content-type': 'application/json'
        },
        json={
            'audio_url': audio_url,
            'language_code': 'pt'
        }
    )
    if response.status_code == 200:
        return response.json().get('id')
    else:
        logging.error(f'Erro ao solicitar transcrição: {response.status_code} - {response.text}')
        return None

def poll_transcription_result(transcript_id):
    url = f"{ASSEMBLYAI_TRANSCRIPT_ENDPOINT}/{transcript_id}"
    headers = {
        'authorization': ASSEMBLYAI_API_KEY
    }
    while True:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            result = response.json()
            if result['status'] == 'completed':
                return result['text']
            elif result['status'] == 'failed':
                logging.error(f'Transcrição falhou: {result}')
                return None
        else:
            logging.error(f'Erro ao obter resultado da transcrição: {response.status_code} - {response.text}')
        time.sleep(5)

def format_text_with_gpt(text):
    headers = {
        'Authorization': f'Bearer {OPENAI_API_KEY}',
        'Content-Type': 'application/json',
    }

    chunks = split_text_into_chunks(text, MAX_TOKENS)
    formatted_chunks = []

    for chunk in chunks:
        prompt = f"Formate esse texto de acordo como um copywriter escreveria ele, utilizando ... após as frases e quebra de linha. Não modifique nada do texto, apenas faça a formatação dele todo.\n\nTexto:\n{chunk}"
        data = {
            'model': 'gpt-3.5-turbo',
            'messages': [
                {"role": "system", "content": "Você é um assistente útil."},
                {"role": "user", "content": prompt}
            ],
            'max_tokens': MAX_TOKENS,
            'temperature': 0.7,
        }
        response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=data)
        if response.status_code == 200:
            formatted_chunks.append(response.json()['choices'][0]['message']['content'].strip())
        else:
            logging.error(f'Erro ao formatar texto com GPT: {response.status_code} - {response.text}')
            return None

    formatted_text = '\n'.join(formatted_chunks)
    return formatted_text

def split_text_into_chunks(text, max_tokens):
    words = text.split()
    chunks = []
    current_chunk = []
    current_length = 0

    for word in words:
        word_length = len(word)
        if current_length + word_length + 1 > max_tokens:  # +1 para o espaço
            chunks.append(' '.join(current_chunk))
            current_chunk = [word]
            current_length = word_length
        else:
            current_chunk.append(word)
            current_length += word_length + 1  # +1 para o espaço

    if current_chunk:
        chunks.append(' '.join(current_chunk))

    return chunks

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/process', methods=['POST'])
def process_link():
    m3u8_url = request.json.get('m3u8_url')
    if not m3u8_url:
        return jsonify({'error': 'No URL provided'}), 400
    
    output_file = os.path.join(PROCESSED_FOLDER, 'audio.mp3')
    mp3_file = download_m3u8(m3u8_url, output_file)
    
    if not mp3_file:
        return jsonify({'error': 'Failed to download and convert m3u8'}), 500
    
    upload_url = upload_audio(mp3_file)
    if not upload_url:
        return jsonify({'error': 'Failed to upload audio'}), 500

    transcript_id = request_transcription(upload_url)
    if not transcript_id:
        return jsonify({'error': 'Failed to request transcription'}), 500

    transcript_text = poll_transcription_result(transcript_id)
    if not transcript_text:
        return jsonify({'error': 'Failed to get transcription result'}), 500

    formatted_text = format_text_with_gpt(transcript_text)
    if not formatted_text:
        return jsonify({'error': 'Failed to format transcription'}), 500

    raw_text_path = os.path.join(PROCESSED_FOLDER, 'audio_raw.txt')
    with open(raw_text_path, 'w', encoding='utf-8') as f:
        f.write(transcript_text)
    
    formatted_text_path = os.path.join(PROCESSED_FOLDER, 'audio_formatted.txt')
    with open(formatted_text_path, 'w', encoding='utf-8') as f:
        f.write(formatted_text)
    
    return jsonify({
        'mp3_file': 'audio.mp3',
        'raw_text_file': 'audio_raw.txt',
        'formatted_text_file': 'audio_formatted.txt'
    }), 200

@app.route('/download/<filename>')
def download_file(filename):
    filepath = os.path.join(PROCESSED_FOLDER, filename)
    if os.path.exists(filepath):
        return send_from_directory(PROCESSED_FOLDER, filename)
    else:
        return jsonify({'error': 'File not found'}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
