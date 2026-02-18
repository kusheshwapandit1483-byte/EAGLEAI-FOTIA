import requests
import hashlib
import uuid
import json
import time

# Configuration
# Using the same default URL as app.py for the system metadata
SYSTEM_DB_URL = "https://eagleai-fotia-default-rtdb.asia-southeast1.firebasedatabase.app"

# --- CACHE CONFIGURATION ---
AUTH_CACHE = {}
AUTH_CACHE_TTL = 300  # 5 minutes

def get_from_cache(key):
    """Retrieves value from cache if valid."""
    if key in AUTH_CACHE:
        data, timestamp = AUTH_CACHE[key]
        if time.time() - timestamp < AUTH_CACHE_TTL:
            return data
        else:
            del AUTH_CACHE[key] # Expired
    return None

def set_to_cache(key, data):
    """Sets value in cache with current timestamp."""
    AUTH_CACHE[key] = (data, time.time())

def invalidate_cache(key_prefix=None):
    """Invalidates cache entries. If prefix provided, only matching keys."""
    global AUTH_CACHE
    if key_prefix:
        keys_to_delete = [k for k in AUTH_CACHE.keys() if k.startswith(key_prefix)]
        for k in keys_to_delete:
            del AUTH_CACHE[k]
    else:
        AUTH_CACHE = {}

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# --- FACTORY MANAGEMENT ---

def add_factory(name, firebase_url):
    """Adds a factory if the URL is unique."""
    # check existence first
    factories = get_factories()
    for f in factories:
        if f['firebase_url'] == firebase_url:
            return False
            
    # Generate ID
    factory_id = str(uuid.uuid4())[:8]
    
    # Default features for a new factory
    default_features = {
        'maintenance_mode': False,
        'beta_features': False,
        'user_registration': True,
        'battery_monitoring': True,
        'diesel_tank_monitoring': True,
        'water_tank_monitoring': True,
        'jockey_pump_logic': True,

        'diesel_pump_logic': True,
        'main_pump_logic': True
    }
    
    data = {
        "id": factory_id, 
        "name": name, 
        "firebase_url": firebase_url,
        "features": default_features
    }
    
    try:
        # We index by ID for easier lookup
        requests.patch(f"{SYSTEM_DB_URL}/system_metadata/factories/{factory_id}.json", json=data)
        invalidate_cache("all_factories")
        return True
    except:
        return False

def update_factory_features(factory_id, features_dict):
    """Updates features for a specific factory."""
    try:
        requests.patch(f"{SYSTEM_DB_URL}/system_metadata/factories/{factory_id}/features.json", json=features_dict)
        invalidate_cache(f"factory_{factory_id}")
        return True
    except:
        return False

def delete_factory(factory_id):
    """Deletes a factory from the system metadata."""
    try:
        requests.delete(f"{SYSTEM_DB_URL}/system_metadata/factories/{factory_id}.json")
        invalidate_cache("all_factories")
        invalidate_cache(f"factory_{factory_id}")
        return True
    except:
        return False

def get_factories():
    cache_key = "all_factories"
    cached = get_from_cache(cache_key)
    if cached is not None:
        return cached

    try:
        response = requests.get(f"{SYSTEM_DB_URL}/system_metadata/factories.json")
        data = response.json()
        if not data: 
            set_to_cache(cache_key, [])
            return []
        
        # Convert dict of dicts to list
        if isinstance(data, dict):
            result = list(data.values())
            set_to_cache(cache_key, result)
            return result
        return []
    except: return []

def get_factory_by_id(factory_id):
    cache_key = f"factory_{factory_id}"
    cached = get_from_cache(cache_key)
    if cached is not None:
        return cached

    try:
        response = requests.get(f"{SYSTEM_DB_URL}/system_metadata/factories/{factory_id}.json")
        data = response.json()
        if data:
            set_to_cache(cache_key, data)
        return data
    except: return None

# --- USER MANAGEMENT ---

def add_user(username, password, role, factory_id=None, can_access_settings=False, name=None, created_by=None):
    # Check if username exists
    users = get_users()
    for u in users:
        if u['username'] == username:
            return False
            
    user_id = str(uuid.uuid4())[:8]
    pwd_hash = hash_password(password)
    
    # Use username as name if not provided
    if not name:
        name = username
    
    data = {
        "id": user_id,
        "username": username,
        "name": name,
        "password_hash": pwd_hash,
        "role": role,
        "factory_id": factory_id,
        "can_access_settings": can_access_settings,
        "created_by": created_by
    }
    
    try:
        requests.patch(f"{SYSTEM_DB_URL}/system_metadata/users/{user_id}.json", json=data)
        invalidate_cache("all_users")
        return True
    except:
        return False

def verify_user(username, password):
    # This involves fetching all users to find by username, 
    # since Firebase doesn't support "WHERE" queries easily on REST without indexing rules.
    # For a small number of users, this is fine.
    users = get_users()
    pwd_hash = hash_password(password)
    
    for u in users:
        if u['username'] == username and u['password_hash'] == pwd_hash:
            return u
    return None

def get_users():
    cache_key = "all_users"
    cached = get_from_cache(cache_key)
    if cached is not None:
        return cached

    try:
        response = requests.get(f"{SYSTEM_DB_URL}/system_metadata/users.json")
        data = response.json()
        if not data: 
            set_to_cache(cache_key, [])
            return []
        
        users_list = []
        if isinstance(data, dict):
            users_list = list(data.values())
        elif isinstance(data, list):
            users_list = [x for x in data if x]
            
        # Enrich with factory names for UI
        # Optimization: Fetch factories once (cached)
        factories = get_factories()
        fac_map = {f['id']: f['name'] for f in factories}
            
        for u in users_list:
            if u.get('factory_id'):
                u['factory_name'] = fac_map.get(u['factory_id'], 'Unknown')
            else:
                u['factory_name'] = None
        
        set_to_cache(cache_key, users_list)      
        return users_list
    except: return []

def delete_user(user_id):
    try:
        requests.delete(f"{SYSTEM_DB_URL}/system_metadata/users/{user_id}.json")
        invalidate_cache("all_users")
        return True
    except: return False

def update_password(user_id, new_password):
    """Updates the password for a specific user ID."""
    try:
        pwd_hash = hash_password(new_password)
        requests.patch(f"{SYSTEM_DB_URL}/system_metadata/users/{user_id}.json", json={"password_hash": pwd_hash})
        invalidate_cache("all_users")
        return True
    except:
        return False

def grant_temp_access(user_id, duration_minutes=60):
    """Grant temporary settings access for a specific duration."""
    try:
        expiry_time = int(time.time() + (duration_minutes * 60))
        requests.patch(f"{SYSTEM_DB_URL}/system_metadata/users/{user_id}.json", json={"settings_unlock_expiry": expiry_time})
        invalidate_cache("all_users")
        return True
    except:
        return False

def update_user_permission(user_id, can_access_settings):
    """Update the permanent settings access permission."""
    try:
        data = {"can_access_settings": can_access_settings}
        if not can_access_settings:
            data["settings_unlock_expiry"] = 0
            
        requests.patch(f"{SYSTEM_DB_URL}/system_metadata/users/{user_id}.json", json=data)
        invalidate_cache("all_users")
        return True
    except:
        return False
