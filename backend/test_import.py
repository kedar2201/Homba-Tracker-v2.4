print("Starting import test...")
try:
    from main import app
    print("Import successful!")
except Exception as e:
    import traceback
    traceback.print_exc()
print("Import test finished.")
