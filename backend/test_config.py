try:
    print("Importing settings...")
    from app.core.config import settings
    print(f"Config loaded: {settings.PROJECT_NAME}")
except Exception as e:
    print(f"Failed to load config: {e}")
