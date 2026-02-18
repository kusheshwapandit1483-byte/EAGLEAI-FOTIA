import auth_db
import time

def recover_admin():
    print("Attempting to recover Admin user...")
    
    # Check if admin exists
    users = auth_db.get_users()
    admin_exists = False
    for u in users:
        if u['username'] == 'admin':
            print("Admin user ALREADY exists.")
            admin_exists = True
            break
            
    if not admin_exists:
        print("Admin user not found. Creating...")
        # Try adding
        success = auth_db.add_user("admin", "admin123", "admin", can_access_settings=True)
        if success:
            print("Admin user created SUCCESSFULLY.")
        else:
            print("FAILED to create Admin user. This might be due to a network error or DB checking issue.")
            # debug why
            # Try verify get_users again
            print("Debug: Current users in DB:")
            print(auth_db.get_users())
            
    else:
        print("Admin exists. You should be able to login with 'admin' / 'admin123'.")

if __name__ == "__main__":
    recover_admin()
