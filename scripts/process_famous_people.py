import os
import sys

# Use home IP via SSH SOCKS proxy
os.environ["YTDLP_PROXY"] = "socks5://127.0.0.1:1080"
os.environ["http_proxy"] = "socks5h://127.0.0.1:1080"
os.environ["https_proxy"] = "socks5h://127.0.0.1:1080"

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
import socket
import signal
from datetime import datetime
from omnivoice import OmniVoice
from upload_results import get_drive_service
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

# Set global socket timeout to 60 seconds
socket.setdefaulttimeout(60)

def checkpoint(msg):
    """Print timestamped message to track execution progress."""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] CHECKPOINT: {msg}", flush=True)

class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutException("Operation timed out!")

def check_proxy_readiness():
    """Verify that the SSH SOCKS proxy is actually working."""
    checkpoint("Checking SOCKS proxy readiness...")
    proxies = {
        "http": "socks5h://127.0.0.1:1080",
        "https": "socks5h://127.0.0.1:1080",
    }
    try:
        # Try a small request to HF or Google
        response = requests.get("https://huggingface.co", proxies=proxies, timeout=15)
        if response.status_code == 200:
            checkpoint("Proxy is READY and reachable.")
            return True
        else:
            checkpoint(f"Proxy check returned unexpected status: {response.status_code}")
    except Exception as e:
        checkpoint(f"Proxy check FAILED: {e}")
    return False

# Suppress warnings
transformers.logging.set_verbosity_error()
logging.getLogger("transformers").setLevel(logging.ERROR)
huggingface_hub.logging.set_verbosity_error()

_VAD_MODEL = None
_VAD_UTILS = None

def _is_valid_cookies_file(path):
    try:
        if not os.path.exists(path) or os.path.getsize(path) < 10:
            return False
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read().lower()
        # Accept if it looks like it has youtube/google cookies, or just has reasonable size
        return 'youtube' in content or 'google' in content or '.com' in content
    except Exception:
        return False

def get_vad_model():
    """Load Silero VAD once per process instead of once per audio file."""
    global _VAD_MODEL, _VAD_UTILS
    if _VAD_MODEL is not None and _VAD_UTILS is not None:
        return _VAD_MODEL, _VAD_UTILS

    checkpoint("Loading Silero VAD model (torch.hub.load)...")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        old_http = os.environ.get("http_proxy")
        old_https = os.environ.get("https_proxy")
        # Silero VAD loading often fails with proxy due to GitHub/S3 interactions
        if "http_proxy" in os.environ: del os.environ["http_proxy"]
        if "https_proxy" in os.environ: del os.environ["https_proxy"]
        
        # Set 3-minute alarm for VAD load
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(180)
        
        try:
            _VAD_MODEL, _VAD_UTILS = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                                    model='silero_vad',
                                                    force_reload=False,
                                                    onnx=False,
                                                    trust_repo=True)
            checkpoint("Silero VAD model loaded successfully.")
        except TimeoutException:
            checkpoint("ERROR: Silero VAD loading TIMED OUT (3 min limit).")
            # Fallback or exit? If VAD fails, we can't process audio.
            # We'll try to continue but expect failures.
            pass
        except Exception as e:
            checkpoint(f"Silero VAD loading failed: {e}")
        finally:
            signal.alarm(0) # Disable alarm
            if old_http: os.environ["http_proxy"] = old_http
            if old_https: os.environ["https_proxy"] = old_https
    return _VAD_MODEL, _VAD_UTILS

def extract_clear_speech(full_wav_path, ref_wav_path, target_duration=8.0):
    print(f"Using AI (Silero VAD) to find clear speech in {full_wav_path}...", flush=True)
    model, utils = get_vad_model()
    get_speech_timestamps = utils[0]
    
    try:
        data, samplerate = sf.read(full_wav_path)
    except Exception as e:
        print(f"Error reading audio: {e}", flush=True)
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
        
    speech_timestamps = get_speech_timestamps(wav_16k, model, sampling_rate=16000, threshold=0.65)
    
    if not speech_timestamps:
        print("No speech detected by AI.", flush=True)
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
    
    print(f"AI selected clear speech segment from {start_sample/samplerate:.2f}s to {end_sample/samplerate:.2f}s", flush=True)
    
    extracted_data = data[start_sample:end_sample]
    sf.write(ref_wav_path, extracted_data, samplerate)
    return True

