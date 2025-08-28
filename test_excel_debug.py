#!/usr/bin/env python3
"""
Excel Debug Test Script
Run this to diagnose Excel file reading issues
"""

import os
import sys
from excel_processor import create_excel_processor

def test_excel_file(file_path):
    """Test an Excel file and show detailed debug information"""
    
    print("=" * 60)
    print("EXCEL FILE DEBUG TEST")
    print("=" * 60)
    print(f"Testing file: {file_path}")
    print()
    
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"❌ ERROR: File not found: {file_path}")
        return False
    
    print(f"✅ File exists: {os.path.getsize(file_path):,} bytes")
    
    try:
        # Create processor
        processor = create_excel_processor()
        print("✅ Excel processor created successfully")
        
        # Validate file
        print("\n🔍 VALIDATING FILE...")
        validation = processor.validate_excel_file(file_path)
        print(f"Validation result: {validation}")
        
        if not validation.get('valid'):
            print(f"❌ File validation failed: {validation.get('error')}")
            return False
        
        print(f"✅ File is valid")
        print(f"   Sheets: {validation.get('sheet_names')}")
        print(f"   Sheet count: {validation.get('sheet_count')}")
        
        # Preview sheets
        print("\n🔍 PREVIEWING SHEETS...")
        preview = processor.preview_excel_sheets(file_path, max_preview_rows=15)
        
        if not preview.get('success'):
            print(f"❌ Preview failed: {preview.get('error')}")
            return False
        
        print(f"✅ Preview successful")
        print(f"   Total sheets: {preview.get('total_sheets')}")
        
        # Analyze each sheet
        for sheet_name, sheet_data in preview.get('sheets', {}).items():
            print(f"\n📊 SHEET: '{sheet_name}'")
            print(f"   Max row: {sheet_data.get('max_row')}")
            print(f"   Max column: {sheet_data.get('max_column')}")
            print(f"   Has data: {sheet_data.get('has_data')}")
            
            debug_info = sheet_data.get('debug_info', {})
            if debug_info:
                print(f"   Debug info:")
                for key, value in debug_info.items():
                    print(f"     {key}: {value}")
            
            # Show first few rows of data
            data = sheet_data.get('data', [])
            if data:
                print(f"   First 3 rows of data:")
                for i, row in enumerate(data[:3]):
                    row_values = [cell.get('value', '') for cell in row[:5]]  # First 5 columns
                    print(f"     Row {i+1}: {row_values}")
            else:
                print(f"   No data found")
            
            # Count non-empty cells
            non_empty_count = 0
            for row in data:
                for cell in row:
                    cell_value = str(cell.get('value', '')).strip()
                    if cell_value and cell_value not in ['', 'None', 'null']:
                        non_empty_count += 1
            
            print(f"   Non-empty cells found: {non_empty_count}")
        
        print("\n✅ Excel file analysis completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR during analysis: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function"""
    
    if len(sys.argv) != 2:
        print("Usage: python3 test_excel_debug.py <path_to_excel_file>")
        print("Example: python3 test_excel_debug.py /path/to/checklist.xlsx")
        sys.exit(1)
    
    file_path = sys.argv[1]
    success = test_excel_file(file_path)
    
    if success:
        print("\n🎉 Analysis completed successfully!")
        print("\nIf you're still getting 'empty sheet' errors in the web interface,")
        print("please share the debug information above.")
    else:
        print("\n❌ Analysis failed - please check the error messages above.")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()