# -*- coding: utf-8 -*-
"""
Created on Fri Feb 13 15:37:20 2026

@author: hemants
"""

import rasterio
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm, rankdata
import os

def normalize_raster_to_range(input_path, output_path, min_val, max_val):
    """
    Transforms a raster to a normal distribution strictly fitted between 
    min_val and max_val.
    """
    print(f"--- Processing: {input_path} ---")
    
    with rasterio.open(input_path) as src:
        profile = src.profile
        data = src.read(1)
        nodata = src.nodata

        # 1. Create Mask for Valid Data
        if nodata is not None:
            mask = data != nodata
        else:
            mask = np.isfinite(data)
        
        valid_pixels = data[mask]

        if valid_pixels.size == 0:
            print("Error: No valid pixels found in raster.")
            return None

        # 2. Dynamic Parameter Calculation
        # Mean is the midpoint; Sigma is range width / 6 (for +/- 3 sigma coverage)
        target_mean = (min_val + max_val) / 2.0
        target_sigma = (max_val - min_val) / 6.0

        print(f"Target Stats -> Mean: {target_mean:.4f}, Sigma: {target_sigma:.4f}")

        # 3. Rank-Based Transformation (Quantile Normalization)
        # Get percentile ranks (0.0 to 1.0)
        ranks = rankdata(valid_pixels, method='average')
        # We divide by N+1 to avoid 0.0 or 1.0 exactly (which map to infinity)
        percentiles = ranks / (len(valid_pixels) + 1)

        # Convert to Standard Normal (Mean=0, Sigma=1)
        z_scores = norm.ppf(percentiles)

        # 4. Scale to Target Range
        transformed_pixels = (z_scores * target_sigma) + target_mean

        # 5. Clip to strictly enforce bounds
        # This handles the extreme tails (<0.3% of data)
        transformed_pixels = np.clip(transformed_pixels, min_val, max_val)

        # 6. Reconstruct Output Raster
        output_data = np.full_like(data, nodata, dtype='float32') if nodata else np.zeros_like(data, dtype='float32')
        output_data[mask] = transformed_pixels

        # Update profile
        profile.update(dtype=rasterio.float32, count=1, nodata=nodata)

        with rasterio.open(output_path, 'w', **profile) as dst:
            dst.write(output_data, 1)

    print(f"Saved transformed raster to: {output_path}")
    return output_path

def compare_histograms(input_path, output_path, plot_output="histogram_comparison.png"):
    """
    Reads both rasters and plots their histograms side-by-side for verification.
    Includes robust handling for NaN and NoData values.
    """
    print("--- Generating Comparison Plot ---")
    
    data_map = {}
    
    # Read both files
    for label, path in [('Original Input', input_path), ('Transformed Output', output_path)]:
        with rasterio.open(path) as src:
            data = src.read(1)
            nodata = src.nodata
            
            # 1. Flatten the array
            flattened_data = data.flatten()
            
            # 2. Mask out Nodata (if it exists and is not NaN)
            if nodata is not None and not np.isnan(nodata):
                valid_data = flattened_data[flattened_data != nodata]
            else:
                valid_data = flattened_data
                
            # 3. CRITICAL: Always remove NaNs and Infs explicitly
            # This fixes the "autodetected range of [nan, nan]" error
            valid_data = valid_data[np.isfinite(valid_data)]
            
            data_map[label] = valid_data

    # Setup Plot
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # Plot Input
    axes[0].hist(data_map['Original Input'], bins=100, color='gray', alpha=0.7, edgecolor='black', linewidth=0.5)
    axes[0].set_title("Original Input Histogram", fontsize=14, fontweight='bold')
    axes[0].set_xlabel("Pixel Value")
    axes[0].set_ylabel("Frequency")
    axes[0].grid(axis='y', alpha=0.3)

    # Plot Output
    out_data = data_map['Transformed Output']
    
    # Check if data exists before plotting to avoid empty errors
    if len(out_data) == 0:
        print("Error: Output raster contains no valid data (all NaN/NoData).")
        return

    axes[1].hist(out_data, bins=100, color='#2ca02c', alpha=0.7, edgecolor='black', linewidth=0.5)
    axes[1].set_title("Transformed Output Histogram", fontsize=14, fontweight='bold')
    axes[1].set_xlabel("Pixel Value")
    
    # Add vertical lines for bounds
    min_val, max_val = np.min(out_data), np.max(out_data)
    axes[1].axvline(min_val, color='red', linestyle='--', label=f'Min: {min_val:.2f}')
    axes[1].axvline(max_val, color='red', linestyle='--', label=f'Max: {max_val:.2f}')
    axes[1].axvline(np.mean(out_data), color='blue', linewidth=2, label=f'Mean: {np.mean(out_data):.2f}')
    axes[1].legend()
    axes[1].grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(plot_output, dpi=150)
    print(f"Comparison plot saved to: {plot_output}")
    plt.show()

# ==========================================
# Execution Block
# ==========================================

# 1. Define Paths
input_path = r"C:\Z DRIVE\Assam_kharif_2025\semiphysical\datasets\LAI\2025\processed_rasters\16022026\s3LAI_convertedYield.tif"
output_path = r"C:\Z DRIVE\Assam_kharif_2025\semiphysical\datasets\LAI\2025\processed_rasters\16022026\renorm_s3LAI_convertedYield.tif"

# 2. Run Transformation
normalize_raster_to_range(input_path, output_path, min_val=0.9, max_val=2.15)

# 3. Visual Verification
compare_histograms(input_path, output_path)



