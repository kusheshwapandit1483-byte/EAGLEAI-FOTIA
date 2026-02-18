import auth_db

def init():
    print("Initializing Firebase Auth System...")
    
    # 1. Default Factory
    print("Checking default factory...")
    default_url = "https://eagleai-fotia-default-rtdb.asia-southeast1.firebasedatabase.app"
    # We can't check by URL easily with current API safely without creating dups if name differs?
    # Actually add_factory checks validation.
    
    if auth_db.add_factory("Tata Motors Main Plant", default_url):
        print("Default factory added.")
    else:
        print("Default factory already exists (or URL conflict).")

    # 2. Default Admin
    print("Checking Admin user...")
    if auth_db.add_user("admin", "admin123", "admin"):
        print("Admin user created (admin/admin123).")
    else:
        print("Admin user already exists.")

if __name__ == "__main__":
    init()
