import torch
import torchaudio
import os
import sys

def test_vad(audio_path):
    print("Loading VAD model...")
    model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                  model='silero_vad',
                                  force_reload=False,
                                  onnx=False)
    (get_speech_timestamps, save_audio, read_audio, VADIterator, collect_chunks) = utils
    
    import soundfile as sf
    print(f"Reading {audio_path}...")
    try:
        data, samplerate = sf.read(audio_path)
        wav = torch.tensor(data, dtype=torch.float32)
        if wav.ndim > 1:
            wav = wav.mean(dim=1) # convert to mono
        # Silero VAD requires 16000Hz. Let's assume it is, or we can use torchaudio.transforms.Resample if needed.
        # Wait, if sample rate is not 16k, we must resample.
        if samplerate != 16000:
            import torchaudio.transforms as T
            resampler = T.Resample(samplerate, 16000)
            wav = resampler(wav)
            samplerate = 16000
    except Exception as e:
        print(f"Error reading audio: {e}")
        return
        
    print("Getting speech timestamps...")
    speech_timestamps = get_speech_timestamps(wav, model, sampling_rate=16000)
    
    if not speech_timestamps:
        print("No speech detected.")
        return
        
    print("Speech timestamps found:")
    for ts in speech_timestamps:
        print(f"Start: {ts['start']/16000:.2f}s, End: {ts['end']/16000:.2f}s")
        
    # Find the longest continuous speech segment or collect 8 seconds
    # Actually, let's just collect the first few chunks until we have 8 seconds.
    # But silero-vad is good for this!
    
if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_vad(sys.argv[1])
    else:
        print("Provide an audio file path.")
