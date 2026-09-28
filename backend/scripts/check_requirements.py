#!/usr/bin/env python3
"""
Check system requirements and dependencies
"""

import sys
import subprocess


def check_python_version():
    """Check Python version"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print(f"❌ Python 3.10+ required, found {version.major}.{version.minor}.{version.micro}")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True


def check_package(package):
    """Check if a Python package is installed"""
    try:
        __import__(package)
        return True
    except ImportError:
        return False


def check_packages():
    """Check required Python packages"""
    required = [
        'fastapi',
        'uvicorn',
        'sqlalchemy',
        'dropbox',
        'PIL',
        'imagehash',
        'numpy',
        'pydantic',
        'aiofiles',
    ]

    missing = []
    for package in required:
        pkg_name = package if package != 'PIL' else 'Pillow'
        if check_package(package):
            print(f"✅ {pkg_name}")
        else:
            print(f"❌ {pkg_name} not found")
            missing.append(pkg_name)

    return len(missing) == 0, missing


def check_env_file():
    """Check if .env file exists"""
    import os
    from pathlib import Path
    if os.path.exists('.env'):
        print("✅ .env file found")

        # Check for required variables
        from dotenv import load_dotenv
        load_dotenv()

        mode = os.getenv('STORAGE_MODE', 'dropbox').lower()
        if mode == 'local':
            root = os.getenv('LOCAL_ROOT', '')
            if not root or not Path(root).expanduser().is_dir():
                print("❌ LOCAL_ROOT must name an existing directory")
                return False
            print(f"✅ Local root: {root}")
        elif mode == 'dropbox':
            token = os.getenv('DROPBOX_ACCESS_TOKEN')
            if not token or token.startswith('your_'):
                print("❌ Set DROPBOX_ACCESS_TOKEN for Dropbox mode")
                return False
            print("✅ Dropbox access token configured")
        else:
            print("❌ STORAGE_MODE must be local or dropbox")
            return False

        return True
    else:
        print("❌ .env file not found")
        return False


def check_node():
    """Check Node.js installation"""
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True)
        version = result.stdout.strip()
        print(f"✅ Node.js {version}")
        return True
    except FileNotFoundError:
        print("❌ Node.js not found")
        return False


def main():
    print("🔍 Checking dbxclean requirements...\n")

    print("--- Python ---")
    py_ok = check_python_version()

    print("\n--- Python Packages ---")
    pkg_ok, missing = check_packages()

    print("\n--- Configuration ---")
    env_ok = check_env_file()

    print("\n--- Node.js (for frontend) ---")
    node_ok = check_node()

    print("\n" + "="*50)

    if py_ok and pkg_ok and env_ok:
        print("✅ Backend requirements satisfied!")
    else:
        print("❌ Backend requirements not satisfied")

        if not pkg_ok:
            print(f"\nInstall missing packages:")
            print(f"  pip install -r requirements.txt")

        if not env_ok:
            print(f"\nConfigure environment:")
            print(f"  cp .env.example .env")
            print(f"  # Set LOCAL_ROOT for local mode, or set a token for Dropbox mode")

        return 1

    if node_ok:
        print("✅ Frontend requirements satisfied!")
    else:
        print("⚠️  Node.js not found (needed for frontend)")

    print("\n✅ System ready to run!")
    return 0


if __name__ == "__main__":
    import os
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.exit(main())
