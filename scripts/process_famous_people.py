import os
import sys

# Use home IP via SSH SOCKS proxy
os.environ["YTDLP_PROXY"] = "socks5://127.0.0.1:1080"
os.environ["http_proxy"] = "socks5://127.0.0.1:1080"
os.environ["https_proxy"] = "socks5://127.0.0.1:1080"

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

def checkpoint(msg, **kwargs):
    """Print timestamped message to track execution progress."""
    ts = datetime.now().strftime("%H:%M:%S")
    kwargs.setdefault("flush", True)
    print(f"[{ts}] CHECKPOINT: {msg}", **kwargs)

class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutException("Operation timed out!")

def check_proxy_readiness():
    """Verify that the SSH SOCKS proxy is actually working."""
    checkpoint("Checking SOCKS proxy readiness...")
    proxies = {
        "http": "socks5://127.0.0.1:1080",
        "https": "socks5://127.0.0.1:1080",
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
PROCESSED_PEOPLE = set()
MATERIALS_FOLDER_ID = "1bAgeolSPr9rHKL3xCi7FwHusm19N9Iq6"

def fetch_processed_people(service):
    """Fetch all folder names from the materials directory that HAVE a ref.wav file."""
    global PROCESSED_PEOPLE
    if not service:
        return
    
    checkpoint(f"Fetching processed people list from Drive (Folder: {MATERIALS_FOLDER_ID})...")
    try:
        import upload_results
        
        # 1. Get or create the 'materials' subfolder
        materials_id = upload_results.get_drive_folder_id(service, "materials", MATERIALS_FOLDER_ID)
        if not materials_id:
            materials_id = upload_results.create_drive_folder(service, "materials", MATERIALS_FOLDER_ID)
            
        folders = upload_results.get_drive_folder_contents(service, materials_id) if materials_id else {}
        if not folders:
            PROCESSED_PEOPLE = set()
            checkpoint("No processed folders found.")
            return

        # 2. Search for all 'ref.wav' files to see which folders they belong to
        # This is more efficient than listing every subfolder individually
        ref_parents = set()
        page_token = None
        while True:
            results = service.files().list(
                q="name = 'ref.wav' and trashed = false",
                fields="nextPageToken, files(parents)",
                pageToken=page_token,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            for f in results.get('files', []):
                if f.get('parents'):
                    ref_parents.update(f['parents'])
            page_token = results.get('nextPageToken')
            if not page_token:
                break
        
        # 3. Only count as processed if the folder name exists AND it has a ref.wav
        processed = set()
        missing_ref = []
        for name, info in folders.items():
            if info['id'] in ref_parents:
                processed.add(name.replace("_", " ").strip().lower())
            else:
                missing_ref.append(name)
        
        PROCESSED_PEOPLE = processed
        if missing_ref:
            checkpoint(f"Folders missing ref.wav (will re-process): {', '.join(missing_ref)}")
        checkpoint(f"Found {len(PROCESSED_PEOPLE)} fully processed individuals (with ref.wav) in 'materials' subfolder.")
    except Exception as e:
        checkpoint(f"Could not fetch processed people list: {e}")

def sync_drive_to_api(service):
    """Sync downloaded voices from Google Drive to the local OmniVoice API so they appear in the UI."""
    checkpoint("Checking local API for missing voices from Drive...")
    api_url = os.environ.get("OMNIVOICE_API_URL", "http://localhost:8000")
    try:
        resp = requests.get(f"{api_url}/gallery/voices", timeout=10)
        if resp.status_code != 200:
            checkpoint("API not ready or reachable, skipping sync.")
            return
        local_voices = resp.json()
        local_names = {v['name'].lower() for v in local_voices}
    except Exception as e:
        checkpoint(f"Could not reach API: {e}")
        return
        
    import upload_results
    materials_id = upload_results.get_drive_folder_id(service, "materials", MATERIALS_FOLDER_ID)
    if not materials_id:
        return
    folders = upload_results.get_drive_folder_contents(service, materials_id)
    
    synced_count = 0
    for name, info in folders.items():
        clean_name = name.replace("_", " ").strip()
        if clean_name.lower() in local_names:
            continue
            
        # Missing from API, check if it has a ref.wav
        person_contents = upload_results.get_drive_folder_contents(service, info['id'])
        if "ref.wav" in person_contents:
            checkpoint(f"Syncing '{clean_name}' from Drive to local API...")
            try:
                file_id = person_contents["ref.wav"]['id']
                from googleapiclient.http import MediaIoBaseDownload
                request = service.files().get_media(fileId=file_id)
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    _, done = downloader.next_chunk()
                fh.seek(0)
                
                requests.post(
                    f"{api_url}/gallery/upload",
                    data={
                        "name": clean_name,
                        "character": clean_name,
                        "category": "Celebs",
                        "description": "Synced from Google Drive"
                    },
                    files={"audio": ("ref.wav", fh, "audio/wav")},
                    timeout=30
                )
                synced_count += 1
            except Exception as e:
                checkpoint(f"Failed to sync '{clean_name}' to API: {e}")
                
    if synced_count > 0:
        checkpoint(f"Successfully synced {synced_count} voices to the UI.")
    else:
        checkpoint("Local API is up to date with Google Drive.")

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
        
        # Increase socket timeout for model loading
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(300)
        
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
            socket.setdefaulttimeout(old_timeout)
    return _VAD_MODEL, _VAD_UTILS

def detect_gender_from_pitch(wav_tensor, sample_rate):
    """Detect gender based on mean pitch (F0)."""
    import torchaudio.functional as F
    try:
        # Detect pitch contour
        # Use a reasonable range for human voice (50Hz - 500Hz)
        pitch = F.detect_pitch_frequency(wav_tensor, sample_rate)
        voiced_pitch = pitch[pitch > 0]
        if voiced_pitch.numel() == 0:
            return "unknown"
        
        mean_pitch = voiced_pitch.mean().item()
        # Typical thresholds: Male: 85-155Hz, Female: 165-255Hz
        # We'll use 160Hz as a threshold
        if mean_pitch > 160:
            return "female", mean_pitch
        else:
            return "male", mean_pitch
    except Exception as e:
        print(f"Pitch detection error: {e}")
        return "unknown", 0

def extract_clear_speech(full_wav_path, ref_wav_path, target_duration=8.0, asr_model=None, person_name=None, target_gender=None):
    print(f"Using AI (Silero VAD) to find clear speech in {full_wav_path} (Target Gender: {target_gender})...", flush=True)
    model, utils = get_vad_model()
    if model is None or utils is None:
        print("ERROR: VAD model could not be loaded. Skipping clear speech extraction.", flush=True)
        return False
    get_speech_timestamps = utils[0]
    
    try:
        data, samplerate = sf.read(full_wav_path)
    except Exception as e:
        print(f"Error reading audio: {e}", flush=True)
        return False
        
    if len(data) == 0:
        print("Audio data is empty.", flush=True)
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
        
    speech_timestamps = get_speech_timestamps(
        wav_16k, 
        model, 
        sampling_rate=16000, 
        threshold=0.85,
        min_speech_duration_ms=1000,
        min_silence_duration_ms=1000
    )
    
    if not speech_timestamps:
        print("No speech detected by AI.", flush=True)
        return False
        
    target_samples_16k = int(target_duration * 16000)
    best_segment = None
    
    import tempfile
    
    # Skip segments in the first 30 seconds — these are usually host/narrator intros
    intro_cutoff_16k = 30 * 16000
    non_intro_timestamps = [ts for ts in speech_timestamps if ts['start'] >= intro_cutoff_16k]
    
    if non_intro_timestamps:
        print(f"Skipping first 30s intro zone. {len(speech_timestamps)} total segments -> {len(non_intro_timestamps)} after intro cutoff.", flush=True)
        candidates_pool = non_intro_timestamps
    else:
        print("All speech is within the first 30s. Using all segments.", flush=True)
        candidates_pool = speech_timestamps
    
    # Sort candidates by start time (later segments = more likely the actual person speaking)
    # Among segments starting at similar times, prefer longer ones
    candidates = sorted(candidates_pool, key=lambda x: (x['start'], x['end'] - x['start']), reverse=False)
    
    valid_candidates = []
    
    try:
        import langdetect
    except ImportError:
        langdetect = None
    
    for ts in candidates:
        length = ts['end'] - ts['start']
        if length < 16000 * 3: # Skip segments shorter than 3 seconds
            continue
            
        start_sample = int(ts['start'] * samplerate / 16000)
        end_sample = int(ts['end'] * samplerate / 16000)
        
        # Check transcription if ASR model is provided
        is_clean = True
        lang = 'en'
        
        if asr_model:
            # Extract a chunk for checking (up to 10 seconds)
            check_end_sample = min(end_sample, start_sample + int(10 * samplerate))
            extracted_data = data[start_sample:check_end_sample]
            
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name
            sf.write(tmp_path, extracted_data, samplerate)
            
            try:
                text = asr_model.transcribe(tmp_path).lower()
                segment_time = start_sample / samplerate
                print(f"Candidate transcription ({segment_time:.1f}s): {text}", flush=True)
                
                bad_tags = ["[applause]", "(applause)", "[music]", "(music)", "[laughter]", "(laughter)",
                            "[cheering]", "(cheering)", "[crowd]", "(crowd)"]
                intro_phrases = [
                    "please welcome", "here is", "introducing", "ladies and gentlemen",
                    "today we have", "our guest", "joining us", "let me introduce",
                    "welcome to", "i'm joined by", "next up", "we're joined by",
                    "put your hands together", "give it up for", "round of applause",
                    "my next guest", "our next guest", "special guest",
                    "here to talk", "here to discuss", "here with us",
                    "welcome back", "thanks for joining", "thank you for joining",
                    "it's my pleasure", "it is my pleasure", "i'd like to welcome",
                    "let's welcome", "now i'd like", "now i would like",
                    "with me today", "with us today", "on the show today",
                    "coming up next", "stay tuned", "subscribe",
                ]
                if any(tag in text for tag in bad_tags):
                    print("Found applause/music/laughter tag. Skipping.", flush=True)
                    is_clean = False
                elif len(text.split()) < 3:
                    print("Too few words. Skipping.", flush=True)
                    is_clean = False
                elif person_name and person_name.lower() in text:
                    print(f"Found person's name '{person_name}' in text, likely an intro. Skipping.", flush=True)
                    is_clean = False
                elif any(phrase in text for phrase in intro_phrases):
                    print(f"Found intro/host phrase in text. Skipping.", flush=True)
                    is_clean = False

                if is_clean:
                    if langdetect:
                        try:
                            lang = langdetect.detect(text)
                            print(f"Detected language: {lang}", flush=True)
                        except:
                            pass
                
                # Check gender if target_gender is provided
                if is_clean and target_gender:
                    # Convert to tensor for gender detection
                    extracted_tensor = torch.tensor(extracted_data, dtype=torch.float32)
                    if extracted_tensor.ndim > 1:
                        extracted_tensor = extracted_tensor.mean(dim=0)
                    
                    detected_gender, pitch_hz = detect_gender_from_pitch(extracted_tensor.unsqueeze(0), samplerate)
                    print(f"Detected gender: {detected_gender} ({pitch_hz:.1f} Hz)", flush=True)
                    
                    if detected_gender != "unknown" and detected_gender.lower() != target_gender.lower():
                        print(f"Gender mismatch: expected {target_gender}, detected {detected_gender}. Skipping (likely host).", flush=True)
                        is_clean = False
            except Exception as e:
                print(f"Transcribe or gender check error: {e}", flush=True)
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
        
        if is_clean:
            # If we found a non-English segment, it's highly likely the original foreign speaker! Stop immediately.
            if lang != 'en':
                best_segment = {'start': ts['start'], 'end': ts['end']}
                if best_segment['end'] - best_segment['start'] > target_samples_16k:
                    best_segment['end'] = best_segment['start'] + target_samples_16k
                print(f"Found non-English speech at {ts['start']/16000:.1f}s — using this (likely the actual person).", flush=True)
                break
            else:
                # Save the clean English segment as a candidate
                valid_candidates.append(ts)
                if len(valid_candidates) >= 3:
                    # Checked 3 clean English segments, probably an English speaker. Stop searching.
                    break
            
    if not best_segment:
        if valid_candidates:
            # Pick the LATEST clean segment (furthest from intro) that is long enough
            # Sort by start time descending — later segments are more likely the actual person
            later_candidates = sorted(valid_candidates, key=lambda x: x['start'], reverse=True)
            chosen = later_candidates[0]
            print(f"Using latest clean English segment at {chosen['start']/16000:.1f}s (avoiding early intro zone).", flush=True)
            best_segment = {'start': chosen['start'], 'end': chosen['end']}
            if best_segment['end'] - best_segment['start'] > target_samples_16k:
                best_segment['end'] = best_segment['start'] + target_samples_16k
        else:
            # Fallback to the latest segment (furthest from intro)
            latest = sorted(candidates, key=lambda x: x['start'], reverse=True)
            print(f"No fully clean segment found, falling back to latest segment at {latest[0]['start']/16000:.1f}s.", flush=True)
            best_segment = latest[0]
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
    
    avoid_list = list(PROCESSED_PEOPLE)
    if not avoid_list and service:
        fetch_processed_people(service)
        avoid_list = list(PROCESSED_PEOPLE)

    prompt = (
        f"Generate a list of 20 of the most famous and recognizable CURRENTLY ALIVE top world leaders for the year 2026. "
        f"Include potential or incoming leaders, and explicitly include leaders from Asia such as Japan, South Korea, and Taiwan, alongside extremely well-known figures like Donald Trump, Emmanuel Macron, etc. "
        f"DO NOT include anyone who is deceased. "
    )
    
    if avoid_list:
        # Pass all names from the avoid list to ensure no repeats
        avoid_str = ", ".join(avoid_list)
        prompt += f"EXTREMELY IMPORTANT: DO NOT include any of the following people as they have already been processed: {avoid_str}. "
        
    prompt += (
        f"Provide a famous quote, the gender ('male' or 'female'), and the country they represent for each person. "
        f"Format each line exactly as 'Name|Quote|Gender|Country'. "
        f"Do not include numbering, bullet points, or any other text."
    )
    
    people = []

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
                people = [line.strip('-1234567890. ') for line in content.split('\n') if line.strip()]
            else:
                print(f"GitHub Models API error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"GitHub Models generation failed: {e}")
    else:
        print("DEBUG: No github_token found in environment.")

    # Try Cloudflare Workers AI if CLOUDFLARE_ACCOUNTS_JSON exists
    cf_accounts_env = os.environ.get("CLOUDFLARE_ACCOUNTS_JSON")
    if not people and cf_accounts_env:
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
                        people = [line.strip('-1234567890. ') for line in content.split('\n') if line.strip()]
                    else:
                        print(f"Cloudflare AI failed: {data.get('errors')}")
                else:
                    print(f"Cloudflare API error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Cloudflare AI exception: {e}")
    elif not people:
        print("DEBUG: No CLOUDFLARE_ACCOUNTS_JSON found.")

    # Try OpenAI if OPENAI_API_KEY exists
    api_key = os.environ.get("OPENAI_API_KEY")
    if not people and api_key:
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
                people = [line.strip('-1234567890. ') for line in content.split('\n') if line.strip()]
            else:
                print(f"OpenAI API error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"OpenAI generation failed: {e}")
    elif not people:
        print("DEBUG: No OPENAI_API_KEY found.")
            
    # Try local Ollama
    if not people:
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
                people = [line.strip('-1234567890. ') for line in content.split('\n') if line.strip()]
        except Exception as e:
            # Don't print Ollama connection errors in CI or if it's clearly not there
            is_conn_error = any(msg in str(e).lower() for msg in ["connection refused", "failed to establish a new connection"])
            if 'GITHUB_ACTIONS' not in os.environ and not is_conn_error:
                print(f"Ollama generation failed: {e}")
            elif is_conn_error:
                # Quietly note that local AI is unavailable
                pass
        
    if not people:
        print("AI generation failed for this round. Using fallback list.", flush=True)
        # Add a small delay if AI fails to prevent rapid looping
        time.sleep(5)

    fallback = [
        "Joe Biden|The future belongs to those who believe in the beauty of their dreams.|male|United States",
        "Rishi Sunak|Integrity and professionalism are my top priorities.|male|United Kingdom",
        "Justin Trudeau|Diversity is our strength.|male|Canada",
        "Narendra Modi|Individual effort can make a big difference.|male|India",
        "Volodymyr Zelenskyy|We are all here, our soldiers are here, citizens are here.|male|Ukraine",
        "Elon Musk|When something is important enough, you do it even if the odds are not in your favor.|male|United States",
        "Bill Gates|Success is a lousy teacher. It seduces smart people into thinking they can't lose.|male|United States",
        "Jeff Bezos|Your brand is what other people say about you when you're not in the room.|male|United States",
        "Mark Zuckerberg|The biggest risk is not taking any risk.|male|United States",
        "Tim Cook|Life is fragile. We're not guaranteed a tomorrow so give it everything you've got.|male|United States",
        "Pope Francis|A little bit of mercy makes the world less cold and more just.|male|Vatican City",
        "Dalai Lama|Happiness is not something ready made. It comes from your own actions.|male|Tibet",
        "Malala Yousafzai|One child, one teacher, one book, one pen can change the world.|female|Pakistan",
        "Greta Thunberg|I want you to act as if our house is on fire. Because it is.|female|Sweden",
        "Lionel Messi|You have to fight to reach your dream. You have to sacrifice and work hard for it.|male|Argentina",
        "Cristiano Ronaldo|Your love makes me strong, your hate makes me unstoppable.|male|Portugal",
        "LeBron James|You can't be afraid to fail. It's the only way you succeed.|male|United States",
        "Stephen Curry|Success is not a destination, it's a journey.|male|United States",
        "Lewis Hamilton|I feel like people are expecting me to fail, therefore I expect myself to win.|male|United Kingdom",
        "Serena Williams|I really think a champion is defined not by their wins but by how they can recover when they fall.|female|United States",
        "Taylor Swift|No matter what happens in life, be good to people. Being good to people is a wonderful legacy to leave behind.|female|United States",
        "Beyonce|I don't like to gamble, but if there's one thing I'm willing to bet on, it's myself.|female|United States",
        "Rihanna|It's important to keep your head held high and your heart even higher.|female|Barbados",
        "Adele|I don't make music for eyes. I make music for ears.|female|United Kingdom",
        "Ed Sheeran|Be a true heart, not a follower.|male|United Kingdom",
        "Drake|Tables turn, bridges burn, you live and learn.|male|Canada",
        "Kanye West|I am my own biggest fan.|male|United States",
        "Lady Gaga|Don't you ever let a soul in the world tell you that you can't be exactly who you are.|female|United States",
        "Bruno Mars|I just want to make music and have a good time.|male|United States",
        "Justin Bieber|I want my world to be fun.|male|Canada",
        "Tom Hanks|I've made a lot of movies and some of them were even good.|male|United States",
        "Meryl Streep|The great gift of human beings is that we have the power of empathy.|female|United States",
        "Leonardo DiCaprio|If you can do what you do best and be happy, you're further along in life than most people.|male|United States",
        "Brad Pitt|I'm one of those people you hate because of genetics. It's the truth.|male|United States",
        "Angelina Jolie|Every day we choose who we are by how we define ourselves.|female|United States",
        "Robert Downey Jr.|I know who I am. I'm the dude playin' the dude, disguised as another dude!|male|United States",
        "Scarlett Johansson|I'm not going to apologize for being successful.|female|United States",
        "Will Smith|If you're not making someone else's life better, then you're wasting your time.|male|United States",
        "Dwayne Johnson|Success at anything will always come down to this: focus and effort.|male|United States",
        "Oprah Winfrey|The biggest adventure you can take is to live the life of your dreams.|female|United States",
        "Ellen DeGeneres|Be kind to one another.|female|United States",
        "David Attenborough|It seems to me that the natural world is the greatest source of excitement.|male|United Kingdom",
        "Michelle Obama|Success isn't about how much money you make; it's about the difference you make in people's lives.|female|United States",
        "Hillary Clinton|Women are the largest untapped reservoir of talent in the world.|female|United States",
        "Angela Merkel|Fear was never a good adviser, neither in our personal lives nor in our society.|female|Germany",
        "Emmanuel Macron|Make our planet great again.|male|France",
        "Boris Johnson|My friends, as I have discovered myself, there are no disasters, only opportunities.|male|United Kingdom",
        "Keir Starmer|Country first, party second.|male|United Kingdom",
        "Olaf Scholz|We are living through a watershed era.|male|Germany",
        "Xi Jinping|The people's aspirations for a better life are what we must fight for.|male|China",
        "Fumio Kishida|Japan must take a leading role in maintaining a free and open international order.|male|Japan",
        "Yoon Suk Yeol|Freedom and solidarity are the foundation of our democracy.|male|South Korea",
        "Lai Ching-te|We will continue to defend our democracy and freedom.|male|Taiwan",
        "Lee Jae-myung|We will create a society where everyone has a fair chance.|male|South Korea",
        "Kim Jong Un|Our party will continue to fight for the prosperity of the nation.|male|North Korea",
        "Sanae Takaichi|I am committed to strengthening our national security and economy.|female|Japan"
    ]
    
    random.shuffle(fallback)
    raw_people = fallback[:10]
    
    # Filter AI generated list against processed cache
    if people:
        raw_people = people
    
    filtered_people = []
    for item in raw_people:
        name = item.split("|")[0].strip().lower()
        if name in PROCESSED_PEOPLE:
            checkpoint(f"AI suggested '{name}', but it's already processed. Skipping.")
            continue
        filtered_people.append(item)
    
    return filtered_people

# 1. Get the famous people list from Google Drive or Generate it
def get_famous_people_from_drive(file_name="famous_people.txt", force_regenerate=False):
    service = get_drive_service()

    if not service:
        print("Could not get Google Drive service. Falling back to AI generation without avoid list.", flush=True)
        return generate_famous_people_with_ai(None)

    # Fetch processed people cache first
    fetch_processed_people(service)

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
    
    has_local_weights = any(os.path.exists(os.path.join(local_model_path, f)) for f in ["model.safetensors", "pytorch_model.bin"])
    if os.path.exists(local_model_path) and has_local_weights:
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
        has_asr_weights = os.path.exists(asr_local_path) and any(os.path.exists(os.path.join(asr_local_path, f)) for f in ["model.safetensors", "pytorch_model.bin"])
        if service and not has_asr_weights:
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
        # Sync existing Google Drive materials to the UI DB before starting the loop
        sync_drive_to_api(service)
        
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

        target_person_env = os.environ.get("TARGET_PERSON")
        if target_person_env:
            famous_people_data = [target_person_env]
            print(f"Using specific TARGET_PERSON: {target_person_env}", flush=True)
        else:
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
                    parts = item.split("|")
                    person = parts[0].strip()
                    sample_text = parts[1].strip()
                    target_gender = parts[2].strip() if len(parts) > 2 else None
                    location = parts[3].strip() if len(parts) > 3 else None
                else:
                    person = item.strip()
                    sample_text = "You're so lucky. You are so lucky to be an opera singer. I mean this."
                    target_gender = None
                    location = None

                print(f"\nProcessing: {person} (Gender: {target_gender}, Location: {location})", flush=True)

                folder_name = person.replace(" ", "_")

                # Check if already processed using local cache
                if person.lower() in PROCESSED_PEOPLE:
                    checkpoint(f"Skipping {person} — already in PROCESSED_PEOPLE cache.", flush=True)
                    continue
                
                # Extra check for ref.wav if cache might be stale
                service = get_drive_service()
                if service:
                    import upload_results
                    person_folder_id = upload_results.get_drive_folder_id(service, folder_name, MATERIALS_FOLDER_ID)
                    if person_folder_id:
                        contents = upload_results.get_drive_folder_contents(service, person_folder_id)
                        if "ref.wav" in contents:
                            checkpoint(f"Skipping {person} — ref.wav actually exists on Drive.", flush=True)
                            PROCESSED_PEOPLE.add(person.lower())
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
                        try: os.remove(f)
                        except: pass

                max_attempts = 3
                success = False

                for attempt in range(1, max_attempts + 1):
                    print(f"\n--- Attempt {attempt}/{max_attempts} for {person} ---", flush=True)

                    # Clear files for this attempt
                    for f in [full_wav, ref_wav, search_info_txt]:
                        if os.path.exists(f):
                            try: os.remove(f)
                            except: pass

                    # Download
                    print(f"Downloading audio for {person} (Search index: {attempt})...", flush=True)
                    location_hint = f" {location}" if location else ""
                    query = f"{person}{location_hint} speaking speech original voice -interpreter -dubbed -translated -translator"
                    cookies_file = os.path.join(script_dir, "cookies.txt")

                    def build_cmd(search_type, use_cookies=False, _query=query, _full_wav=full_wav, _cookies_file=cookies_file, item_index=attempt):
                        cmd = [
                            sys.executable, "-m", "yt_dlp",
                            f"{search_type}{item_index}:{_query}",
                            "--playlist-items", str(item_index),
                            "-f", "ba*[language=en]/ba*[language=orig]/ba/worst",
                            "-x", "--audio-format", "wav",
                            "-o", _full_wav,
                            "--write-info-json",
                            "--retries", "3", "--socket-timeout", "30",
                            "--extractor-args", "youtube:player-client=web,android"
                        ]
                        is_youtube = search_type.startswith("ytsearch")
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
                        result = subprocess.run(build_cmd("ytsearch", use_cookies=True), check=False, capture_output=True, text=True)
                        if result.returncode == 0 and os.path.exists(full_wav):
                            downloaded = True
                            print("Downloaded from YouTube (with cookies).", flush=True)
                        else:
                            print(f"YouTube with cookies failed:\n{result.stderr[-300:]}", flush=True)

                    # Try YouTube without cookies
                    if not downloaded:
                        print("Trying YouTube without cookies...", flush=True)
                        result = subprocess.run(build_cmd("ytsearch"), check=False, capture_output=True, text=True)
                        if result.returncode == 0 and os.path.exists(full_wav):
                            downloaded = True
                            print("Downloaded from YouTube (no cookies).", flush=True)
                        else:
                            print(f"YouTube without cookies failed:\n{result.stderr[-300:]}", flush=True)

                    # Try SoundCloud as last resort
                    if not downloaded:
                        print("Trying SoundCloud...", flush=True)
                        sc_cmd = build_cmd("scsearch", _query=f"{person} speech")
                        result = subprocess.run(sc_cmd, check=False, capture_output=True, text=True)
                        if result.returncode == 0 and os.path.exists(full_wav):
                            downloaded = True
                            print(f"Downloaded from SoundCloud.", flush=True)
                        else:
                            print(f"SoundCloud failed:\n{result.stderr[-500:]}", flush=True)


                    if not downloaded:
                        print(f"Skipping {person} — could not download audio on attempt {attempt}.", flush=True)
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
                        f.write(f"Attempt: {attempt}\n")
                        if location:
                            f.write(f"Location: {location}\n")

                    # VAD
                    success = extract_clear_speech(full_wav, ref_wav, target_duration=8.0, asr_model=model, person_name=person, target_gender=target_gender)
                    if success:
                        break # Found clear speech!
                    else:
                        print(f"Failed to find clear speech in attempt {attempt}.", flush=True)

                if not success:
                    print(f"Failed to find clear speech for {person} after {max_attempts} attempts. Uploading to Google Drive for review.", flush=True)
                    try:
                        subprocess.run([
                            "python", upload_script,
                            folder_path, "--name", folder_name, "--parent", MATERIALS_FOLDER_ID, "--parent-name", "materials"
                        ], check=True)
                        print(f"Uploaded review files for {person} to Google Drive 'materials' subfolder.", flush=True)
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

                try:
                    subprocess.run([
                        "python", upload_script,
                        folder_path, "--name", folder_name, "--parent", MATERIALS_FOLDER_ID, "--parent-name", "materials",
                        "--exclude", "full.wav"
                    ], check=True)
                    print(f"Uploaded {person} to Google Drive 'materials' subfolder.", flush=True)
                except subprocess.CalledProcessError as e:
                    print(f"Upload failed for {person}: {e}", flush=True)

                # Upload to local API so it appears in UI instantly
                try:
                    api_url = os.environ.get("OMNIVOICE_API_URL", "http://localhost:8000")
                    with open(ref_wav, "rb") as f:
                        resp = requests.post(
                            f"{api_url}/gallery/upload",
                            data={
                                "name": person,
                                "character": person,
                                "category": "Celebs",
                                "description": f"Generated from YouTube. Location: {location or 'Unknown'}. Search: {query}"
                            },
                            files={"audio": ("ref.wav", f, "audio/wav")},
                            timeout=30
                        )
                    if resp.status_code == 200:
                        print(f"Uploaded {person} to local OmniVoice API.", flush=True)
                    else:
                        print(f"Failed to upload {person} to API: {resp.status_code} {resp.text}", flush=True)
                except Exception as e:
                    print(f"API upload failed for {person}: {e}", flush=True)

            print(f"\nBatch {batch_idx+1} complete. Pausing 5s before next batch...", flush=True)
            time.sleep(5)

        if target_person_env:
            print(f"Finished processing specific TARGET_PERSON: {target_person_env}. Exiting.", flush=True)
            break

        print(f"\nRound {round_num} complete. Starting next round immediately...", flush=True)


if __name__ == "__main__":
    main()
