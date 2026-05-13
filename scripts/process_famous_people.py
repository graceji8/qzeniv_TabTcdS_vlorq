import os
import time
import subprocess
import soundfile as sf
import io
import requests
import warnings
import torch
import logging
import transformers
import huggingface_hub
from omnivoice import OmniVoice
from upload_results import get_drive_service
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

# Suppress warnings
transformers.logging.set_verbosity_error()
logging.getLogger("transformers").setLevel(logging.ERROR)
huggingface_hub.logging.set_verbosity_error()

def extract_clear_speech(full_wav_path, ref_wav_path, target_duration=8.0):
    print(f"Using AI (Silero VAD) to find clear speech in {full_wav_path}...")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                      model='silero_vad',
                                      force_reload=False,
                                      onnx=False)
    get_speech_timestamps = utils[0]
    
    try:
        data, samplerate = sf.read(full_wav_path)
    except Exception as e:
        print(f"Error reading audio: {e}")
        return False
        
    # Process only the first 5 minutes to save memory/time
    max_samples = 5 * 60 * samplerate
    if len(data) > max_samples:
        data = data[:max_samples]
        
    wav = torch.tensor(data, dtype=torch.float32)
    if wav.ndim > 1:
        wav = wav.mean(dim=1)
        
    if samplerate != 16000:
        import torchaudio.transforms as T
        resampler = T.Resample(samplerate, 16000)
        wav_16k = resampler(wav)
    else:
        wav_16k = wav
        
    speech_timestamps = get_speech_timestamps(wav_16k, model, sampling_rate=16000)
    
    if not speech_timestamps:
        print("No speech detected by AI.")
        return False
        
    target_samples_16k = int(target_duration * 16000)
    best_segment = None
    
    for ts in speech_timestamps:
        length = ts['end'] - ts['start']
        if length >= target_samples_16k:
            best_segment = {'start': ts['start'], 'end': ts['start'] + target_samples_16k}
            break
            
    if not best_segment:
        longest = max(speech_timestamps, key=lambda x: x['end'] - x['start'])
        best_segment = longest
        if best_segment['end'] - best_segment['start'] > target_samples_16k:
            best_segment['end'] = best_segment['start'] + target_samples_16k

    start_sample = int(best_segment['start'] * samplerate / 16000)
    end_sample = int(best_segment['end'] * samplerate / 16000)
    
    print(f"AI selected clear speech segment from {start_sample/samplerate:.2f}s to {end_sample/samplerate:.2f}s")
    
    extracted_data = data[start_sample:end_sample]
    sf.write(ref_wav_path, extracted_data, samplerate)
    return True

def generate_famous_people_with_ai():
    print("Generating list of famous people using AI...")
    prompt = "Generate a list of 5 famous people, including famous film actors, and a famous quote for each person. Format each line exactly as 'Name|Quote'. Do not include numbering or bullet points."
    
    # Try OpenAI if key exists
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "gpt-4o",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7
                }
            )
            data = response.json()
            content = data['choices'][0]['message']['content']
            return [line.strip('-1234567890. ') for line in content.split('\n') if line.strip()]
        except Exception as e:
            print(f"OpenAI generation failed: {e}")
            
    # Try local Ollama
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3",
                "prompt": prompt,
                "stream": False
            }
        )
        if response.status_code == 200:
            content = response.json().get("response", "")
            return [line.strip('-1234567890. ') for line in content.split('\n') if line.strip()]
    except Exception as e:
        print(f"Ollama generation failed: {e}")
        
    print("AI generation failed. Using default fallback list.")
    return [
        "Leonardo DiCaprio|I'm the king of the world!",
        "Brad Pitt|You must lose everything in order to gain anything.",
        "Scarlett Johansson|I'm always looking for a challenge.",
        "Tom Cruise|I feel the need, the need for speed.",
        "Morgan Freeman|Get busy living or get busy dying."
    ]

# 1. Get the famous people list from Google Drive or Generate it
def get_famous_people_from_drive(file_name="famous_people.txt", force_regenerate=False):
    print(f"Fetching famous people list from Google Drive ({file_name})...")
    service = get_drive_service()

    if not service:
        print("Could not get Google Drive service. Falling back to AI generation.")
        return generate_famous_people_with_ai()

    # Always regenerate on forced rounds
    if not force_regenerate:
        query = f"name = '{file_name}' and trashed = false"
        try:
            results = service.files().list(q=query, fields="files(id, name)").execute()
            items = results.get('files', [])

            if items:
                file_id = items[0]['id']
                request = service.files().get_media(fileId=file_id)
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()

                content = fh.getvalue().decode('utf-8')
                people = [line.strip('-1234567890. ') for line in content.split('\n') if line.strip()]

                if people:
                    print(f"Successfully loaded {len(people)} people from Google Drive.")
                    return people
        except Exception as e:
            print(f"Error fetching list from Google Drive: {e}")

    # Generate fresh list with AI
    print("Generating fresh list with AI...")
    people = generate_famous_people_with_ai()

    if people and service:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        local_file_path = os.path.join(script_dir, file_name)
        with open(local_file_path, "w", encoding="utf-8") as f:
            for p in people:
                f.write(p + "\n")

        print(f"Uploading new list to Google Drive...")
        import upload_results
        parent_id = upload_results.create_drive_folder(service, "materials")

        # Delete old file first to avoid duplicates
        try:
            query = f"name = '{file_name}' and trashed = false"
            results = service.files().list(q=query, fields="files(id)").execute()
            for old_file in results.get('files', []):
                service.files().delete(fileId=old_file['id']).execute()
                print(f"Deleted old {file_name} from Drive.")
        except Exception as e:
            print(f"Could not delete old file: {e}")

        media = MediaFileUpload(local_file_path, mimetype='text/plain', resumable=True)
        file_metadata = {'name': file_name}
        if parent_id:
            file_metadata['parents'] = [parent_id]

        try:
            service.files().create(body=file_metadata, media_body=media).execute()
            print(f"Uploaded fresh list to Google Drive: {people}")
        except Exception as e:
            print(f"Error uploading to Google Drive: {e}")

    return people

