from flask import Flask, render_template, request, redirect, url_for, flash, session
from datetime import timedelta
import requests
import json
import os
import uuid
import functools
import auth_db
import time

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'eagle_ai_super_secret_key_8822')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

# --- FIREBASE CONFIGURATION ---
# Default/Fallback URL (can be used for unassigned admins or initial setup)
DEFAULT_FIREBASE_URL = "https://eagleai-fotia-default-rtdb.asia-southeast1.firebasedatabase.app"

def get_current_factory_url():
    """Returns the Firebase URL for the current session context."""
    return session.get('factory_url', DEFAULT_FIREBASE_URL)

# --- HELPER FUNCTIONS ---
def fb_get(path):
    try:
        base_url = get_current_factory_url()
        response = requests.get(f"{base_url}/{path}.json")
        return response.json()
    except: return None

def fb_update(path, data):
    try:
        base_url = get_current_factory_url()
        requests.patch(f"{base_url}/{path}.json", json=data)
        return True
    except: return False

def fb_push(path, data):
    try:
        base_url = get_current_factory_url()
        requests.post(f"{base_url}/{path}.json", json=data)
        return True
    except: return False

def fb_delete(path):
    try:
        base_url = get_current_factory_url()
        requests.delete(f"{base_url}/{path}.json")
        return True
    except: return False

def fb_put(path, data):
    try:
        base_url = get_current_factory_url()
        requests.put(f"{base_url}/{path}.json", json=data)
        return True
    except: return False

# --- CACHE CONFIGURATION ---
# MOVED TO AUTH_DB.PY

# ========================================================
# CONTEXT PROCESSORS
# ========================================================
@app.context_processor
def inject_features():
    """Injects current factory features into all templates."""
    if 'factory_id' in session:
        factory_id = session['factory_id']
        
        # Fetch from auth_db (now cached internally)
        factory = auth_db.get_factory_by_id(factory_id)
        if factory and 'features' in factory:
            return dict(factory_features=factory['features'])
    
    # Default fallback if no factory or features
    return dict(factory_features={})

# ========================================================
# AUTHENTICATION DECORATORS
# ========================================================
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return view(**kwargs)
    return wrapped_view

def admin_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if 'user_id' not in session or session.get('role') not in ['admin', 'superadmin', 'developer']:
            flash("Access denied. Admin privileges required.", "error")
            return redirect(url_for('index'))
        return view(**kwargs)
    return wrapped_view

# ========================================================
# ROUTES
# ========================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = auth_db.verify_user(username, password)
        if user:
            session.clear()
            session.permanent = True
            session['user_id'] = user.get('id')
            session['username'] = user.get('username')
            session['name'] = user.get('name', user.get('username'))
            session['role'] = user.get('role')
            session['factory_id'] = user.get('factory_id')
            
            # PERMISSION Logic
            if user.get('role') in ['admin', 'superadmin']:
                session['can_access_settings'] = True
            else:
                 session['can_access_settings'] = user.get('can_access_settings', False)

            # Set Context
            # Set Context
            if user.get('role') == 'developer':
                 session['factory_url'] = DEFAULT_FIREBASE_URL
                 session['factory_name'] = "MASTER PANEL"
                 return redirect(url_for('developer_dashboard'))

            if user.get('role') in ['admin', 'superadmin']:
                # If Admin/Superadmin has a specific factory assigned, default to that context
                if user.get('factory_id'):
                    factory = auth_db.get_factory_by_id(user.get('factory_id'))
                    if factory:
                        session['factory_url'] = factory['firebase_url']
                        session['factory_name'] = factory['name']
                    else:
                        session['factory_url'] = DEFAULT_FIREBASE_URL
                        session['factory_name'] = "Global View" # Or keep unset to fall back
                else:
                    session['factory_url'] = DEFAULT_FIREBASE_URL
                    # session['factory_name'] = "Global View" 
                
                return redirect(url_for('index'))
            else:
                # Regular Users: Get their assigned factory URL
                if user.get('factory_id'):
                    factory = auth_db.get_factory_by_id(user.get('factory_id'))
                    if factory:
                        session['factory_url'] = factory['firebase_url']
                        session['factory_name'] = factory['name']
                        return redirect(url_for('index'))
                
                flash("User has no assigned factory. Contact Admin.", "error")
                return redirect(url_for('login'))
        
        flash("Invalid username or password.", "error")
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for('login'))

