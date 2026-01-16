"""
Migración: user_profile.json → DB (tabla user_profile)
"""
import sys
import json
from pathlib import Path
from datetime import datetime

# Fix imports
sys.path.insert(0, str(Path(__file__).parent))

from database.connection import init_db, get_db
from database.repositories import UserProfileRepository

def main():
    print("🔧 Migrating user_profile.json to database...")
    
    # Initialize database (crear tabla si no existe)
    init_db()
    print("✅ Database initialized")
    
    # Read JSON
    profile_path = Path("data/processed/user_profile.json")
    if not profile_path.exists():
        print("⚠️ user_profile.json not found; creating default profile in DB...")
        db = next(get_db())
        try:
            UserProfileRepository.create_or_update(db, UserProfileRepository.DEFAULT_PROFILE)
            print("✅ Default profile created in database")
        finally:
            db.close()
        return
    
    with profile_path.open('r', encoding='utf-8') as f:
        profile_data = json.load(f)
    
    print(f"📦 Loaded profile with {len(profile_data)} keys from JSON")
    
    # Insert into DB
    db = next(get_db())
    try:
        UserProfileRepository.create_or_update(db, profile_data)
        print("✅ User profile migrated to database")
        
        # Verify
        loaded = UserProfileRepository.get(db)
        print(f"✅ Verified: archetype={loaded.get('archetype',{}).get('archetype')}, "
              f"insights={len(loaded.get('insights',[]))} items")
    finally:
        db.close()
    
    print("\n🎉 Migration complete! User profile is now in the database.")
    print("💡 The app will now read from DB automatically via load_user_profile().")

if __name__ == "__main__":
    main()
