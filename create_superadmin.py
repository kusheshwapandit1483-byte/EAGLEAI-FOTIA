
import auth_db

def create_superadmin():
    print("Creating Superadmin User...")
    username = input("Enter username (default: superadmin): ") or "superadmin"
    password = input("Enter password (default: admin123): ") or "admin123"
    
    # role='superadmin'
    # factory_id=None (Global access)
    # can_access_settings=True
    
    if auth_db.add_user(username, password, 'superadmin', None, True, name="Super Admin"):
        print(f"SUCCESS: User '{username}' created with role 'superadmin'.")
    else:
        print(f"ERROR: Could not create user '{username}'. It might already exist.")

if __name__ == "__main__":
    create_superadmin()
