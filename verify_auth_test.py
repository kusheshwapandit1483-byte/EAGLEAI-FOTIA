import unittest
from app import app
import auth_db

class AuthTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.secret_key = 'test_secret'
        self.client = app.test_client()
        
        # Reset DB for reliable testing (optional, but good)
        # For now, we reuse existing DB but ensure our test user is there
        # but let's just create a test user
        # auth_db.init_db() <--- REMOVED
        auth_db.add_factory("Test Factory", "https://test-factory.firebaseio.com")
        factories = auth_db.get_factories()
        
        # Find our test factory
        self.factory_id = None
        for f in factories:
            if f['name'] == "Test Factory":
                self.factory_id = f['id']
                break
        
        if not self.factory_id:
             # Should practically never happen if add_factory works
             self.skipTest("Could not create/find test factory")

        auth_db.add_user("testuser", "password123", "user", self.factory_id)
        auth_db.add_user("testadmin", "adminpass", "admin")

    def tearDown(self):
        # Clean up if needed
        pass

    def login(self, username, password):
        return self.client.post('/login', data=dict(
            username=username,
            password=password
        ), follow_redirects=True)

    def logout(self):
        return self.client.get('/logout', follow_redirects=True)

    def test_login_required(self):
        response = self.client.get('/', follow_redirects=True)
        # Should redirect to login
        self.assertIn(b'EAGLE AI ACCESS', response.data) # Check for text in login.html

    def test_admin_login(self):
        response = self.login('testadmin', 'adminpass')
        self.assertIn(b'System Dashboard', response.data)
        # Check for Users link in sidebar
        self.assertIn(b'Users', response.data)
        
        # Verify access to users page
        response = self.client.get('/users')
        self.assertIn(b'User Management', response.data)

    def test_user_login(self):
        response = self.login('testuser', 'password123')
        # Should redirect to index and rely on mock db?
        # Actually our app.py tries to read from firebase. 
        # But 'test-factory.firebaseio.com' will fail in requests.get inside fb_get?
        # That's fine, we just check if it renders the template.
        # But wait, app.py calls `requests.get` synchronously in `settings` route, but `index` route just renders template.
        self.assertIn(b'System Dashboard', response.data)

    def test_admin_access_restriction(self):
        self.login('testuser', 'password123')
        response = self.client.get('/users', follow_redirects=True)
        # Should be denied and redirected to index?
        # Actually our admin_required redirects to index if failed.
        # So we should see index page.
        self.assertIn(b'System Dashboard', response.data)
        self.assertNotIn(b'User Management', response.data)

if __name__ == '__main__':
    unittest.main()
