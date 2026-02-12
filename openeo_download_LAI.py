# -*- coding: utf-8 -*-
"""
Created on Wed Feb 11 15:02:34 2026

@author: hemants
"""

import os
import openeo
import geopandas as gpd

def download_lai_bbox_timeseries(shapefile_path, start_date, end_date, output_folder):
    """
    Submits an openEO batch job to download a bounding-box time series of LAI images.
    """
    os.makedirs(output_folder, exist_ok=True)

    connection = openeo.connect("openeofed.dataspace.copernicus.eu")
    connection.authenticate_oidc()

    # 1. Read shapefile and get ONLY the bounding box
    print("Reading shapefile and calculating bounding box...")
    gdf = gpd.read_file(shapefile_path).to_crs(epsg=4326)
    bbox = gdf.total_bounds
    spatial_bounds = {
        "west": bbox[0],
        "south": bbox[1],
        "east": bbox[2],
        "north": bbox[3]
    }

    # 2. Load Datacube using only the bounding box
    # We bypass filter_spatial() entirely to avoid payload size errors
    datacube = connection.load_collection(
        "CGLS_LAI300_V1_GLOBAL",
        spatial_extent=spatial_bounds,
        temporal_extent=[start_date, end_date],
        bands=['LAI']
    )

    # 3. Define Output Format
    datacube = datacube.save_result(format="GTiff")

    # 4. Create, Run, and Download Batch Job
    print(f"Submitting batch job for BBOX of dates {start_date} to {end_date}...")
    job = connection.create_job(datacube, title="LAI_BBOX_Timeseries")
    
    print("Processing on CDSE servers. This may take several minutes...")
    job.start_and_wait()

    print("Processing complete. Downloading files...")
    results = job.get_results()
    results.download_files(output_folder)
    
    print(f"All rectangular bounding box images downloaded to: {os.path.abspath(output_folder)}")

# Example Execution:
download_lai_bbox_timeseries(
    shapefile_path=r"C:\Z DRIVE\Assam_kharif_2025\shapefile\kharif2025_final_shp_24102025_with_Notification.shp", 
    start_date="2025-08-01", 
    end_date="2025-11-30", 
    output_folder=r"C:\Z DRIVE\Assam_kharif_2025\semiphysical\datasets\LAI\2025\raw_downloads"
)

