import auth_db
import requests

def reset_users():
    print("WARNING: This will delete ALL users.")
    
    # 1. Fetch all users to find their IDs
    users = auth_db.get_users()
    print(f"Found {len(users)} existing users.")
    
    # 2. Delete each user
    for user in users:
        print(f"Deleting user: {user['username']} ({user['id']})")
        auth_db.delete_user(user['id'])
        
    print("All users deleted.")
    
    # 3. Re-create Admin
    # Explicitly allow settings access just in case, though admin role implies it in app.py logic
    # But for consistency in DB, we'll set it to True.
    print("Re-creating Admin user...")
    if auth_db.add_user("admin", "admin123", "admin", can_access_settings=True):
        print("Admin user created (admin/admin123).")
    else:
        print("Failed to create Admin user!")

if __name__ == "__main__":
    reset_users()
