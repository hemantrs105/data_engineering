# -*- coding: utf-8 -*-
"""
Created on Thu Feb 12 16:32:46 2026

@author: hemants
"""

import os
import openeo
import geopandas as gpd
import pandas as pd

def interactive_downloader():
    print("--- UNIVERSAL COPERNICUS DOWNLOADER (openEO) ---")
    
    # 1. Connect and Authenticate
    print("Connecting to Copernicus Data Space Ecosystem...")
    connection = openeo.connect("openeo.cloud")
    connection.authenticate_oidc()
    print("Authenticated successfully.\n")

    # 2. Search and Select Collection
    collections = connection.list_collections()
    all_ids = [c['id'] for c in collections]
    
    selected_collection_id = None
    while not selected_collection_id:
        search_term = input("Enter a search term for the dataset (e.g., 'LAI', 'Sentinel', 'Agera5'): ").strip().lower()
        matches = [cid for cid in all_ids if search_term in cid.lower()]
        
        if not matches:
            print("No collections found. Try a different term.")
            continue
        
        print(f"\nFound {len(matches)} matching collections:")
        for idx, cid in enumerate(matches):
            print(f"[{idx}] {cid}")
            
        selection = input("\nEnter the ID of the collection to select (or 'r' to retry): ").strip()
        if selection.lower() == 'r':
            continue
        
        try:
            selected_collection_id = matches[int(selection)]
            print(f"Selected: {selected_collection_id}")
        except (ValueError, IndexError):
            print("Invalid selection. Please enter the number corresponding to the collection.")

    # 3. List and Select Bands
    print(f"\nFetching metadata for {selected_collection_id}...")
    metadata = connection.describe_collection(selected_collection_id)
    
    # Try to extract band names from various metadata structures
    available_bands = []
    try:
        # Common structure for optical/sar data
        cube_dim = metadata.get('cube:dimensions', {})
        if 'bands' in cube_dim:
            available_bands = cube_dim['bands'].get('values', [])
        # Alternative structure
        elif 'summaries' in metadata and 'eo:bands' in metadata['summaries']:
             available_bands = [b['name'] for b in metadata['summaries']['eo:bands']]
    except Exception as e:
        print(f"Warning: Could not auto-parse bands ({e}).")

    if available_bands:
        print(f"\nAvailable Bands: {available_bands}")
        band_input = input("Enter bands to download (comma-separated, e.g., 'LAI,QFLAG' or 'B04,B08'): ").strip()
        selected_bands = [b.strip() for b in band_input.split(',')]
    else:
        print("Could not automatically list bands. You must know the band names manually.")
        band_input = input("Enter band names manually (comma-separated): ").strip()
        selected_bands = [b.strip() for b in band_input.split(',')]

    # 4. Get Time Range
    print("\n--- Time Configuration ---")
    start_date = input("Enter Start Date (YYYY-MM-DD): ").strip()
    end_date = input("Enter End Date (YYYY-MM-DD): ").strip()

    # 5. Get Shapefile
    print("\n--- Spatial Configuration ---")
    while True:
        shapefile_path = input("Enter full path to Shapefile (.shp): ").strip().strip('"')
        if os.path.exists(shapefile_path):
            break
        print("File not found. Please try again.")

    output_folder = input("Enter output folder path: ").strip().strip('"')
    os.makedirs(output_folder, exist_ok=True)

    # 6. Process Geometry (Bounding Box)
    print("\nReading shapefile...")
    gdf = gpd.read_file(shapefile_path).to_crs(epsg=4326)
    bbox = gdf.total_bounds
    spatial_bounds = {"west": bbox[0], "south": bbox[1], "east": bbox[2], "north": bbox[3]}

    # 7. Construct Datacube
    print("\nConstructing processing graph...")
    datacube = connection.load_collection(
        selected_collection_id,
        spatial_extent=spatial_bounds,
        temporal_extent=[start_date, end_date],
        bands=selected_bands
    )
    
    # Save as GTiff
    datacube = datacube.save_result(format="GTiff")

    # 8. Submit Batch Job
    job_title = f"Download_{selected_collection_id}"
    print(f"\nSubmitting batch job: {job_title}")
    
    try:
        job = connection.create_job(datacube, title=job_title)
        print(f"Job created with ID: {job.job_id}")
        print("Waiting for server processing (this may take time)...")
        
        job.start_and_wait()
        
        print("\nProcessing complete. Downloading results...")
        results = job.get_results()
        results.download_files(output_folder)
        
        print(f"\nSUCCESS! Files downloaded to: {output_folder}")
        
    except Exception as e:
        print(f"\nAn error occurred during processing: {e}")

if __name__ == "__main__":
    interactive_downloader()