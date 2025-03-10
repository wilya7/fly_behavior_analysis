#!/usr/bin/env python3
"""
Behavioral Annotation Data Conversion Tool

This script converts behavioral annotation data from Drosophila fly videos (annotated via ImageJ)
into a more structured and analysis-friendly format. It processes CSV files containing frame
annotations of grooming events and generates timeline tables, event lists, visualizations,
and summary statistics.
"""

import argparse
import os
import sys
import logging
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Tuple, Optional, Union, Dict, Any
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataValidationError(Exception):
    """Custom exception for data validation errors."""
    pass

def process_csv(file_path: Union[str, Path], error_log: Optional[Dict[str, Any]] = None) -> Optional[pd.DataFrame]:
    """
    Process and validate a CSV file containing behavioral annotation data.
    
    This function performs several validation checks:
    1. Checks if the 'Frame' column exists in the CSV
    2. Ensures all frame entries can be converted to integers
    3. Verifies there's an even number of entries (alternating start/stop frames)
    4. Confirms frames are in strictly increasing order
    
    Args:
        file_path: Path to the CSV file to process
        error_log: Optional dictionary to store error information for batch processing
        
    Returns:
        DataFrame containing valid frame data if all checks pass, None otherwise
        
    Raises:
        DataValidationError: If any validation check fails and error_log is not provided
    """
    file_path = Path(file_path)
    filename = file_path.name
    
    try:
        # Read the CSV file
        logger.info(f"Reading file: {filename}")
        df = pd.read_csv(file_path)
        
        # Check if 'Frame' column exists
        if 'Frame' not in df.columns:
            error_msg = f"File {filename} is missing the 'Frame' column"
            if error_log is not None:
                error_log.update({
                    'filename': filename,
                    'error_type': 'Missing Column',
                    'details': error_msg,
                    'frame': None
                })
                logger.error(error_msg)
                return None
            else:
                raise DataValidationError(error_msg)
        
        # Extract the Frame column
        frames = df['Frame']
        
        # Check if all values can be converted to integers
        try:
            frames = frames.astype(int)
        except ValueError:
            error_msg = f"File {filename} contains non-numeric values in the 'Frame' column"
            if error_log is not None:
                error_log.update({
                    'filename': filename,
                    'error_type': 'Non-numeric Values',
                    'details': error_msg,
                    'frame': None
                })
                logger.error(error_msg)
                return None
            else:
                raise DataValidationError(error_msg)
        
        # Check if number of entries is even
        if len(frames) % 2 != 0:
            error_msg = f"File {filename} contains an odd number of frame entries ({len(frames)})"
            if error_log is not None:
                error_log.update({
                    'filename': filename,
                    'error_type': 'Odd Entry Count',
                    'details': error_msg,
                    'frame': None
                })
                logger.error(error_msg)
                return None
            else:
                raise DataValidationError(error_msg)
        
        # Check if frames are in strictly increasing order
        for i in range(1, len(frames)):
            if frames.iloc[i] <= frames.iloc[i-1]:
                error_msg = f"File {filename} contains non-increasing frame numbers at position {i}"
                problematic_frame = frames.iloc[i]
                if error_log is not None:
                    error_log.update({
                        'filename': filename,
                        'error_type': 'Non-increasing Frames',
                        'details': error_msg,
                        'frame': problematic_frame
                    })
                    logger.error(error_msg)
                    return None
                else:
                    raise DataValidationError(f"{error_msg} (frame: {problematic_frame})")
        
        # If all checks pass, return the extracted frames as a DataFrame
        logger.info(f"File {filename} validated successfully with {len(frames)} frame entries")
        return pd.DataFrame({'Frame': frames})
    
    except Exception as e:
        # Catch any other exceptions (file not found, permission issues, etc.)
        error_msg = f"Error processing file {filename}: {str(e)}"
        if error_log is not None:
            error_log.update({
                'filename': filename,
                'error_type': 'Processing Error',
                'details': error_msg,
                'frame': None
            })
            logger.error(error_msg)
            return None
        else:
            raise DataValidationError(error_msg) from e

def parse_arguments():
    """
    Parse command line arguments for the data conversion tool.
    
    Returns:
        argparse.Namespace: Parsed command line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Convert behavioral annotation data from ImageJ CSV files to structured format."
    )
    parser.add_argument(
        "--input", 
        type=str, 
        required=True, 
        help="Path to input CSV file or directory containing CSV files"
    )
    parser.add_argument(
        "--output", 
        type=str, 
        required=True, 
        help="Path to output directory for storing results"
    )
    parser.add_argument(
        "--total_frames", 
        type=int, 
        default=8999, 
        help="Total number of frames to consider (default: 8999)"
    )
    
    return parser.parse_args()


def validate_args(args):
    """
    Validate the input arguments.
    
    Args:
        args (argparse.Namespace): Parsed command line arguments.
        
    Returns:
        bool: True if arguments are valid, False otherwise.
    """
    # Check if input path exists
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input path '{args.input}' does not exist.")
        return False
        
    # Check if output directory exists - if it does, exit
    output_path = Path(args.output)
    if output_path.exists():
        print(f"Error: Output directory '{args.output}' already exists. Please specify a new directory.")
        return False
        
    # Validate total_frames is positive
    if args.total_frames <= 0:
        print("Error: total_frames must be a positive integer.")
        return False
        
    return True


def main():
    """
    Main function that orchestrates the data processing pipeline.
    
    This function:
    1. Parses and validates command line arguments
    2. Creates the output directory
    3. Processes input files and generates output files
    4. Generates summary statistics and reports
    """
    # Parse command-line arguments
    args = parse_arguments()
    
    # Validate arguments
    if not validate_args(args):
        sys.exit(1)
    
    # Create output directory
    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=False)
    
    print(f"Starting processing...")
    print(f"Input: {args.input}")
    print(f"Output: {args.output}")
    print(f"Total frames: {args.total_frames}")
    
    # TODO: Implement the rest of the processing pipeline
    
    print("Processing complete.")


if __name__ == "__main__":
    main()