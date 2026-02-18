import auth_db
import requests

SYSTEM_DB_URL = auth_db.SYSTEM_DB_URL

def delete_factory(factory_id):
    try:
        requests.delete(f"{SYSTEM_DB_URL}/system_metadata/factories/{factory_id}.json")
        return True
    except: return False

def migrate_credentials():
    print("Starting migration...")
    
    # 1. Clean up existing Factories
    factories = auth_db.get_factories()
    print(f"Found {len(factories)} factories.")
    
    target_factory_name = "TM SEATING AUTOMOTIVE SYSTEMS PVT LTD"
    dummy_factory_name = "Tata Motors Main Plant"
    
    target_factory_id = None
    
    # Remove dummy, find target
    for f in factories:
        if f['name'] == dummy_factory_name:
            print(f"Removing dummy factory: {f['name']}")
            delete_factory(f['id'])
        elif f['name'] == target_factory_name:
            print(f"Target factory already exists: {f['name']}")
            target_factory_id = f['id']

    # 2. Add Target Factory if not exists
    if not target_factory_id:
        print(f"Adding target factory: {target_factory_name}")
        # Using the default URL as per previous config
        default_url = "https://eagleai-fotia-default-rtdb.asia-southeast1.firebasedatabase.app"
        if auth_db.add_factory(target_factory_name, default_url):
            print("Factory added successfully.")
            # Fetch again to get ID
            factories = auth_db.get_factories()
            for f in factories:
                if f['name'] == target_factory_name:
                    target_factory_id = f['id']
                    break
        else:
            print("Failed to add factory.")

    # 3. Clean up Users
    users = auth_db.get_users()
    dummy_user = "admin"
    target_user = "tm_admin"
    
    for u in users:
        if u['username'] == dummy_user:
            print(f"Removing dummy user: {u['username']}")
            auth_db.delete_user(u['id'])
            
    # 4. Add new Admin User
    print(f"Creating new admin user: {target_user}")
    # Give full access
    if auth_db.add_user(target_user, "admin123", "admin", factory_id=target_factory_id, can_access_settings=True):
        print(f"User {target_user} created successfully.")
    else:
        print(f"User {target_user} already exists or failed.")

if __name__ == "__main__":
    migrate_credentials()
