import time
import requests
import json
import os

# Configuration
FIREBASE_URL = "https://eagleai-fotia-default-rtdb.asia-southeast1.firebasedatabase.app"
DATA_PATH = "live_data"

def monitor():
    print(f"--- [CONNECTING] Firebase Monitor: {FIREBASE_URL} ---")
    print(f"--- [WATCHING] Path: /{DATA_PATH} ---")
    print("Press Ctrl+C to stop.\n")

    last_key = None

    try:
        while True:
            try:
                # Fetch only the latest entry to save bandwidth
                url = f"{FIREBASE_URL}/{DATA_PATH}.json?orderBy=\"$key\"&limitToLast=1"
                response = requests.get(url)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data:
                        # Get the key and value
                        key = list(data.keys())[0]
                        value = data[key]
                        
                        # Only print if it's new data
                        if key != last_key:
                            print(f"\n[{time.strftime('%H:%M:%S')}] 🟢 New Data Received ({key}):")
                            print(json.dumps(value, indent=4))
                            last_key = key
                        else:
                            # print(".", end="", flush=True) # Heartbeat
                            pass
                    else:
                        print(f"\n[{time.strftime('%H:%M:%S')}] ⚠️ No data found at path.")
                else:
                    print(f"\n❌ Error {response.status_code}: {response.text}")

            except Exception as e:
                print(f"\n❌ Connection Error: {e}")

            time.sleep(2) # Refresh rate

    except KeyboardInterrupt:
        print("\n\n🛑 Monitor Stopped.")

if __name__ == "__main__":
    monitor()