@app.route('/pumps')
@login_required
def pumps():
    return render_template('pumps.html', current_time=time.time())

# --- ADMIN ROUTES ---

@app.route('/users')
@admin_required
def admin_users():
    all_users = auth_db.get_users()
    # Visibility Logic
    current_role = session.get('role')
    current_user_id = session.get('user_id')
    current_factory_id = session.get('factory_id')
    
    # 2. Filter Factories based on Role
    all_factories = auth_db.get_factories()
    visible_factories = []
    
    if current_role in ['superadmin', 'developer']:
        visible_factories = all_factories
    elif current_role == 'admin':
        # Admin only sees their own factory
        for f in all_factories:
            if f['id'] == current_factory_id:
                visible_factories.append(f)
                break
    
    # 3. Filter Users based on Role
    all_users = auth_db.get_users()
    visible_users = []
    
    if current_role == 'developer':
        visible_users = all_users
    elif current_role == 'superadmin':
        # Superadmin sees all EXCEPT developers
        visible_users = [u for u in all_users if u.get('role') != 'developer']
    elif current_role == 'admin':
        # Admin sees only users THEY created, plus themselves
        filtered = []
        for u in all_users:
            if u.get('created_by') == current_user_id or u.get('id') == current_user_id:
                # Double check they don't see developers even if they somehow created them (unlikely but safe)
                if u.get('role') != 'developer':
                    filtered.append(u)
        visible_users = filtered
        
    return render_template('users.html', users=visible_users, factories=visible_factories, current_time=time.time())

@app.route('/admin/add_user', methods=['POST'])
@admin_required
def admin_add_user():
    username = request.form['username']
    password = request.form['password']
    role = request.form['role']
    name = request.form.get('name') 
    factory_id = request.form.get('factory_id')
    source_page = request.form.get('source_page', 'admin') # 'admin' or 'users'
    can_access_settings = (request.form.get('settings_access') == 'on')

    # Security Check: Only Superadmin can create 'admin' or 'superadmin' roles
    if role in ['admin', 'superadmin'] and session.get('role') not in ['superadmin', 'developer']:
        flash("Only Superadmins/Developers can create Admin accounts.", "error")
        return redirect(url_for('admin_users'))
    
    
    if not factory_id:
        factory_id = None
        
    # Security Enforcement: Admins can ONLY add to their own factory
    if session.get('role') == 'admin':
        factory_id = session.get('factory_id')
        
    # Pass created_by as current user_id
    current_user_id = session.get('user_id')
    
    if auth_db.add_user(username, password, role, factory_id, can_access_settings, name=name, created_by=current_user_id):
        flash(f"User {username} created successfully.", "success")
    else:
        flash("Error creating user. Username might already exist.", "error")
        
    return redirect(url_for('admin_users'))

