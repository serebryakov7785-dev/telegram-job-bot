import os


def cleanup():
    files_to_remove = [
        "utils.py",
        "utils_validators.py",
        "utils_formatters.py",
        "utils_security.py",
        "utils_misc.py",
    ]

    print("🧹 Cleaning up obsolete files...")
    for filename in files_to_remove:
        if os.path.exists(filename):
            try:
                os.remove(filename)
                print(f"✅ Removed: {filename}")
            except Exception as e:
                print(f"❌ Error removing {filename}: {e}")
    print("✨ Cleanup complete. You can now run pytest.")


if __name__ == "__main__":
    cleanup()
