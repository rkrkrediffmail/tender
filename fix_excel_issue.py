#!/usr/bin/env python3
"""
Quick fix script for Excel processing issues
"""

import subprocess
import sys
import os

def install_openpyxl():
    """Install openpyxl if not available"""
    print("📦 Installing openpyxl...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "openpyxl>=3.1.0"], check=True)
        print("✅ openpyxl installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install openpyxl: {e}")
        return False

def test_import():
    """Test if openpyxl can be imported"""
    try:
        import openpyxl
        print(f"✅ openpyxl is available (version: {openpyxl.__version__})")
        return True
    except ImportError:
        print("❌ openpyxl is not available")
        return False

def test_excel_processor():
    """Test the Excel processor"""
    try:
        from excel_processor import create_excel_processor, EXCEL_AVAILABLE
        
        if not EXCEL_AVAILABLE:
            print("❌ Excel processing is disabled")
            return False
        
        processor = create_excel_processor()
        print("✅ Excel processor created successfully")
        return True
        
    except Exception as e:
        print(f"❌ Excel processor test failed: {e}")
        return False

def main():
    """Main fix function"""
    print("=" * 50)
    print("🔧 EXCEL PROCESSING FIX SCRIPT")  
    print("=" * 50)
    
    success_count = 0
    
    # Test 1: Check openpyxl import
    print("1. Testing openpyxl import...")
    if test_import():
        success_count += 1
    else:
        # Try to install it
        print("   Attempting to install openpyxl...")
        if install_openpyxl():
            if test_import():
                success_count += 1
    
    # Test 2: Test Excel processor
    print("\n2. Testing Excel processor...")
    if test_excel_processor():
        success_count += 1
    
    print(f"\n📊 Results: {success_count}/2 tests passed")
    
    if success_count == 2:
        print("\n✅ Excel processing should now work!")
        print("\nNext steps:")
        print("1. Restart your web application")
        print("2. Try uploading your Excel checklist again")
        print("3. If you still get errors, run:")
        print("   python3 test_excel_debug.py /path/to/your/file.xlsx")
    else:
        print("\n❌ Some issues remain. You may need to:")
        print("1. Install openpyxl manually: pip install openpyxl")
        print("2. Check if you have permission to install packages")
        print("3. Use a virtual environment if needed")
    
    return success_count == 2

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)