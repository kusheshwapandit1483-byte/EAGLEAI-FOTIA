import requests
import json

FIREBASE_URL = "https://eagleai-fotia-default-rtdb.asia-southeast1.firebasedatabase.app"
DATA_PATH = "live_data"

def check_data():
    url = f"{FIREBASE_URL}/{DATA_PATH}.json?orderBy=\"$key\"&limitToLast=1"
    print(f"Fetching from: {url}")
    
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data:
                key = list(data.keys())[0]
                value = data[key]
                print(f"Key: {key}")
                print(f"Has 'lastUpdated'?: {'lastUpdated' in value}")
                if 'lastUpdated' in value:
                    print(f"lastUpdated value: {value['lastUpdated']}")
                else:
                    print("Keys found:", value.keys())
            else:
                print("No data found.")
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    check_data()
