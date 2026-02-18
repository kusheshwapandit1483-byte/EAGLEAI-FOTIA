import auth_db

def init():
    print("Initializing Database...")
    auth_db.init_db() if hasattr(auth_db, 'init_db') else None
    
    print("Adding default factory...")
    default_url = "https://eagleai-fotia-default-rtdb.asia-southeast1.firebasedatabase.app"
    target_factory_name = "TM SEATING AUTOMOTIVE SYSTEMS PVT LTD"
    
    if auth_db.add_factory(target_factory_name, default_url):
        print(f"Factory '{target_factory_name}' added.")
    else:
        print("Factory already exists.")

    print("Adding Admin user...")
    # New credentials: tm_admin / admin123
    # We need to find the factory ID first to associate it, although admin usually has access to all.
    # But good practice to associate.
    factories = auth_db.get_factories()
    factory_id = None
    for f in factories:
        if f['name'] == target_factory_name:
            factory_id = f['id']
            break
            
    if auth_db.add_user("tm_admin", "admin123", "admin", factory_id=factory_id, can_access_settings=True):
        print("Admin user 'tm_admin' created.")
    else:
        print("Admin user already exists.")

if __name__ == "__main__":
    init()
