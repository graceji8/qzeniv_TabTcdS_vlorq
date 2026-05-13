import os
import sys
import json
import time
import subprocess
import threading
import re

# Force UTF-8 for console output
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def heartbeat():
    """Prints a heartbeat message every 5 minutes to keep the logs active."""
    while True:
        print(f"[HEARTBEAT] {time.strftime('%Y-%m-%d %H:%M:%S')} - Server is alive and healthy.")
        sys.stdout.flush()
        time.sleep(300)

def start_omnivoice():
    """Starts the OmniVoice HTTP server."""
    print("Starting OmniVoice HTTP server on port 9000...")
    # Based on common usage, starting the demo server. 
    # Adjust if a different entry point is required.
    cmd = ["omnivoice-demo", "--port", "9000", "--host", "0.0.0.0"]
    try:
        # Run in background
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        # We don't wait for it to finish
        return proc
    except Exception as e:
        print(f"Error starting OmniVoice server: {e}")
        return None

def start_tunnel():
    """Starts the cloudflared tunnel and extracts the public URL."""
    print("Starting cloudflared tunnel...")
    cmd = ["cloudflared", "tunnel", "--url", "http://localhost:9000"]
    
    # cloudflared prints the URL to stderr/stdout
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    
    public_url = None
    
    # Read output line by line to find the URL
    def monitor_output():
        nonlocal public_url
        for line in iter(proc.stdout.readline, ''):
            print(f"[cloudflared] {line.strip()}")
            if "https://" in line and ".trycloudflare.com" in line:
                match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
                if match:
                    public_url = match.group(0)
                    print("\n" + "="*60)
                    print(f"🚀 OMNIVOICE PUBLIC URL: {public_url}")
                    print("="*60 + "\n")
            sys.stdout.flush()

    thread = threading.Thread(target=monitor_output, daemon=True)
    thread.start()
    
    return proc

def main():
    print("--- OmniVoice Server Runner ---")
    
    # 1. Parse Cloudflare Accounts (Optional if KV is dropped, but kept for context)
    cf_json = os.environ.get("CLOUDFLARE_ACCOUNTS_JSON")
    if cf_json:
        try:
            accounts = json.loads(cf_json)
            if accounts:
                print(f"Found {len(accounts)} Cloudflare account(s) in configuration.")
                # We could use account details here if needed for named tunnels or KV
        except Exception as e:
            print(f"Note: Could not parse CLOUDFLARE_ACCOUNTS_JSON: {e}")

    # 2. Start heartbeat thread
    h_thread = threading.Thread(target=heartbeat, daemon=True)
    h_thread.start()
    
    # 3. Start OmniVoice
    server_proc = start_omnivoice()
    if not server_proc:
        print("Failed to start server. Exiting.")
        sys.exit(1)
        
    # Give the server a few seconds to warm up
    time.sleep(5)
    
    # 4. Start Tunnel
    tunnel_proc = start_tunnel()
    
    # 5. Keep alive (up to 6 hours for GitHub Actions limit)
    start_time = time.time()
    max_duration = 5.8 * 3600  # 5 hours 48 minutes
    
    print(f"Runner will stay active for up to 6 hours.")
    
    try:
        while time.time() - start_time < max_duration:
            # Check if processes are still running
            if server_proc.poll() is not None:
                print("OmniVoice server process exited unexpectedly!")
                break
            if tunnel_proc.poll() is not None:
                print("Cloudflared tunnel process exited unexpectedly!")
                break
            time.sleep(60)
    except KeyboardInterrupt:
        print("Shutdown requested...")
    finally:
        print("Cleaning up...")
        if server_proc: server_proc.terminate()
        if tunnel_proc: tunnel_proc.terminate()
        print("Done.")

if __name__ == "__main__":
    main()
