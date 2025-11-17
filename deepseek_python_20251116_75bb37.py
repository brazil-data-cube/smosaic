import os
from collections import defaultdict

def check_s2_integrity(root_folder):
    """
    Check Sentinel-2 folder structure integrity by counting TIFF files
    across different bands and identifying missing files.
    Ignores S2A/S2B differences, focuses on band, date, and scene.
    """
    
    # Dictionary to store scene information
    # Structure: {scene_code: {date: {band: [file_names]}}}
    scene_data = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    
    # Walk through all directories
    for root, dirs, files in os.walk(root_folder):
        for file in files:
            if file.endswith('.tif') or file.endswith('.tiff'):
                file_path = os.path.join(root, file)
                
                try:
                    # Parse filename components
                    parts = file.split('_')
                    if len(parts) >= 6:
                        band = parts[1]  # B02, B03, B04, SCL, etc.
                        date = parts[2]  # 20250115T135701
                        scene = parts[5]  # 22MCC, 21MZU, etc.
                        
                        # Store file information (ignore S2A/S2B)
                        scene_data[scene][date][band].append(file)
                        
                except (IndexError, ValueError) as e:
                    print(f"Warning: Could not parse filename: {file}")
                    continue
    
    # Analyze the data
    print("=== Sentinel-2 Integrity Check ===")
    print(f"Root folder: {root_folder}")
    print()
    
    all_missing_files = []
    total_missing_count = 0
    
    for scene in sorted(scene_data.keys()):
        print(f"Scene: {scene}")
        print("-" * 50)
        
        scene_missing_count = 0
        
        for date in sorted(scene_data[scene].keys()):
            bands_data = scene_data[scene][date]
            bands_present = set(bands_data.keys())
            
            # Get file counts for each band
            files_per_band = {band: len(files) for band, files in bands_data.items()}
            
            # Find the expected number of files (most common count)
            if files_per_band:
                from collections import Counter
                count_freq = Counter(files_per_band.values())
                expected_count = count_freq.most_common(1)[0][0]
            else:
                expected_count = 0
            
            # Check for inconsistent file counts
            inconsistent_bands = {band: count for band, count in files_per_band.items() 
                                if count != expected_count}
            
            if inconsistent_bands:
                print(f"  Date: {date}")
                print(f"    Expected: {expected_count} files per band")
                print(f"    Actual: {files_per_band}")
                
                # Find missing files in bands with fewer files
                for band, actual_count in files_per_band.items():
                    if actual_count < expected_count:
                        missing_count = expected_count - actual_count
                        print(f"    Band {band} is missing {missing_count} file(s):")
                        
                        # Find what specific files are missing
                        find_missing_files_for_band(scene, date, band, bands_data, 
                                                  expected_count, all_missing_files)
                        scene_missing_count += missing_count
                        total_missing_count += missing_count
            else:
                if expected_count > 0:
                    print(f"  Date: {date} - OK ({expected_count} files per band)")
                else:
                    print(f"  Date: {date} - NO FILES")
        
        # Check for completely missing bands
        scene_missing_count += find_completely_missing_bands(scene_data, scene, all_missing_files)
        total_missing_count += scene_missing_count
        
        if scene_missing_count > 0:
            print(f"  Total missing files in scene {scene}: {scene_missing_count}")
        print()
    
    # Summary
    print("=== SUMMARY ===")
    total_scenes = len(scene_data)
    total_dates = sum(len(dates) for dates in scene_data.values())
    
    print(f"Total scenes processed: {total_scenes}")
    print(f"Total dates found: {total_dates}")
    print(f"Total missing files: {total_missing_count}")
    
    if all_missing_files:
        print("\nAll missing files:")
        for missing_file in sorted(all_missing_files):
            print(f"  {missing_file}")
    
    return all_missing_files

def find_missing_files_for_band(scene, date, band, bands_data, expected_count, all_missing_files):
    """Find specific missing files for a band that has fewer files than expected."""
    
    # Get existing files for this band
    existing_files = bands_data[band]
    
    # Find a sample file from another band to use as template
    sample_file = None
    for other_band, files in bands_data.items():
        if other_band != band and files:
            sample_file = files[0]
            break
    
    if not sample_file:
        return
    
    # Extract base pattern from sample file
    sample_parts = sample_file.split('_')
    
    # Generate what files should exist for this band
    for i in range(expected_count):
        # Construct expected filename
        expected_filename = '_'.join([
            sample_parts[0],  # S2A/S2B (ignored but kept for naming)
            band,            # target band
            date,            # target date
            sample_parts[3], # N0511
            sample_parts[4], # R067
            scene,           # target scene
            sample_parts[6] if len(sample_parts) > 6 else ""  # processing date
        ]).strip('_')
        
        # Check if this specific file exists
        file_exists = any(expected_filename == f for f in existing_files)
        
        if not file_exists:
            print(f"      - {expected_filename}")
            all_missing_files.append(expected_filename)

def find_completely_missing_bands(scene_data, scene, all_missing_files):
    """Find bands that are completely missing for some dates in a scene."""
    missing_count = 0
    
    # Get all bands that exist in this scene (across all dates)
    all_bands_in_scene = set()
    for date in scene_data[scene].keys():
        all_bands_in_scene.update(scene_data[scene][date].keys())
    
    # For each date, check if all bands are present
    for date in sorted(scene_data[scene].keys()):
        bands_present = set(scene_data[scene][date].keys())
        missing_bands = all_bands_in_scene - bands_present
        
        for missing_band in missing_bands:
            # Find expected file count for this band from other dates
            expected_count = 0
            sample_file = None
            
            for other_date in scene_data[scene].keys():
                if missing_band in scene_data[scene][other_date]:
                    band_files = scene_data[scene][other_date][missing_band]
                    if band_files:
                        expected_count = len(band_files)
                        sample_file = band_files[0]
                        break
            
            if sample_file and expected_count > 0:
                print(f"  Date: {date}")
                print(f"    Band {missing_band} is completely missing:")
                
                # Generate all missing files for this missing band
                sample_parts = sample_file.split('_')
                for i in range(expected_count):
                    missing_filename = '_'.join([
                        sample_parts[0],  # S2A/S2B
                        missing_band,     # missing band
                        date,             # target date
                        sample_parts[3],  # N0511
                        sample_parts[4],  # R067
                        scene,            # target scene
                        sample_parts[6] if len(sample_parts) > 6 else ""  # processing date
                    ]).strip('_')
                    
                    print(f"      - {missing_filename}")
                    all_missing_files.append(missing_filename)
                    missing_count += 1
    
    return missing_count

if __name__ == "__main__":
    # Set your root folder path here
    root_folder = "S2_L2A-1"  # Change this to your actual path
    
    if not os.path.exists(root_folder):
        print(f"Error: Folder '{root_folder}' does not exist!")
    else:
        missing_files = check_s2_integrity(root_folder)