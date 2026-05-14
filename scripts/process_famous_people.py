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

def _is_valid_cookies_file(path):
    try:
        if not os.path.exists(path):
            return False
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            first_line = f.readline().strip()
        return 'Netscape HTTP Cookie File' in first_line
    except Exception:
        return False

def extract_clear_speech(full_wav_path, ref_wav_path, target_duration=8.0):
    print(f"Using AI (Silero VAD) to find clear speech in {full_wav_path}...")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                      model='silero_vad',
                                      force_reload=False,
                                      onnx=False,
                                      trust_repo=True)
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

def generate_famous_people_with_ai(service=None):
    import random
    print("Generating list of famous people using AI...")
    
    avoid_list = []
    if service:
        try:
            import upload_results
            materials_id = "1bAgeolSPr9rHKL3xCi7FwHusm19N9Iq6"
            if materials_id:
                contents = upload_results.get_drive_folder_contents(service, materials_id)
                for name, item in contents.items():
                    if item.get("mimeType") == "application/vnd.google-apps.folder":
                        avoid_list.append(name.replace("_", " "))
        except Exception as e:
            print(f"Could not fetch existing people to avoid: {e}")

    prompt = (
        f"Generate a list of 5 of the most famous and recognizable CURRENTLY ALIVE top world leaders, "
        f"prioritizing extremely well-known living figures like Donald Trump, Barack Obama, Emmanuel Macron, etc. "
        f"DO NOT include anyone who is deceased. "
    )
    
    if avoid_list:
        # Pass up to 50 random names from the avoid list to keep the prompt size reasonable
        avoid_sample = random.sample(avoid_list, min(len(avoid_list), 50))
        avoid_str = ", ".join(avoid_sample)
        prompt += f"EXTREMELY IMPORTANT: DO NOT include any of the following people as they have already been processed: {avoid_str}. "
        
    prompt += (
        f"Provide a famous quote for each person. Format each line exactly as 'Name|Quote'. "
        f"Do not include numbering, bullet points, or any other text."
    )
    
    # Try GitHub Models if GH_MODELS_TOKEN or GITHUB_TOKEN exists
    github_token = os.environ.get("GH_MODELS_TOKEN") or os.environ.get("GIT_MODEL_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if github_token:
        try:
            response = requests.post(
                "https://models.inference.ai.azure.com/chat/completions",
                headers={"Authorization": f"Bearer {github_token}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4o",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.9
                },
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                content = data['choices'][0]['message']['content']
                return [line.strip('-1234567890. ') for line in content.split('\n') if line.strip()]
            else:
                print(f"GitHub Models API error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"GitHub Models generation failed: {e}")

    # Try Cloudflare Workers AI if CLOUDFLARE_ACCOUNTS_JSON exists
    cf_accounts_env = os.environ.get("CLOUDFLARE_ACCOUNTS_JSON")
    if cf_accounts_env:
        try:
            import json
            import random
            accounts = json.loads(cf_accounts_env)
            if isinstance(accounts, dict):
                accounts = [accounts]
            
            account = random.choice(accounts)
            account_id = account.get("account_id")
            api_token = account.get("api_token")
            
            if account_id and api_token:
                response = requests.post(
                    f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/meta/llama-3-8b-instruct",
                    headers={"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"},
                    json={"messages": [{"role": "user", "content": prompt}]},
                    timeout=30
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        content = data["result"]["response"]
                        return [line.strip('-1234567890. ') for line in content.split('\n') if line.strip()]
                    else:
                        print(f"Cloudflare AI failed: {data.get('errors')}")
                else:
                    print(f"Cloudflare API error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Cloudflare AI exception: {e}")

    # Try OpenAI if OPENAI_API_KEY exists
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "gpt-4o",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.9
                },
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                content = data['choices'][0]['message']['content']
                return [line.strip('-1234567890. ') for line in content.split('\n') if line.strip()]
            else:
                print(f"OpenAI API error: {response.status_code} - {response.text}")
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
            },
            timeout=5
        )
        if response.status_code == 200:
            content = response.json().get("response", "")
            return [line.strip('-1234567890. ') for line in content.split('\n') if line.strip()]
    except Exception as e:
        # Don't print Ollama error in CI, it's expected to fail
        if 'GITHUB_ACTIONS' not in os.environ:
            print(f"Ollama generation failed: {e}")
        
    print("AI generation failed for this round. Using fallback list.")
    # Add a small delay if AI fails to prevent rapid looping
    time.sleep(10)
    
    return [
        "Joe Biden|The future belongs to those who believe in the beauty of their dreams.",
        "Rishi Sunak|Integrity and professionalism are my top priorities.",
        "Justin Trudeau|Diversity is our strength.",
        "Narendra Modi|Individual effort can make a big difference.",
        "Volodymyr Zelenskyy|We are all here, our soldiers are here, citizens are here."
    ]

# 1. Get the famous people list from Google Drive or Generate it
def get_famous_people_from_drive(file_name="famous_people.txt", force_regenerate=False):
    service = get_drive_service()

    if not service:
        print("Could not get Google Drive service. Falling back to AI generation without avoid list.")
        return generate_famous_people_with_ai(None)

    # Generate fresh list with AI, generate_famous_people_with_ai handles avoiding existing subfolders
    people = generate_famous_people_with_ai(service)

    if people:
        people.sort(key=lambda x: 0 if "politician" in x.lower() else 1)

    return people

def download_model_from_drive(service, local_model_path, folder_name="OmniVoice_model"):
    """Download model files from Google Drive."""
    import upload_results
    from googleapiclient.http import MediaIoBaseDownload as DL
    
    model_folder_id = upload_results.get_drive_folder_id(service, folder_name)
    if not model_folder_id:
        return False
    
    contents = upload_results.get_drive_folder_contents(service, model_folder_id)
    if not contents:
        return False
    
    os.makedirs(local_model_path, exist_ok=True)
    print(f"Downloading {len(contents)} model files from Google Drive...")
    
    for fname, finfo in contents.items():
        local_file = os.path.join(local_model_path, fname)
        if os.path.exists(local_file):
            continue
        print(f"  Downloading {fname}...")
        request = service.files().get_media(fileId=finfo['id'])
        fh = io.BytesIO()
        downloader = DL(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        with open(local_file, 'wb') as f:
            f.write(fh.getvalue())
    
    print("Model downloaded from Google Drive.")
    return True

def upload_model_to_drive(service, local_model_path, folder_name="OmniVoice_model"):
    """Upload model files to Google Drive."""
    import upload_results
    
    model_folder_id = upload_results.create_drive_folder(service, folder_name)
    if not model_folder_id:
        print("Could not create model folder on Drive.")
        return
    
    for fname in os.listdir(local_model_path):
        fpath = os.path.join(local_model_path, fname)
        if os.path.isfile(fpath):
            print(f"  Uploading {fname} to Drive...")
            media = MediaFileUpload(fpath, resumable=True)
            file_metadata = {'name': fname, 'parents': [model_folder_id]}
            try:
                service.files().create(body=file_metadata, media_body=media).execute()
            except Exception as e:
                print(f"  Failed to upload {fname}: {e}")
    
    print("Model uploaded to Google Drive.")

def main():
    print("Loading OmniVoice model...")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    model_path = 'k2-fsa/OmniVoice'
    local_model_path = os.path.join(script_dir, "models", "OmniVoice")
    
    if os.path.exists(local_model_path) and os.listdir(local_model_path):
        print(f"Local model found! Loading from: {local_model_path}")
        model_path = local_model_path
    else:
        # Try downloading from Google Drive first
        service = get_drive_service()
        if service and download_model_from_drive(service, local_model_path):
            print(f"Model loaded from Google Drive cache.")
            model_path = local_model_path
        else:
            print(f"Downloading from Hugging Face: {model_path}")
            # After loading, we'll save to Drive
    
    model = OmniVoice.from_pretrained(model_path)
    
    # Pre-load the ASR model (try Google Drive cache first, then HuggingFace)
    print("Pre-loading ASR model...")
    asr_downloaded_from_hf = False
    try:
        # Check if ASR model is cached on Google Drive
        service = get_drive_service()
        asr_local_path = os.path.join(script_dir, "models", "OmniVoice_ASR")
        if service and not (os.path.exists(asr_local_path) and os.listdir(asr_local_path)):
            if download_model_from_drive(service, asr_local_path, folder_name="OmniVoice_ASR_model"):
                # Set HF cache env so OmniVoice finds it
                os.environ["HF_HUB_CACHE"] = os.path.dirname(asr_local_path)
                print("ASR model loaded from Google Drive cache.")
    except Exception as e:
        print(f"ASR Drive cache check: {e}")
    
    try:
        model.load_asr_model()
        print("ASR model ready.")
        asr_downloaded_from_hf = True
    except Exception as e:
        print(f"ASR model pre-load note: {e}")
    
    # Cache models to Google Drive for next time
    service = get_drive_service()
    if service:
        # Cache OmniVoice model
        if model_path == 'k2-fsa/OmniVoice':
            try:
                from huggingface_hub import snapshot_download
                hf_local = snapshot_download(repo_id='k2-fsa/OmniVoice')
                print("Caching OmniVoice model to Google Drive...")
                upload_model_to_drive(service, hf_local, folder_name="OmniVoice_model")
            except Exception as e:
                print(f"Could not cache OmniVoice model to Drive: {e}")
        
        # Cache ASR model
        if asr_downloaded_from_hf:
            try:
                from huggingface_hub import snapshot_download
                # Find the ASR model path from HF cache
                import upload_results
                asr_folder_id = upload_results.get_drive_folder_id(service, "OmniVoice_ASR_model")
                if not asr_folder_id:
                    # Try to find the ASR model in HF cache and upload
                    hf_cache = os.path.expanduser("~/.cache/huggingface/hub")
                    if os.path.exists(hf_cache):
                        for d in os.listdir(hf_cache):
                            full_d = os.path.join(hf_cache, d)
                            if os.path.isdir(full_d) and "whisper" in d.lower():
                                snap = os.path.join(full_d, "snapshots")
                                if os.path.exists(snap):
                                    subdirs = os.listdir(snap)
                                    if subdirs:
                                        asr_path = os.path.join(snap, subdirs[0])
                                        print(f"Caching ASR model to Google Drive from {asr_path}...")
                                        upload_model_to_drive(service, asr_path, folder_name="OmniVoice_ASR_model")
                                        break
            except Exception as e:
                print(f"Could not cache ASR model to Drive: {e}")
    
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

                # Check if already processed on Google Drive
                service = get_drive_service()
                if service:
                    import upload_results
                    materials_id = "1bAgeolSPr9rHKL3xCi7FwHusm19N9Iq6"
                    if materials_id:
                        person_folder_id = upload_results.get_drive_folder_id(service, folder_name, materials_id)
                        if person_folder_id:
                            contents = upload_results.get_drive_folder_contents(service, person_folder_id)
                            if "cloned.wav" in contents:
                                print(f"Skipping {person} — cloned.wav already exists on Google Drive.")
                                continue
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

                def build_cmd(search_prefix, use_cookies=False, _query=query, _full_wav=full_wav, _cookies_file=cookies_file):
                    cmd = [
                        "python", "-m", "yt_dlp",
                        f"{search_prefix}{_query}",
                        "-x", "--audio-format", "wav",
                        "-o", _full_wav,
                        "--no-playlist", "--retries", "3", "--socket-timeout", "30",
                        "--download-sections", "*0:00-0:30",
                    ]
                    is_youtube = search_prefix.startswith("ytsearch")
                    if is_youtube:
                        cmd += ["--js-runtimes", "nodejs"]
                    if use_cookies and is_youtube and _is_valid_cookies_file(_cookies_file):
                        cmd += ["--cookies", _cookies_file]
                    return cmd

                downloaded = False
                
                # Try SoundCloud first (no auth needed)
                print("Trying SoundCloud...")
                result = subprocess.run(build_cmd("scsearch1:"), check=False, capture_output=True, text=True)
                if result.returncode == 0 and os.path.exists(full_wav):
                    downloaded = True
                    print(f"Downloaded from SoundCloud.")

                # Try YouTube with cookies if SoundCloud failed
                if not downloaded and _is_valid_cookies_file(cookies_file):
                    print("Trying YouTube with cookies...")
                    result = subprocess.run(build_cmd("ytsearch1:", use_cookies=True), check=False, capture_output=True, text=True)
                    if result.returncode == 0 and os.path.exists(full_wav):
                        downloaded = True
                        print(f"Downloaded from YouTube (with cookies).")
                    else:
                        print(f"YouTube with cookies failed:\n{result.stderr[-500:]}")

                # Try YouTube without cookies as last resort
                if not downloaded:
                    print("Trying YouTube without cookies...")
                    result = subprocess.run(build_cmd("ytsearch1:"), check=False, capture_output=True, text=True)
                    if result.returncode == 0 and os.path.exists(full_wav):
                        downloaded = True
                        print(f"Downloaded from YouTube (no cookies).")
                    else:
                        print(f"YouTube without cookies failed:\n{result.stderr[-500:]}")


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
                        folder_path, "--name", folder_name, "--parent", "1bAgeolSPr9rHKL3xCi7FwHusm19N9Iq6",
                        "--exclude", "full.wav"
                    ], check=True)
                    print(f"Uploaded {person} to Google Drive.")
                except subprocess.CalledProcessError as e:
                    print(f"Upload failed for {person}: {e}")

            print(f"\nBatch {batch_idx+1} complete. Pausing 5s before next batch...")
            time.sleep(5)

        print(f"\nRound {round_num} complete. Starting next round immediately...")


if __name__ == "__main__":
    main()