def generate_famous_people_with_ai(service=None):
    import random
    print("Generating list of famous people using AI...", flush=True)
    
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
        print(f"DEBUG: github_token detected (length: {len(github_token)})", flush=True)
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
                print("DEBUG: GitHub Models API success!")
                data = response.json()
                content = data['choices'][0]['message']['content']
                return [line.strip('-1234567890. ') for line in content.split('\n') if line.strip()]
            else:
                print(f"GitHub Models API error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"GitHub Models generation failed: {e}")
    else:
        print("DEBUG: No github_token found in environment.")

    # Try Cloudflare Workers AI if CLOUDFLARE_ACCOUNTS_JSON exists
    cf_accounts_env = os.environ.get("CLOUDFLARE_ACCOUNTS_JSON")
    if cf_accounts_env:
        print("DEBUG: CLOUDFLARE_ACCOUNTS_JSON detected.", flush=True)
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
                        print("DEBUG: Cloudflare AI success!")
                        content = data["result"]["response"]
                        return [line.strip('-1234567890. ') for line in content.split('\n') if line.strip()]
                    else:
                        print(f"Cloudflare AI failed: {data.get('errors')}")
                else:
                    print(f"Cloudflare API error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Cloudflare AI exception: {e}")
    else:
        print("DEBUG: No CLOUDFLARE_ACCOUNTS_JSON found.")

    # Try OpenAI if OPENAI_API_KEY exists
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        print(f"DEBUG: OPENAI_API_KEY detected (length: {len(api_key)})", flush=True)
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
                print("DEBUG: OpenAI API success!")
                data = response.json()
                content = data['choices'][0]['message']['content']
                return [line.strip('-1234567890. ') for line in content.split('\n') if line.strip()]
            else:
                print(f"OpenAI API error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"OpenAI generation failed: {e}")
    else:
        print("DEBUG: No OPENAI_API_KEY found.")
            
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
        # Don't print Ollama connection errors in CI or if it's clearly not there
        is_conn_error = any(msg in str(e).lower() for msg in ["connection refused", "failed to establish a new connection"])
        if 'GITHUB_ACTIONS' not in os.environ and not is_conn_error:
            print(f"Ollama generation failed: {e}")
        elif is_conn_error:
            # Quietly note that local AI is unavailable
            pass
        
    print("AI generation failed for this round. Using fallback list.", flush=True)
    # Add a small delay if AI fails to prevent rapid looping
    time.sleep(5)
    
    fallback = [
        "Joe Biden|The future belongs to those who believe in the beauty of their dreams.",
        "Rishi Sunak|Integrity and professionalism are my top priorities.",
        "Justin Trudeau|Diversity is our strength.",
        "Narendra Modi|Individual effort can make a big difference.",
        "Volodymyr Zelenskyy|We are all here, our soldiers are here, citizens are here.",
        "Elon Musk|When something is important enough, you do it even if the odds are not in your favor.",
        "Bill Gates|Success is a lousy teacher. It seduces smart people into thinking they can't lose.",
        "Jeff Bezos|Your brand is what other people say about you when you're not in the room.",
        "Mark Zuckerberg|The biggest risk is not taking any risk.",
        "Tim Cook|Life is fragile. We’re not guaranteed a tomorrow so give it everything you've got.",
        "Pope Francis|A little bit of mercy makes the world less cold and more just.",
        "Dalai Lama|Happiness is not something ready made. It comes from your own actions.",
        "Malala Yousafzai|One child, one teacher, one book, one pen can change the world.",
        "Greta Thunberg|I want you to act as if our house is on fire. Because it is.",
        "Lionel Messi|You have to fight to reach your dream. You have to sacrifice and work hard for it.",
        "Cristiano Ronaldo|Your love makes me strong, your hate makes me unstoppable.",
        "LeBron James|You can't be afraid to fail. It's the only way you succeed.",
        "Stephen Curry|Success is not a destination, it's a journey.",
        "Lewis Hamilton|I feel like people are expecting me to fail, therefore I expect myself to win.",
        "Serena Williams|I really think a champion is defined not by their wins but by how they can recover when they fall.",
        "Taylor Swift|No matter what happens in life, be good to people. Being good to people is a wonderful legacy to leave behind.",
        "Beyonce|I don't like to gamble, but if there's one thing I'm willing to bet on, it's myself.",
        "Rihanna|It's important to keep your head held high and your heart even higher.",
        "Adele|I don't make music for eyes. I make music for ears.",
        "Ed Sheeran|Be a true heart, not a follower.",
        "Drake|Tables turn, bridges burn, you live and learn.",
        "Kanye West|I am my own biggest fan.",
        "Lady Gaga|Don't you ever let a soul in the world tell you that you can't be exactly who you are.",
        "Bruno Mars|I just want to make music and have a good time.",
        "Justin Bieber|I want my world to be fun.",
        "Tom Hanks|I've made a lot of movies and some of them were even good.",
        "Meryl Streep|The great gift of human beings is that we have the power of empathy.",
        "Leonardo DiCaprio|If you can do what you do best and be happy, you're further along in life than most people.",
        "Brad Pitt|I'm one of those people you hate because of genetics. It's the truth.",
        "Angelina Jolie|Every day we choose who we are by how we define ourselves.",
        "Robert Downey Jr.|I know who I am. I'm the dude playin' the dude, disguised as another dude!",
        "Scarlett Johansson|I'm not going to apologize for being successful.",
        "Will Smith|If you're not making someone else's life better, then you're wasting your time.",
        "Dwayne Johnson|Success at anything will always come down to this: focus and effort.",
        "Oprah Winfrey|The biggest adventure you can take is to live the life of your dreams.",
        "Ellen DeGeneres|Be kind to one another.",
        "David Attenborough|It seems to me that the natural world is the greatest source of excitement.",
        "Michelle Obama|Success isn't about how much money you make; it's about the difference you make in people's lives.",
        "Hillary Clinton|Women are the largest untapped reservoir of talent in the world.",
        "Angela Merkel|Fear was never a good adviser, neither in our personal lives nor in our society.",
        "Emmanuel Macron|Make our planet great again.",
        "Boris Johnson|My friends, as I have discovered myself, there are no disasters, only opportunities.",
        "Keir Starmer|Country first, party second.",
        "Olaf Scholz|We are living through a watershed era.",
        "Xi Jinping|The people's aspirations for a better life are what we must fight for."
    ]
    
    random.shuffle(fallback)
    return fallback[:10]

# 1. Get the famous people list from Google Drive or Generate it
def get_famous_people_from_drive(file_name="famous_people.txt", force_regenerate=False):
    service = get_drive_service()

    if not service:
        print("Could not get Google Drive service. Falling back to AI generation without avoid list.", flush=True)
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
    print(f"Downloading {len(contents)} model files from Google Drive...", flush=True)
    
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
    
    print("Model uploaded to Google Drive.", flush=True)

def main():
    checkpoint("Starting process_famous_people.py")
    
    # Check proxy first
    if not check_proxy_readiness():
        checkpoint("WARNING: Proxy not ready. HF/YouTube downloads may fail.")

    checkpoint("Initializing OmniVoice model setup...")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    model_path = 'k2-fsa/OmniVoice'
    local_model_path = os.path.join(script_dir, "models", "OmniVoice")
    
    if os.path.exists(local_model_path) and os.listdir(local_model_path):
        checkpoint(f"Local model found! Loading from: {local_model_path}")
        model_path = local_model_path
    else:
        # Try downloading from Google Drive first
        checkpoint("Searching for OmniVoice model on Google Drive...")
        service = get_drive_service()
        if service:
            try:
                # Set alarm for Drive download (5 mins)
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(300)
                if download_model_from_drive(service, local_model_path):
                    checkpoint(f"Model loaded from Google Drive cache.")
                    model_path = local_model_path
                else:
                    checkpoint("Model not found on Google Drive.")
            except TimeoutException:
                checkpoint("ERROR: Google Drive model download TIMED OUT.")
            finally:
                signal.alarm(0)
        
        if model_path == 'k2-fsa/OmniVoice':
            checkpoint(f"Will download from Hugging Face: {model_path}")

    checkpoint(f"Calling OmniVoice.from_pretrained({model_path})...")
    try:
        # Set alarm for HF download/load (10 mins)
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(600)
        model = OmniVoice.from_pretrained(model_path)
        checkpoint("OmniVoice model ready.")
    except TimeoutException:
        checkpoint("ERROR: OmniVoice model loading TIMED OUT (10 min limit).")
        return # Cannot proceed without model
    except Exception as e:
        checkpoint(f"ERROR: OmniVoice loading failed: {e}")
        return
    finally:
        signal.alarm(0)
    
    # Pre-load the ASR model (try Google Drive cache first, then HuggingFace)
    checkpoint("Pre-loading ASR model...")
    asr_downloaded_from_hf = False
    try:
        # Check if ASR model is cached on Google Drive
        service = get_drive_service()
        asr_local_path = os.path.join(script_dir, "models", "OmniVoice_ASR")
        if service and not (os.path.exists(asr_local_path) and os.listdir(asr_local_path)):
            checkpoint("Checking for ASR model on Google Drive...")
            signal.alarm(300)
            try:
                if download_model_from_drive(service, asr_local_path, folder_name="OmniVoice_ASR_model"):
                    # Set HF cache env so OmniVoice finds it
                    os.environ["HF_HUB_CACHE"] = os.path.dirname(asr_local_path)
                    checkpoint("ASR model loaded from Google Drive cache.")
            finally:
                signal.alarm(0)
    except Exception as e:
        checkpoint(f"ASR Drive cache check exception: {e}")
    
    checkpoint("Calling model.load_asr_model()...")
    try:
        signal.alarm(600)
        model.load_asr_model()
        checkpoint("ASR model initialized.")
        asr_downloaded_from_hf = True
    except TimeoutException:
        checkpoint("ERROR: ASR model loading TIMED OUT.")
    except Exception as e:
        checkpoint(f"ASR model pre-load note: {e}")
    finally:
        signal.alarm(0)
    
    # Cache models to Google Drive for next time
    checkpoint("Entering model caching phase...")
    service = get_drive_service()
    if service:
        # Cache OmniVoice model
        if model_path == 'k2-fsa/OmniVoice':
            try:
                checkpoint("Downloading snapshot for OmniVoice to cache to Drive...")
                from huggingface_hub import snapshot_download
                hf_local = snapshot_download(repo_id='k2-fsa/OmniVoice')
                checkpoint(f"Snapshot downloaded to {hf_local}. Uploading to Drive...")
                # Set a 5 min limit for upload
                signal.alarm(300)
                try:
                    upload_model_to_drive(service, hf_local, folder_name="OmniVoice_model")
                finally:
                    signal.alarm(0)
            except Exception as e:
                checkpoint(f"Could not cache OmniVoice model to Drive: {e}")
        
        # Cache ASR model
        if asr_downloaded_from_hf:
            try:
                import upload_results
                asr_folder_id = upload_results.get_drive_folder_id(service, "OmniVoice_ASR_model")
                if not asr_folder_id:
                    checkpoint("ASR model not on Drive. Searching HF cache for upload...")
                    # Find the ASR model in HF cache and upload
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
                                        checkpoint(f"Caching ASR model to Google Drive from {asr_path}...")
                                        signal.alarm(300)
                                        try:
                                            upload_model_to_drive(service, asr_path, folder_name="OmniVoice_ASR_model")
                                        finally:
                                            signal.alarm(0)
                                        break
            except Exception as e:
                checkpoint(f"Could not cache ASR model to Drive: {e}")
    
    checkpoint("Model initialization and caching complete. Starting processing loop.")
    
    upload_script = os.path.join(script_dir, "upload_results.py")

    batch_size = 5
    round_num = 0

    while True:
        round_num += 1
        print(f"\n{'#'*40}", flush=True)
        print(f"  ROUND {round_num} — Fetching fresh list from Drive", flush=True)
        print(f"{'#'*40}", flush=True)

        # Round 1: use existing Drive list if available
        # Round 2+: always generate a fresh AI list
        famous_people_data = get_famous_people_from_drive(
            "famous_people.txt",
            force_regenerate=(round_num > 1)
        )

        if not famous_people_data:
            print("No people found. Waiting 60s before retrying...", flush=True)
            time.sleep(60)
            continue

        # Split into batches of 5
        batches = [famous_people_data[i:i+batch_size] for i in range(0, len(famous_people_data), batch_size)]

        for batch_idx, batch in enumerate(batches):
            print(f"\n{'='*40}", flush=True)
            print(f"  Batch {batch_idx+1}/{len(batches)} of Round {round_num}", flush=True)
            print(f"{'='*40}", flush=True)

            for item in batch:
                if "|" in item:
                    person, sample_text = item.split("|", 1)
                    person = person.strip()
                    sample_text = sample_text.strip()
                else:
                    person = item.strip()
                    sample_text = "You're so lucky. You are so lucky to be an opera singer. I mean this."

                print(f"\nProcessing: {person}", flush=True)

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
                                print(f"Skipping {person} — cloned.wav already exists on Google Drive.", flush=True)
                                continue
                temp_base = os.path.join(script_dir, "temp_workspace")
                os.makedirs(temp_base, exist_ok=True)
                folder_path = os.path.join(temp_base, folder_name)
                os.makedirs(folder_path, exist_ok=True)

                full_wav = os.path.join(folder_path, "full.wav")
                ref_wav = os.path.join(folder_path, "ref.wav")
                cloned_wav = os.path.join(folder_path, "cloned.wav")

                search_info_txt = os.path.join(folder_path, "search_info.txt")
                # Clear previous run's files so we re-process fresh each round
                for f in [full_wav, ref_wav, cloned_wav, search_info_txt]:
                    if os.path.exists(f):
                        os.remove(f)

                # Download
                print(f"Downloading audio for {person}...", flush=True)
                query = f"{person} speaking speech"
                cookies_file = os.path.join(script_dir, "cookies.txt")

                def build_cmd(search_prefix, use_cookies=False, _query=query, _full_wav=full_wav, _cookies_file=cookies_file):
                    cmd = [
                        sys.executable, "-m", "yt_dlp",
                        f"{search_prefix}{_query}",
                        "-f", "worst",
                        "-x", "--audio-format", "wav",
                        "-o", _full_wav,
                        "--write-info-json",
                        "--no-playlist", "--retries", "3", "--socket-timeout", "30"
                    ]
                    is_youtube = search_prefix.startswith("ytsearch")
                    if use_cookies and is_youtube and _is_valid_cookies_file(_cookies_file):
                        cmd += ["--cookies", _cookies_file]
                    proxy = os.environ.get("YTDLP_PROXY")
                    if proxy:
                        cmd += ["--proxy", proxy]
                    return cmd

                downloaded = False
                
                # Try YouTube with cookies first
                if _is_valid_cookies_file(cookies_file):
                    print("Trying YouTube with cookies...", flush=True)
                    result = subprocess.run(build_cmd("ytsearch1:", use_cookies=True), check=False, capture_output=True, text=True)
                    if result.returncode == 0 and os.path.exists(full_wav):
                        downloaded = True
                        print("Downloaded from YouTube (with cookies).", flush=True)
                    else:
                        print(f"YouTube with cookies failed:\n{result.stderr[-300:]}", flush=True)

                # Try YouTube without cookies
                if not downloaded:
                    print("Trying YouTube without cookies...", flush=True)
                    result = subprocess.run(build_cmd("ytsearch1:"), check=False, capture_output=True, text=True)
                    if result.returncode == 0 and os.path.exists(full_wav):
                        downloaded = True
                        print("Downloaded from YouTube (no cookies).", flush=True)
                    else:
                        print(f"YouTube without cookies failed:\n{result.stderr[-300:]}", flush=True)

                # Try SoundCloud as last resort
                if not downloaded:
                    print("Trying SoundCloud...", flush=True)
                    sc_cmd = build_cmd("scsearch3:", _query=f"{person} speech")
                    result = subprocess.run(sc_cmd, check=False, capture_output=True, text=True)
                    if result.returncode == 0 and os.path.exists(full_wav):
                        downloaded = True
                        print(f"Downloaded from SoundCloud.", flush=True)
                    else:
                        print(f"SoundCloud failed:\n{result.stderr[-500:]}", flush=True)


                if not downloaded:
                    print(f"Skipping {person} — could not download audio.", flush=True)
                    continue

                # Get URL and save search info
                info_url = "URL not found"
                json_path1 = full_wav.replace('.wav', '.info.json')
                json_path2 = full_wav + '.info.json'
                for jp in [json_path1, json_path2]:
                    if os.path.exists(jp):
                        try:
                            import json
                            with open(jp, 'r', encoding='utf-8') as f:
                                info_data = json.load(f)
                                info_url = info_data.get('webpage_url', info_url)
                        except Exception as e:
                            print(f"Could not read info json {jp}: {e}", flush=True)
                        try:
                            os.remove(jp)
                        except: pass

                with open(search_info_txt, "w", encoding="utf-8") as f:
                    f.write(f"Keywords: {query}\n")
                    f.write(f"URL: {info_url}\n")

                # VAD
                success = extract_clear_speech(full_wav, ref_wav, target_duration=8.0)
                if not success:
                    print(f"Failed to find clear speech for {person}. Uploading to Google Drive for review.", flush=True)
                    try:
                        subprocess.run([
                            "python", upload_script,
                            folder_path, "--name", folder_name, "--parent", "1bAgeolSPr9rHKL3xCi7FwHusm19N9Iq6"
                        ], check=True)
                        print(f"Uploaded review files for {person} to Google Drive.", flush=True)
                    except Exception as e:
                        print(f"Review upload failed for {person}: {e}", flush=True)
                    continue

                # Clone
                try:
                    print(f"Cloning voice for {person}...", flush=True)
                    audio = model.generate(text=sample_text, ref_audio=ref_wav)
                    sf.write(cloned_wav, audio[0], 24000)
                    print(f"Cloned successfully: {person}", flush=True)
                except Exception as e:
                    print(f"Failed to clone {person}: {e}", flush=True)
                    continue

                # Upload
                try:
                    subprocess.run([
                        "python", upload_script,
                        folder_path, "--name", folder_name, "--parent", "1bAgeolSPr9rHKL3xCi7FwHusm19N9Iq6",
                        "--exclude", "full.wav"
                    ], check=True)
                    print(f"Uploaded {person} to Google Drive.", flush=True)
                except subprocess.CalledProcessError as e:
                    print(f"Upload failed for {person}: {e}", flush=True)

            print(f"\nBatch {batch_idx+1} complete. Pausing 5s before next batch...", flush=True)
            time.sleep(5)

        print(f"\nRound {round_num} complete. Starting next round immediately...", flush=True)


if __name__ == "__main__":
    main()
