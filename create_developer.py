import auth_db

def create_developer():
    print("--- Developer Credentials Update ---")
    
    # 1. Find and delete existing developers (or previous attempts)
    print("Scanning for existing developer accounts...")
    users = auth_db.get_users()
    
    for u in users:
        # Delete if role is developer OR username is FOTIADEV (to start fresh)
        if u.get('role') == 'developer' or u.get('username') == 'FOTIADEV':
            print(f"Deleting existing user: {u['username']} (Role: {u.get('role')})")
            if auth_db.delete_user(u['id']):
                print("  -> Deleted successfully.")
            else:
                print("  -> Failed to delete.")

    # 2. Create new Developer
    print("\nCreating new Developer account...")
    target_user = "FOTIADEV"
    target_pass = "123456"
    
    # Using 'developer' role as seen in app.py security checks
    # Factory ID can be None for developers (GLOBAL ACCESS)
    # can_access_settings=True (implicitly handled by role in app.py, but good to set)
    
    if auth_db.add_user(target_user, target_pass, "developer", factory_id=None, can_access_settings=True, name="Fotia Developer"):
        print(f"SUCCESS: User '{target_user}' created with role 'developer'.")
        print(f"Password: {target_pass}")
    else:
        print(f"ERROR: Could not create user '{target_user}'.")

if __name__ == "__main__":
    create_developer()
