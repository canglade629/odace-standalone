#!/usr/bin/env python3
"""
Script to move existing files in GCS bucket to /raw/ structure.

This script organizes files from the bucket root into the proper /raw/{domain}/ structure.
"""
import os
from google.cloud import storage


def move_files_to_raw():
    """Move files from bucket root to /raw/ structure."""
    
    # Configuration
    project_id = "icc-project-472009"
    bucket_name = "jaccueille"
    
    # Initialize GCS client
    client = storage.Client(project=project_id)
    bucket = client.bucket(bucket_name)
    
    # List all blobs in the bucket
    print(f"Scanning bucket: {bucket_name}")
    blobs = list(bucket.list_blobs())
    
    print(f"Found {len(blobs)} total objects")
    
    # Define domain mappings (based on directory names shown in screenshot)
    domain_mappings = {
        'accueillants/': 'raw/accueillants/',
        'geo/': 'raw/geo/',
        'logement/': 'raw/logement/',
        'transport/': 'raw/transport/',
        'zones_attraction/': 'raw/zones_attraction/',
        'raw/': 'raw/'  # Already in raw, keep as is
    }
    
    moved_count = 0
    already_in_raw = 0
    skipped = 0
    
    for blob in blobs:
        source_name = blob.name
        
        # Skip if already in raw/
        if source_name.startswith('raw/'):
            already_in_raw += 1
            print(f"✓ Already in raw: {source_name}")
            continue
        
        # Skip if it's a directory marker (ends with /)
        if source_name.endswith('/'):
            skipped += 1
            continue
        
        # Determine target path
        target_name = None
        for prefix, raw_prefix in domain_mappings.items():
            if source_name.startswith(prefix) and prefix != 'raw/':
                # Move to raw structure
                target_name = source_name.replace(prefix, raw_prefix, 1)
                break
        
        if target_name:
            print(f"Moving: {source_name} -> {target_name}")
            
            # Copy to new location
            source_blob = bucket.blob(source_name)
            bucket.copy_blob(source_blob, bucket, target_name)
            
            # Optionally delete the old file (commented out for safety)
            # source_blob.delete()
            # print(f"  Deleted old file: {source_name}")
            
            moved_count += 1
        else:
            print(f"⚠️  Skipping (no mapping): {source_name}")
            skipped += 1
    
    print("\n" + "="*60)
    print("Summary:")
    print(f"  Moved: {moved_count} files")
    print(f"  Already in raw/: {already_in_raw} files")
    print(f"  Skipped: {skipped} files")
    print("="*60)
    print("\n⚠️  Note: Old files were NOT deleted. Review the new structure,")
    print("   then manually delete old files if everything looks good.")


if __name__ == "__main__":
    print("🗂️  File Organization Script for Odace Data Pipeline")
    print("="*60)
    print("This script will copy files to the /raw/ structure.")
    print("Original files will be preserved (not deleted).")
    print("="*60)
    
    response = input("\nProceed? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        try:
            move_files_to_raw()
            print("\n✅ File organization complete!")
        except Exception as e:
            print(f"\n❌ Error: {e}")
    else:
        print("Aborted.")

