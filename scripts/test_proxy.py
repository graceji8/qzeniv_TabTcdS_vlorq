import os
import requests

# Set proxy environment variables
os.environ["http_proxy"] = "socks5h://127.0.0.1:1080"
os.environ["https_proxy"] = "socks5h://127.0.0.1:1080"

print("Fetching IP address through the SOCKS5 proxy...")
try:
    response = requests.get("https://api.ipify.org", timeout=10)
    print("Success! Your proxied public IP is:", response.text)
except Exception as e:
    print("Error fetching IP:", e)
