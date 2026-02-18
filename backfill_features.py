import auth_db
import requests
import json

SYSTEM_DB_URL = auth_db.SYSTEM_DB_URL

def backfill():
    print("--- starting backfill ---")
    factories = auth_db.get_factories()
    
    new_defaults = {
        'battery_monitoring': True,
        'diesel_tank_monitoring': True,
        'water_tank_monitoring': True,
        'jockey_pump_logic': True,
        'sprinkler_pump_logic': True,
        'diesel_pump_logic': True,
        'main_pump_logic': True
    }
    
    for f in factories:
        print(f"Processing: {f['name']}")
        current_features = f.get('features', {})
        updated = False
        
        for key, val in new_defaults.items():
            if key not in current_features:
                current_features[key] = val
                updated = True
                print(f"   + Added {key}")
                
        if updated:
            try:
                auth_db.update_factory_features(f['id'], current_features)
                print("   Saved.")
            except Exception as e:
                print(f"   Error saving: {e}")
        else:
            print("   No changes needed.")

    print("--- backfill complete ---")

if __name__ == "__main__":
    backfill()