def main():
    print("Loading OmniVoice model...")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    model_path = 'k2-fsa/OmniVoice'
    local_model_path = os.path.join(script_dir, "models", "OmniVoice")
    
    if os.path.exists(local_model_path):
        print(f"Local model found! Loading manually from: {local_model_path}")
        model_path = local_model_path
    else:
        print(f"Loading from Hugging Face: {model_path}")
        
    model = OmniVoice.from_pretrained(model_path)
    upload_script = os.path.join(script_dir, "upload_results.py")

    batch_size = 5
    round_num = 0

    while True:
        round_num += 1
        print(f"\n{'#'*40}")
        print(f"  ROUND {round_num} — Fetching fresh list from Drive")
        print(f"{'#'*40}")

        # Round 1: use existing Drive list if available
        # Round 2+: always generate a fresh AI list
        famous_people_data = get_famous_people_from_drive(
            "famous_people.txt",
            force_regenerate=(round_num > 1)
        )

        if not famous_people_data:
            print("No people found. Waiting 60s before retrying...")
            time.sleep(60)
            continue

        # Split into batches of 5
        batches = [famous_people_data[i:i+batch_size] for i in range(0, len(famous_people_data), batch_size)]

        for batch_idx, batch in enumerate(batches):
            print(f"\n{'='*40}")
            print(f"  Batch {batch_idx+1}/{len(batches)} of Round {round_num}")
            print(f"{'='*40}")

            for item in batch:
                if "|" in item:
                    person, sample_text = item.split("|", 1)
                    person = person.strip()
                    sample_text = sample_text.strip()
                else:
                    person = item.strip()
                    sample_text = "You're so lucky. You are so lucky to be an opera singer. I mean this."

                print(f"\nProcessing: {person}")

                folder_name = person.replace(" ", "_")
                temp_base = os.path.join(script_dir, "temp_workspace")
                os.makedirs(temp_base, exist_ok=True)
                folder_path = os.path.join(temp_base, folder_name)
                os.makedirs(folder_path, exist_ok=True)

                full_wav = os.path.join(folder_path, "full.wav")
                ref_wav = os.path.join(folder_path, "ref.wav")
                cloned_wav = os.path.join(folder_path, "cloned.wav")

                # Clear previous run's files so we re-process fresh each round
                for f in [full_wav, ref_wav, cloned_wav]:
                    if os.path.exists(f):
                        os.remove(f)

                # Download
                print(f"Downloading audio for {person}...")
                query = f"{person} speaking speech"
                cookies_file = os.path.join(script_dir, "cookies.txt")

                def build_cmd(search_prefix, _query=query, _full_wav=full_wav, _cookies_file=cookies_file):
                    cmd = [
                        "python", "-m", "yt_dlp",
                        f"{search_prefix}{_query}",
                        "-x", "--audio-format", "wav",
                        "-o", _full_wav,
                        "--no-playlist", "--retries", "3", "--socket-timeout", "30",
                    ]
                    if os.path.exists(_cookies_file):
                        cmd += ["--cookies", _cookies_file]
                    else:
                        cmd += ["--cookies-from-browser", "chromium"]
                    return cmd

                downloaded = False
                
                # Try YouTube
                result = subprocess.run(build_cmd("ytsearch1:"), check=False, capture_output=True, text=True)
                if result.returncode == 0 and os.path.exists(full_wav):
                    downloaded = True
                    print(f"Downloaded from YouTube.")
                else:
                    print(f"YouTube failed:\n{result.stderr[-800:]}")  # show full error

                # Try SoundCloud
                if not downloaded:
                    print("Trying SoundCloud...")
                    result = subprocess.run(build_cmd("scsearch1:"), check=False, capture_output=True, text=True)
                    if result.returncode == 0 and os.path.exists(full_wav):
                        downloaded = True
                        print(f"Downloaded from SoundCloud.")
                    else:
                        print(f"SoundCloud failed:\n{result.stderr[-800:]}")  # show full error

                if not downloaded:
                    print(f"Skipping {person} — could not download audio.")
                    continue

                # VAD
                success = extract_clear_speech(full_wav, ref_wav, target_duration=8.0)
                if not success:
                    print(f"Failed to find clear speech for {person}.")
                    continue

                # Clone
                try:
                    print(f"Cloning voice for {person}...")
                    audio = model.generate(text=sample_text, ref_audio=ref_wav)
                    sf.write(cloned_wav, audio[0], 24000)
                    print(f"Cloned successfully: {person}")
                except Exception as e:
                    print(f"Failed to clone {person}: {e}")
                    continue

                # Upload
                try:
                    subprocess.run([
                        "python", upload_script,
                        folder_path, "--name", folder_name, "--parent-name", "materials"
                    ], check=True)
                    print(f"Uploaded {person} to Google Drive.")
                except subprocess.CalledProcessError as e:
                    print(f"Upload failed for {person}: {e}")

            print(f"\nBatch {batch_idx+1} complete. Pausing 5s before next batch...")
            time.sleep(5)

        print(f"\nRound {round_num} complete. Starting next round immediately...")


if __name__ == "__main__":
    main()
