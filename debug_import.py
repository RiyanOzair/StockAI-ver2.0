import sys
import os
sys.path.insert(0, os.getcwd())
try:
    from backend.app.core.config import settings
    print("Settings imported successfully")
    print(f"Provider: {settings.DEFAULT_MODEL_PROVIDER}")
except Exception as e:
    import traceback
    traceback.print_exc()