@app.route('/admin/delete_user/<user_id>', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    # Prevent deleting self
    if user_id == session.get('user_id'):
         flash("Cannot delete yourself.", "error")
         return redirect(url_for('admin_users'))

    # Security Check: Standard Admins cannot delete other Admins or Superadmins
    # We need to fetch the target user to check their role.
    target_user = None
    users = auth_db.get_users() # Not efficient but safe
    for u in users:
        if u['id'] == user_id:
            target_user = u
            break
            
    if target_user:
        if target_user.get('role') in ['admin', 'superadmin'] and session.get('role') not in ['superadmin', 'developer']:
            flash("Insufficient privileges to delete an Admin/Superadmin.", "error")
            return redirect(url_for('admin_users'))
            
        auth_db.delete_user(user_id)
        flash("User deleted.", "success")
    else:
        flash("User not found.", "error")
        
    return redirect(url_for('admin_users'))

@app.route('/admin/temp_unlock/<user_id>', methods=['POST'])
@admin_required
def admin_temp_unlock(user_id):
    if auth_db.grant_temp_access(user_id, 360):
         flash("Temporary access granted for 6 hours.", "success")
    else:
         flash("Failed to grant temporary access.", "error")
    return redirect(url_for('admin_users'))

@app.route('/admin/toggle_access/<user_id>', methods=['POST'])
@admin_required
def admin_toggle_access(user_id):
    action = request.form.get('action')
    if action == 'grant':
        if auth_db.update_user_permission(user_id, True):
            flash("Permanent settings access GRANTED.", "success")
        else:
            flash("Error updating permission.", "error")
    elif action == 'revoke':
        if auth_db.update_user_permission(user_id, False):
            flash("Permanent settings access REVOKED.", "success")
        else:
            flash("Error updating permission.", "error")
    
    return redirect(url_for('admin_users'))

@app.route('/admin/switch_factory/<factory_id>')
@admin_required
def admin_switch_factory(factory_id):
    factory = auth_db.get_factory_by_id(factory_id)
    if factory:
        session['factory_url'] = factory['firebase_url']
        session['factory_name'] = factory['name']
        flash(f"Switched context to {factory['name']}", "success")
        return redirect(url_for('index'))
    else:
        flash("Factory not found.", "error")
        return redirect(url_for('admin_users'))

# --- DEVELOPER (MASTER) ROUTES ---

def developer_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if 'user_id' not in session or session.get('role') != 'developer':
            flash("Access denied. Developer privileges required.", "error")
            return redirect(url_for('index'))
        return view(**kwargs)
    return wrapped_view

@app.route('/developer')
@developer_required
def developer_dashboard():
    factories = auth_db.get_factories()
    # Ensure all factories have a 'features' dict for safe template rendering
    for f in factories:
        if 'features' not in f or not f['features']:
            f['features'] = {
                'maintenance_mode': False,
                'beta_features': False,
                'user_registration': True
            }
            
    return render_template('developer_dashboard.html', factories=factories)

@app.route('/developer/add_factory', methods=['POST'])
@developer_required
def developer_add_factory():
    name = request.form['name']
    url = request.form['firebase_url']
    
    if auth_db.add_factory(name, url):
        flash(f"Factory '{name}' added successfully.", "success")
    else:
        flash("Error adding factory. URL might already exist.", "error")
        
    return redirect(url_for('developer_dashboard'))

@app.route('/developer/toggle_feature', methods=['POST'])
@developer_required
def developer_toggle_feature():
    factory_id = request.form['factory_id']
    feature_key = request.form['key']
    action = request.form.get('action', 'toggle')
    
    # We need to fetch current features, update one, save back
    factory = auth_db.get_factory_by_id(factory_id)
    if factory:
        features = factory.get('features', {})
        if not features: # Init if missing
             features = {'maintenance_mode': False, 'beta_features': False, 'user_registration': True}
        
        if action == 'set':
             # Set explicitly (e.g. for adding new feature)
             new_value = (request.form['value'] == 'True')
        else:
             # Toggle existing
             current_value = request.form['value'] == 'True' 
             new_value = not current_value
        
        features[feature_key] = new_value
        
        if auth_db.update_factory_features(factory_id, features):
             flash(f"Feature '{feature_key}' updated to {new_value}.", "success")
        else:
             flash("Error updating feature.", "error")
    else:
        flash("Factory not found.", "error")
        
    return redirect(url_for('developer_dashboard'))

@app.route('/developer/reset_password', methods=['POST'])
@developer_required
def developer_reset_password():
    user_id = request.form['user_id']
    new_password = request.form['new_password']
    
    # corrected function name from update_user_password to update_password
    if auth_db.update_password(user_id, new_password):
        flash("User password updated successfully.", "success")
    else:
        flash("Error updating password.", "error")
        
    return redirect(request.referrer or url_for('developer_dashboard'))

@app.route('/developer/change_password', methods=['POST'])
@developer_required
def developer_change_password():
    current_password = request.form['current_password']
    new_password = request.form['new_password']
    confirm_password = request.form['confirm_password']
    
    if new_password != confirm_password:
        flash("New passwords do not match.", "error")
        return redirect(url_for('developer_dashboard'))
        
    # Verify current password
    user_id = session.get('user_id')
    username = session.get('username')
    
    # We verify the user logic again to check old password
    if auth_db.verify_user(username, current_password):
        if auth_db.update_password(user_id, new_password):
            flash("Your password has been updated successfully.", "success")
        else:
            flash("Error updating password.", "error")
    else:
        flash("Incorrect current password.", "error")

    return redirect(url_for('developer_dashboard'))

@app.route('/developer/update_factory_pin', methods=['POST'])
@developer_required
def developer_update_factory_pin():
    factory_id = request.form['factory_id']
    new_pin = request.form['new_pin']
    
    if not new_pin or len(new_pin) != 6 or not new_pin.isdigit():
        flash("PIN must be exactly 6 digits.", "error")
        return redirect(url_for('developer_dashboard'))
    
    # Get factory URL
    factory = auth_db.get_factory_by_id(factory_id)
    if factory:
        fb_url = factory.get('firebase_url')
        try:
            # Direct update to factory DB
            requests.patch(f"{fb_url}/settings.json", json={"settings_pin": new_pin})
            flash(f"PIN for {factory.get('name')} updated to {new_pin}.", "success")
        except Exception as e:
            flash(f"Error updating PIN: {str(e)}", "error")
    else:
        flash("Factory not found.", "error")
        
    return redirect(url_for('developer_dashboard'))

@app.route('/developer/delete_factory/<factory_id>', methods=['POST'])
@developer_required
def developer_delete_factory(factory_id):
    if auth_db.delete_factory(factory_id):
        flash("Factory deleted successfully.", "success")
    else:
        flash("Error deleting factory.", "error")
    return redirect(url_for('developer_dashboard'))

@app.route('/developer/clear_logs/<factory_id>', methods=['POST'])
@developer_required
def developer_clear_logs(factory_id):
    factory = auth_db.get_factory_by_id(factory_id)
    if factory:
        fb_url = factory.get('firebase_url')
        try:
            # Delete the entire history node
            requests.delete(f"{fb_url}/history.json")
            flash(f"Event logs cleared for {factory.get('name')}.", "success")
        except Exception as e:
            flash(f"Error clearing logs: {str(e)}", "error")
    else:
        flash("Factory not found.", "error")
        
    return redirect(url_for('developer_dashboard'))


# --- APP ROUTES ---

@app.route('/')
@login_required
def index():
    """Renders the Main Dashboard"""
    # If admin hasn't selected a factory, maybe warn them or show default?
    # The session['factory_url'] is robust enough now.
    return render_template('index.html')

@app.route('/alarms')
@login_required
def alarms():
    return render_template('alarms.html')

@app.route('/api/live_data')
@login_required
def api_live_data():
    """Fetches the latest live data entry from Firebase."""
    try:
        base_url = get_current_factory_url()
        # Fetch only the latest entry to optimize performance
        url = f"{base_url}/live_data.json?orderBy=\"$key\"&limitToLast=1"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            if data:
                # Firebase returns { "timestamp_key": { ...data... } }
                # We just want the inner data object
                key = list(data.keys())[0]
                return json.dumps(data[key])
            return json.dumps({})
        return json.dumps({"error": "Firebase Error"}), 500
    except Exception as e:
        return json.dumps({"error": str(e)}), 500

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """Handles the Configuration Page"""
    
    # 1. READ SETTINGS FROM CLOUD
    cloud_settings = fb_get('settings')
    if not cloud_settings:
        cloud_settings = {
            "tank_height_cm": 200, 
            "pump_runtime_threshold": 60,
            "normal_frequency_seconds": 21600,
            "critical_frequency_seconds": 900,
            "settings_pin": "1234"
        }
    
    # Ensure PIN exists even if other settings do
    if 'settings_pin' not in cloud_settings:
        cloud_settings['settings_pin'] = "1234"

    # 2. HANDLE FORM ACTIONS
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'save_calibration':
            try:
                h = float(request.form.get('tank_height_cm'))
                r = int(request.form.get('pump_runtime_threshold'))
                fb_update('settings', {"tank_height_cm": h, "pump_runtime_threshold": r})
                flash("Calibration updated successfully!", "success")
            except:
                flash("Invalid input for calibration.", "error")

        elif action == 'save_frequencies':
            try:
                n = int(request.form.get('normal_frequency_seconds'))
                c = int(request.form.get('critical_frequency_seconds'))
                fb_update('settings', {"normal_frequency_seconds": n, "critical_frequency_seconds": c})
                flash("Data frequencies updated successfully!", "success")
            except:
                flash("Invalid input for frequencies.", "error")
        
        elif action == 'save_pin':
            current_typed_pin = request.form.get('current_pin')
            new_pin = request.form.get('new_pin')
            confirm_pin = request.form.get('confirm_pin')
            
            stored_pin = cloud_settings.get('settings_pin', '1234')

            if current_typed_pin != stored_pin:
                 flash("Current PIN is incorrect.", "error")
            elif not new_pin or not new_pin.isdigit() or len(new_pin) != 6:
                flash("New PIN must be exactly 6 digits.", "error")
            elif new_pin != confirm_pin:
                flash("New PINs do not match.", "error")
            else:
                fb_update('settings', {"settings_pin": new_pin})
                flash("Security PIN updated successfully.", "success")

        elif action == 'add_number':
            # Check limit first
            current_nums = fb_get('phone_numbers')
            if current_nums and len(current_nums) >= 4:
                flash("Maximum 4 recipients allowed.", "error")
            else:
                name = request.form.get('holder_name')
                num = request.form.get('new_number')
                rtype = request.form.get('recipient_type')
                
                # Simple ID generation
                new_id = str(uuid.uuid4())[:8]
                
                new_entry = {
                    "id": new_id,
                    "name": name, 
                    "number": num, 
                    "recipient_type": rtype
                }
                
                # Push with custom key or auto ID? 
                # Original code used fb_push or update. Let's stick to update dict logic if it was a dict, 
                # or push if it's a list. 
                # Let's use fb_update with generated ID key to be safe & consistent
                fb_update(f'phone_numbers/{new_id}', new_entry)
                flash("Recipient added. Please wait for 30 min to update the change.", "success")

        elif action == 'delete_number':
            num_id = request.form.get('number_id')
            if num_id:
                fb_delete(f'phone_numbers/{num_id}')
                flash("Recipient deleted. Please wait for 30 min to update the change.", "success")
        
        return redirect(url_for('settings'))

    # 3. FETCH DATA AND RENDER
    # Get phone numbers
    raw_nums = fb_get('phone_numbers')
    phone_numbers = []
    if raw_nums:
        # If it's a dict (Firebase default for keys), convert to list
        if isinstance(raw_nums, dict):
            for k, v in raw_nums.items():
                if isinstance(v, dict):
                    v['id'] = k # ensure ID is in dict
                    phone_numbers.append(v)
        elif isinstance(raw_nums, list):
             # filter out Nones if any
             phone_numbers = [x for x in raw_nums if x]



    # Determine Access Permission
    access_allowed = session.get('can_access_settings', False)
    
    # Developers and Superadmins ALWAYS have access
    if session.get('role') in ['developer', 'superadmin']:
        access_allowed = True
    
    # If not allowed by session (i.e., not Admin or Permitted User), check Temporary Access
    if not access_allowed:
        # We need to fetch the user again to check expiry timestamp
        # Optimization: In a real app we might cache this, but for now fetch fresh.
        # However, verify_user fetches by username. We have ID.
        # auth_db doesn't have a quick get_user_by_id exposed nicely yet without querying list or direct path.
        # Let's verify against the stored session user_id to avoid extra DB calls if possible,
        # but to be secure we should check DB.
        # Since we use Firebase REST, we can just get that node.
        try:
            import requests # Explicit import if lazy, but already at top
            sys_url = auth_db.SYSTEM_DB_URL
            uid = session.get('user_id')
            if uid:
                resp = requests.get(f"{sys_url}/system_metadata/users/{uid}/settings_unlock_expiry.json")
                if resp.status_code == 200:
                    expiry = resp.json()
                    if expiry and isinstance(expiry, (int, float)):
                        if time.time() < expiry:
                            access_allowed = True
        except:
             pass

    return render_template('settings.html', 
        current_settings=cloud_settings, 
        phone_numbers=phone_numbers,
        access_allowed=access_allowed
    )
@app.route('/analytics')
@login_required
def analytics():
    """Renders the Analytics/Graphs Page"""
    return render_template('analytics.html')



# ========================================================
# HISTORY TRACKER INTEGRATION
# ========================================================
# History tracker uses background threads which don't work in
# serverless environments (Vercel). Only start it for local dev.
IS_SERVERLESS = os.environ.get('VERCEL', False) or os.environ.get('AWS_LAMBDA_FUNCTION_NAME', False)

if not IS_SERVERLESS:
    from history_tracker import HistoryTracker
    tracker = HistoryTracker()
else:
    tracker = None

@app.route('/history')
@login_required
def history():
    """Renders the History Page"""
    return render_template('history.html')

if __name__ == '__main__':
    # Start tracker manually (local dev only)
    if tracker and not tracker.running:
        tracker.start()

    app.run(host='0.0.0.0', port=5000, debug=True)
