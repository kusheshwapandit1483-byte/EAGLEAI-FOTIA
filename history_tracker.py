import threading
import time
import requests
import datetime
import json

# Configuration
FIREBASE_DB_URL = "https://eagleai-fotia-default-rtdb.asia-southeast1.firebasedatabase.app"
POLL_INTERVAL = 5  # Seconds - Increased to reduce load
HISTORY_RETENTION_DAYS = 30

class HistoryTracker:
    def __init__(self):
        self.running = False
        self.thread = None
        self.previous_states = {} # Store last known state of pumps { 'main': {'status': 'OFF', 'mode': 'AUTO'}, ... }
        self.previous_tank_status = "NORMAL" # NORMAL or CRITICAL
        self.previous_diesel_status = "NORMAL"
        self.previous_battery_status = "NORMAL"
        self.previous_pressure_status = "NORMAL"

    def start(self):
        """Starts the background tracking thread."""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()
            print("History Tracker Started.")

    def stop(self):
        """Stops the background tracking thread."""
        self.running = False
        if self.thread:
            self.thread.join()

    def _run_loop(self):
        """Main polling loop."""
        last_cleanup_time = 0
        
        while self.running:
            try:
                # 1. Fetch Live Data
                data = self._get_latest_live_data()
                if data:
                    if 'pumps' in data:
                        self._check_pumps(data['pumps'])
                    
                    # Check Sensors
                    self._check_tank(data)
                    self._check_diesel(data)
                    self._check_battery(data)
                    self._check_pressure(data)

                # 2. Daily Cleanup (Every 24 hours)
                if time.time() - last_cleanup_time > 86400: 
                    self._cleanup_old_history()
                    last_cleanup_time = time.time()

            except Exception as e:
                print(f"History Tracker Error: {e}")
            
            time.sleep(POLL_INTERVAL)

    def _get_latest_live_data(self):
        try:
            # Fetch only the last entry to minimize bandwidth
            response = requests.get(f"{FIREBASE_DB_URL}/live_data.json?orderBy=\"$key\"&limitToLast=1")
            if response.status_code == 200 and response.json():
                raw = response.json()
                key = list(raw.keys())[0]
                return raw[key]
        except:
            return None
        return None

    def _check_tank(self, data):
        """Checks tank level against critical threshold (95)."""
        # Support both keys as per dashboard.js
        level = float(data.get('waterLevel') or data.get('tank_level') or 0)
        
        current_status = "CRITICAL" if level < 95 else "NORMAL"
        
        if self.previous_tank_status != current_status:
            # State change detected
            if current_status == "CRITICAL":
                self._log_event(
                    "Water Tank",
                    "ALARM",
                    f"Critical Level Detected: {level}%",
                    {"level": level, "threshold": 95}
                )
            else:
                self._log_event(
                    "Water Tank",
                    "STATUS_CHANGE",
                    f"Level Restored to Normal: {level}%",
                    {"level": level, "threshold": 95}
                )
            
            self.previous_tank_status = current_status

    def _check_diesel(self, data):
        """Checks diesel level against critical threshold (95)."""
        level = float(data.get('dieselLevel') or data.get('diesel_level') or 0)
        current_status = "CRITICAL" if level < 95 else "NORMAL"
        
        if self.previous_diesel_status != current_status:
            if current_status == "CRITICAL":
                self._log_event("Diesel Tank", "ALARM", f"Critical Level Detected: {level}%", {"level": level})
            else:
                self._log_event("Diesel Tank", "STATUS_CHANGE", f"Level Restored to Normal: {level}%", {"level": level})
            self.previous_diesel_status = current_status

    def _check_battery(self, data):
        """Checks battery voltage (Range: 11.8 - 14.2)."""
        volts = float(data.get('batteryVoltage') or data.get('battery_voltage') or 0)
        # Critical if below 11.8 or above 14.2
        current_status = "CRITICAL" if (volts < 11.8 or volts > 14.2) else "NORMAL"
        
        if self.previous_battery_status != current_status:
            if current_status == "CRITICAL":
                msg = f"Low Voltage: {volts}V" if volts < 11.8 else f"High Voltage: {volts}V"
                self._log_event("Battery System", "ALARM", msg, {"voltage": volts})
            else:
                self._log_event("Battery System", "STATUS_CHANGE", f"Voltage Normal: {volts}V", {"voltage": volts})
            self.previous_battery_status = current_status

    def _check_pressure(self, data):
        """Checks system pressure (Threshold: < 6.0 Bar)."""
        pressure = float(data.get('pressure') or 0)
        current_status = "CRITICAL" if pressure < 6.0 else "NORMAL"
        
        if self.previous_pressure_status != current_status:
            if current_status == "CRITICAL":
                self._log_event("System Pressure", "ALARM", f"Low Pressure Detected: {pressure} Bar", {"pressure": pressure})
            else:
                self._log_event("System Pressure", "STATUS_CHANGE", f"Pressure Normal: {pressure} Bar", {"pressure": pressure})
            self.previous_pressure_status = current_status

    def _check_pumps(self, bumps_data):
        """Checks for state changes in pumps (Status, Mode)."""
        # Expected pump keys: main, jockey, sprinkler, diesel
        for pump_name, pump_info in bumps_data.items():
            current_status = pump_info.get('status', 'OFF').upper()
            current_mode = pump_info.get('mode', 'AUTO').upper()
            
            # Initialize previous state if not present
            if pump_name not in self.previous_states:
                self.previous_states[pump_name] = {
                    'status': current_status, 
                    'mode': current_mode
                }
                continue

            prev_info = self.previous_states[pump_name]
            prev_status = prev_info.get('status', 'OFF')
            prev_mode = prev_info.get('mode', 'AUTO')

            # 1. DETECT STATUS CHANGE
            if prev_status != current_status:
                self._log_event(
                    pump_name, 
                    "STATUS_CHANGE", 
                    f"Status changed to {current_status}",
                    {"from": prev_status, "to": current_status}
                )
                self.previous_states[pump_name]['status'] = current_status

            # 2. DETECT MODE CHANGE
            if prev_mode != current_mode:
                self._log_event(
                    pump_name, 
                    "MODE_CHANGE", 
                    f"Mode changed to {current_mode}",
                    {"from": prev_mode, "to": current_mode}
                )
                self.previous_states[pump_name]['mode'] = current_mode

    def _log_event(self, pump_name, event_type, message, details=None):
        """Pushes a new generic event record to Firebase."""
        
        now = time.time()
        record = {
            "timestamp": int(now * 1000), # JS Timestamp
            "date_formatted": datetime.datetime.fromtimestamp(now).strftime('%Y-%m-%d %H:%M:%S'),
            "pump_name": pump_name.capitalize(),
            "event_type": event_type, # STATUS_CHANGE, MODE_CHANGE, ALARM
            "message": message,
            "details": details or {}
        }
        
        try:
            requests.post(f"{FIREBASE_DB_URL}/history.json", json=record)
            print(f"Recorded Event: [{record['date_formatted']}] {pump_name}: {message}")
        except Exception as e:
            print(f"Failed to save history: {e}")

    def _cleanup_old_history(self):
        """Deletes history records older than HISTORY_RETENTION_DAYS."""
        try:
            print("Running History Cleanup...")
            cutoff_timestamp = (time.time() - (HISTORY_RETENTION_DAYS * 86400)) * 1000
            
            # Query by timestamp
            query = f'{FIREBASE_DB_URL}/history.json?orderBy="timestamp"&endAt={cutoff_timestamp}'
            response = requests.get(query)
            
            if response.status_code == 200 and response.json():
                items_to_delete = response.json()
                for key in items_to_delete:
                    requests.delete(f"{FIREBASE_DB_URL}/history/{key}.json")
                print(f"Deleted {len(items_to_delete)} old history records.")
        except Exception as e:
            print(f"Cleanup Error: {e}")
