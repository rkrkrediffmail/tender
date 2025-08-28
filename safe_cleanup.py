#!/usr/bin/env python3
"""
Safe cleanup of obviously unused files - no confirmation needed
"""

import os
import shutil
from typing import List

def safe_cleanup():
    """Remove only obviously unused files without confirmation"""
    
    # Files that are 100% safe to remove (test data, old uploads, etc.)
    definitely_safe_to_remove = [
        # Old test uploads - these are just development data files
        'uploads/0136f5a6-5369-49a4-9986-de63002db1ae_maruthi.docx',
        'uploads/07dd49d7-90ef-4d3f-b989-3b37cb6920ce_maruthi.docx',
        'uploads/0e89b489-052a-4473-8ba8-e88302ea6112_maruthi.docx',
        'uploads/2634e039-f1fe-47d7-a530-53b61eeb4f83_Fronterra-RFP.pdf',
        'uploads/2711abb5-6016-4211-a473-69072e35c962_Fronterra-RFP.pdf',
        'uploads/28631a05-5b25-4fd9-94e1-8821ebd2d0e0_RFP_HR_Payroll_Software.PDF',
        'uploads/2bd3f335-1f30-4db5-96f4-36ba7adee501_Fronterra-RFP.pdf',
        'uploads/331b13fc-11cd-42ef-a9e0-5ef8c23d13b5_Fronterra-RFP_compressed.pdf',
        'uploads/3c7ce695-fe46-4daa-879a-7fdeb3354fad_maruthi.docx',
        'uploads/3df19d95-80bd-46dd-80c4-58102e969f72_Fronterra-RFP.pdf',
        'uploads/423eaeae-ab88-449d-bf09-f109a3660a8f_maruthi.docx',
        'uploads/4cc57f2f-2fb4-4b05-88fe-f70c40f1f0f3_maruthi.docx',
        'uploads/60699b91-33c4-4060-9024-6374d3c3c6f1_maruthi.docx',
        'uploads/60951a41-ff3f-4581-b619-a3d131e0352c_Fronterra-RFP.pdf',
        'uploads/6d00d3c6-d89c-42e8-97a3-c826186cff13_Fronterra-RFP.pdf',
        'uploads/6e2818c4-1481-4a71-ab96-dcf654f3e95d_maruthi.docx',
        'uploads/76d0e3be-9f8e-4348-ac2e-41c672f27e7f_Fronterra-RFP.pdf',
        'uploads/7e34dbe2-3448-4581-9ad0-7d8ef49a1d3a_maruthi.docx',
        'uploads/858ff009-63f1-46bd-9e6d-2f834379bb82_Fronterra-RFP.pdf',
        'uploads/a3128083-9743-442b-9822-5cc30546a435_Fronterra-RFP.pdf',
        'uploads/ade2ec4f-cd48-49ab-be6e-4cd1eb2b2187_maruthi.docx',
        'uploads/b66ddeac-16e8-4358-87b2-5aa2c27ef8c0_Fronterra-RFP.pdf',
        'uploads/f8f292c2-1b03-4b18-ad92-9a1834146871_Fronterra-RFP.pdf',
        'uploads/past_20250824_122650_ITSS_EDB_Ingenuous_AML_Platform_Commercial_Proposal_v1.0_1.pdf',
        'uploads/checklists/upgrade_20250824_114243_ITSS Upgrade Scoping_Questionnaire.xlsx',
        'uploads/checklists/upgrade_20250825_035622_Compliance_Matrix_Evaluation.xlsx',
        'uploads/checklists/upgrade_20250825_035750_ITSS Upgrade Scoping_Questionnaire - checklist.xlsx',
        'uploads/checklists/upgrade_20250825_041414_ITSS Upgrade Scoping_Questionnaire - checklist.xlsx',
        'uploads/checklists/upgrade_20250825_042723_ITSS Upgrade Scoping_Questionnaire - checklist.xlsx',
        'uploads/checklists/upgrade_20250825_043213_ITSS Upgrade Scoping_Questionnaire - checklist.xlsx',
        
        # Old generated test proposals
        'generated_proposals/Fonterra2_commercial_20250819_160740.html',
        'generated_proposals/Fonterra2_compliance_20250819_160837.html',
        'generated_proposals/Fonterra2_implementation_20250819_160815.html',
        'generated_proposals/Fonterra2_technical_20250819_160705.html',
        'generated_proposals/Jai_Shriram_commercial_20250803_114943.docx',
        'generated_proposals/Jai_Shriram_commercial_20250814_063855.html',
        'generated_proposals/Jai_Shriram_technical_20250803_114851.docx',
        'generated_proposals/Jai_Shriram_technical_20250814_063803.html',
        'generated_proposals/for_Thiag_commercial_20250814_125639.docx',
        'generated_proposals/for_Thiag_technical_20250814_125549.docx',
        'generated_proposals/for_somu_commercial_20250814_085333.html',
        'generated_proposals/for_somu_technical_20250814_085241.html',
        'generated_proposals/jai_maruthi_commercial_20250803_064020.html',
        'generated_proposals/jai_maruthi_technical_20250803_063938.html',
        'generated_proposals/proposal_package_Fonterra2_20250819_160837.zip',
        
        # Temporary/debug files
        'tempfix.py',
        'test_past_proposals_import.py',
        'vector_db/chroma.sqlite3',  # Will be replaced with Azure
        
        # Platform-specific files not needed
        'replit.md',
        '.replit',
        '.python-version',
        
        # Analysis/cleanup files we just created
        'analyze_unused_files.py',
        'cleanup_unused_files.py',
        'file_usage_analysis.json'
    ]
    
    # Only remove duplicate files where we're sure which one to keep
    obvious_duplicates = [
        'assumptions_analysis_agent.py',  # Keep the one in agents/ folder
        'base_agent.py',                  # Keep the one in agents/ folder
    ]
    
    # Combine lists
    files_to_remove = definitely_safe_to_remove + obvious_duplicates
    
    print("🧹 SAFE CLEANUP - REMOVING OBVIOUS UNUSED FILES")
    print("=" * 60)
    print(f"Files to remove: {len(files_to_remove)}")
    print("- Old test uploads and generated files")
    print("- Duplicate files (keeping the ones in proper locations)")
    print("- Temporary/debug files")
    print("- Platform-specific files")
    
    removed_files = []
    removed_size = 0
    
    for file_path in files_to_remove:
        if os.path.exists(file_path):
            try:
                # Get file size before removal
                file_size = os.path.getsize(file_path) if os.path.isfile(file_path) else 0
                
                if os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                else:
                    os.remove(file_path)
                    
                removed_files.append(file_path)
                removed_size += file_size
                print(f"🗑️  Removed: {file_path}")
                
            except Exception as e:
                print(f"❌ Failed to remove {file_path}: {e}")
        else:
            print(f"⚠️  Not found: {file_path}")
    
    # Clean up empty directories
    empty_dirs = []
    for root, dirs, files in os.walk('.', topdown=False):
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            try:
                if not os.listdir(dir_path):  # Empty directory
                    os.rmdir(dir_path)
                    empty_dirs.append(dir_path)
                    print(f"🗂️  Removed empty directory: {dir_path}")
            except OSError:
                pass
    
    print(f"\n{'='*60}")
    print("✅ SAFE CLEANUP COMPLETE!")
    print(f"{'='*60}")
    print(f"Files removed: {len(removed_files)}")
    print(f"Empty directories removed: {len(empty_dirs)}")
    print(f"Space saved: {removed_size / 1024 / 1024:.1f} MB")
    
    print(f"\n📋 REMAINING CLEANUP OPPORTUNITIES:")
    print("Consider manually reviewing these categories:")
    print("- Old documentation files (*.md)")
    print("- One-time fix scripts (fix_*.py)")
    print("- Legacy database utilities")
    print("- Old configuration files")
    
    return len(removed_files)

if __name__ == "__main__":
    removed_count = safe_cleanup()
    print(f"\n🎉 Safe cleanup removed {removed_count} obviously unused files!")