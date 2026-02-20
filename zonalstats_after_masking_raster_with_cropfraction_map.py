# -*- coding: utf-8 -*-
"""
Created on Thu Feb 12 12:18:59 2026

@author: hemants
"""
import rasterio
from rasterio.enums import Resampling
import numpy as np
import pandas as pd
from rasterstats import zonal_stats
import os
from tqdm import tqdm

def process_crop_stats(cropmap_path, input_raster_path, shapefile_path, threshold, output_csv, save_intermediate=False):
    """
    Calculates crop fraction, masks an input raster based on a threshold, 
    and performs zonal statistics with progress tracking.
    
    Args:
        cropmap_path (str): Path to binary 10m crop map.
        input_raster_path (str): Path to the coarser input raster (e.g., NDVI, EVI).
        shapefile_path (str): Path to the zone shapefile.
        threshold (float): Fraction threshold (0.0 to 1.0) to classify a pixel as crop.
        output_csv (str): Path where the final CSV will be saved.
        save_intermediate (bool): If True, saves crop_fraction and masked_raster to the output folder.
    """
    
    # distinct steps for the progress bar
    steps = 5 
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_csv)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with tqdm(total=steps, desc="Processing Pipeline") as pbar:
        
        # --- Step 1: Read Reference Raster ---
        pbar.set_description("Reading Input Raster")
        with rasterio.open(input_raster_path) as src_lr:
            lr_meta = src_lr.meta.copy()
            lr_shape = (src_lr.height, src_lr.width)
            input_data = src_lr.read(1)
            nodata_val = src_lr.nodata
            # Handle case where nodata is None
            if nodata_val is None:
                nodata_val = -9999
        pbar.update(1)

        # --- Step 2: Resample 10m Binary Map to Crop Fraction ---
        pbar.set_description("Resampling Crop Map to Fraction")
        with rasterio.open(cropmap_path) as src_hr:
            # Resampling.average calculates the mean of values within the target pixel window.
            # For a binary (0/1) map, the mean is exactly the fraction of '1's.
            crop_fraction = src_hr.read(
                1,
                out_shape=lr_shape,
                resampling=Resampling.average
            ).astype(np.float32)
        pbar.update(1)

        # --- Step 3: Create Mask and Apply to Raster ---
        pbar.set_description("Masking Raster based on Threshold")
        # Pixels with crop fraction >= threshold are valid (1), others are masked
        binary_mask = (crop_fraction >= threshold)
        
        # Initialize masked array with nodata
        masked_raster = np.full(lr_shape, nodata_val, dtype=np.float32)
        
        # Fill valid pixels with input data
        # Note: input_data might need handling if it contains its own nodata, 
        # but here we strictly mask by the crop map.
        valid_indices = np.where(binary_mask)
        masked_raster[valid_indices] = input_data[valid_indices]
        
        # Update metadata for saving intermediate/temp files
        lr_meta.update(dtype=rasterio.float32, nodata=nodata_val, compress='lzw')
        pbar.update(1)

        # --- Step 4: Save Intermediate Files (Optional) ---
        pbar.set_description("Handling Intermediate Files")
        temp_masked_tif = os.path.join(output_dir, "temp_masked_for_stats.tif")
        
        # Always save temp file for zonal_stats to read
        with rasterio.open(temp_masked_tif, 'w', **lr_meta) as dst:
            dst.write(masked_raster, 1)

        if save_intermediate:
            # Save the Crop Fraction Raster
            frac_path = os.path.join(output_dir, "intermediate_crop_fraction3.tif")
            with rasterio.open(frac_path, 'w', **lr_meta) as dst:
                dst.write(crop_fraction, 1)
            
            # Save the Final Masked Raster (keep the temp file as permanent)
            masked_path = os.path.join(output_dir, "intermediate_masked_input3.tif")
            # We can just copy or write again. Writing is safer to ensure closure.
            with rasterio.open(masked_path, 'w', **lr_meta) as dst:
                dst.write(masked_raster, 1)
        pbar.update(1)

        # --- Step 5: Zonal Statistics ---
        pbar.set_description("Computing Zonal Statistics")
        stats_list = ['mean', 'median', 'majority', 'minority', 'max', 'min', 'std', 'count']
        
        # Calculate stats
        zonal_results = zonal_stats(
            shapefile_path, 
            temp_masked_tif, 
            stats=stats_list,
            # add_stats={
            #     'p25': lambda x: np.percentile(x, 25), 
            #     'p75': lambda x: np.percentile(x, 75)
            # },
            geojson_out=True
        )

        # Export to CSV
        final_data = [entry['properties'] for entry in zonal_results]
        df = pd.DataFrame(final_data)
        df.to_csv(output_csv, index=False)
        
        # Cleanup temp file if we didn't want to save intermediates
        if not save_intermediate and os.path.exists(temp_masked_tif):
            os.remove(temp_masked_tif)
        elif save_intermediate:
            # If saving intermediates, we might want to rename or keep the temp.
            # The code above saved specific named files, so we can clean the temp 
            # one to avoid clutter, or leave it. Cleaning it here:
            if os.path.exists(temp_masked_tif):
                os.remove(temp_masked_tif)
                
        pbar.update(1)
        pbar.set_description("Complete")



# Example Usage: process_crop_stats(cropmap_path, input_raster_path, shapefile_path, threshold, output_csv):
process_crop_stats(
    cropmap_path = r"C:\Z DRIVE\Assam_kharif_2025\final_cropmap_2025\Assam_salipaddy2025_final_cropmap.tif", 
    input_raster_path = r"C:\Z DRIVE\Assam_kharif_2025\semiphysical\datasets\LAI\2025\processed_rasters\historic_LAI\LAIX_S3_2022.tif",
    shapefile_path = r"C:\Z DRIVE\Assam_kharif_2025\shapefile\kharif2025_final_shp_24102025_with_Notification.shp",
    threshold = 0.8,
    output_csv = r"C:\Z DRIVE\Assam_kharif_2025\semiphysical\datasets\LAI\2025\processed_rasters\LAIX_S3_2022.csv",
    save_intermediate = True)