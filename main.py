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
from typing import Tuple, Optional, Union, Dict, Any, List
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

def generate_timeline(frames: pd.Series, total_frames: int) -> pd.DataFrame:
    """
    Generate a timeline table from the extracted frame numbers.
    
    This function:
    1. Pairs frame numbers as alternating start and stop values
    2. Validates each pair (start <= stop)
    3. Creates a DataFrame with rows for frames 1 to N
    4. For each valid event pair, updates the corresponding rows in the DataFrame
    
    Args:
        frames: Series of frame numbers (assumed to be validated and even in count)
        total_frames: Total number of frames to consider (N)
        
    Returns:
        DataFrame containing the timeline with columns: Frame, GroomingFlag, EventID
        
    Raises:
        ValueError: If any pair is invalid (start > stop)
    """
    # Create a timeline DataFrame with frames 1 to N
    timeline = pd.DataFrame({
        'Frame': range(1, total_frames + 1),
        'GroomingFlag': 0,
        'EventID': 0
    })
    
    # Convert frames to numpy array if it's a pandas Series
    frame_values = frames.values if isinstance(frames, pd.Series) else np.array(frames)
    
    # Ensure we have an even number of frames (should be pre-validated)
    if len(frame_values) % 2 != 0:
        raise ValueError("Expected an even number of frame entries for pairing")
    
    # Create pairs of start and stop frames
    pairs = [(frame_values[i], frame_values[i+1]) for i in range(0, len(frame_values), 2)]
    
    # Update timeline for each valid pair
    for event_id, (start, stop) in enumerate(pairs, 1):
        # Validate that start <= stop
        if start > stop:
            raise ValueError(f"Invalid frame pair at index {event_id-1}: start ({start}) > stop ({stop})")
        
        # Ensure frames are within the valid range
        if start < 1:
            logger.warning(f"Event {event_id} has start frame ({start}) less than 1. Adjusted to 1.")
            start = 1
            
        if stop > total_frames:
            logger.warning(f"Event {event_id} has stop frame ({stop}) greater than {total_frames}. Adjusted to {total_frames}.")
            stop = total_frames
        
        # Update the timeline for this event
        mask = (timeline['Frame'] >= start) & (timeline['Frame'] <= stop)
        timeline.loc[mask, 'GroomingFlag'] = 1
        timeline.loc[mask, 'EventID'] = event_id
    
    return timeline

def generate_event_list(frames: pd.Series) -> pd.DataFrame:
    """
    Generate an event list from frame data, pairing them as alternating start and stop values.
    
    This function takes the frame numbers extracted from the CSV file and creates a DataFrame
    listing all events with their start and stop frames. Each event is assigned a unique ID
    that corresponds to the EventID used in the timeline.
    
    Args:
        frames: Series of frame numbers (assumed to be validated and even in count)
        
    Returns:
        DataFrame containing event list with columns: EventID, StartFrame, StopFrame
        
    Raises:
        ValueError: If any pair is invalid (start > stop) or if the input has an odd number of entries
    """
    # Convert frames to numpy array if it's a pandas Series
    frame_values = frames.values if isinstance(frames, pd.Series) else np.array(frames)
    
    # Ensure we have an even number of frames
    if len(frame_values) % 2 != 0:
        raise ValueError("Expected an even number of frame entries for pairing")
    
    # Create pairs of start and stop frames
    events = []
    for i in range(0, len(frame_values), 2):
        start = frame_values[i]
        stop = frame_values[i+1]
        
        # Validate that start <= stop
        if start > stop:
            raise ValueError(f"Invalid frame pair at index {i//2}: start ({start}) > stop ({stop})")
        
        # Add the event to our list
        events.append({
            'EventID': i//2 + 1,  # Start EventIDs from 1
            'StartFrame': start,
            'StopFrame': stop
        })
    
    # Create and return the DataFrame
    return pd.DataFrame(events)

def calculate_file_summary(filename: str, timeline_df: pd.DataFrame, event_list_df: pd.DataFrame, total_frames: int) -> Tuple[Dict[str, Any], List[int]]:
    """
    Calculate summary statistics for a processed file.
    
    Args:
        filename: Name of the processed file
        timeline_df: Timeline DataFrame for the file
        event_list_df: Event list DataFrame for the file
        total_frames: Total number of frames considered
        
    Returns:
        Tuple containing:
            - Dictionary with summary statistics for the file
            - List of event durations for calculating overall statistics
    """
    # Calculate event durations
    event_durations = [(row['StopFrame'] - row['StartFrame'] + 1) for _, row in event_list_df.iterrows()]
    
    # Count of grooming events
    num_events = len(event_list_df)
    
    # Total grooming duration (in frames)
    total_grooming_frames = timeline_df['GroomingFlag'].sum()
    
    # Average event duration
    avg_event_duration = np.mean(event_durations) if event_durations else 0
    
    # Median event duration
    median_event_duration = np.median(event_durations) if event_durations else 0
    
    # Standard deviation of event durations
    std_event_duration = np.std(event_durations) if event_durations else 0
    
    # Percentage of grooming frames relative to total
    grooming_percentage = (total_grooming_frames / total_frames) * 100
    
    # Create summary dictionary
    summary = {
        'filename': filename,
        'num_events': num_events,
        'total_grooming_frames': int(total_grooming_frames),
        'avg_event_duration': float(avg_event_duration),
        'median_event_duration': float(median_event_duration),
        'std_event_duration': float(std_event_duration),
        'grooming_percentage': float(grooming_percentage)
    }
    
    return summary, event_durations

def save_summary_report(summary_report: Dict[str, Any], output_dir: Path, total_frames: int) -> None:
    """
    Save the consolidated summary report as a CSV file.
    
    Args:
        summary_report: Dictionary containing summary statistics
        output_dir: Directory to save the report
        total_frames: Total number of frames considered per file
    """
    # Extract file summaries
    file_summaries = summary_report['file_summaries']
    
    if not file_summaries:
        logger.warning("No files were successfully processed. Cannot generate summary report.")
        return
    
    # Create DataFrame from file summaries
    summary_df = pd.DataFrame(file_summaries)
    
    # Calculate overall statistics
    all_event_durations = summary_report['all_event_durations']
    successful_files = summary_report['successful_files']
    total_events = summary_df['num_events'].sum()
    total_grooming_frames = summary_df['total_grooming_frames'].sum()
    
    # Calculate overall grooming percentage across all files
    overall_grooming_percentage = (total_grooming_frames / (successful_files * total_frames)) * 100 if successful_files > 0 else 0
    
    # Create overall summary row
    overall_summary = {
        'filename': 'OVERALL',
        'num_events': total_events,
        'total_grooming_frames': int(total_grooming_frames),
        'avg_event_duration': float(np.mean(all_event_durations)) if all_event_durations else 0,
        'median_event_duration': float(np.median(all_event_durations)) if all_event_durations else 0,
        'std_event_duration': float(np.std(all_event_durations)) if all_event_durations else 0,
        'grooming_percentage': float(overall_grooming_percentage)
    }
    
    # Append overall summary to the DataFrame
    summary_df = pd.concat([summary_df, pd.DataFrame([overall_summary])], ignore_index=True)
    
    # Save summary report
    summary_file = output_dir / "summary_report.csv"
    summary_df.to_csv(summary_file, index=False)
    logger.info(f"Saved consolidated summary report to {summary_file}")
    
def generate_timeline_plot(timeline_df: pd.DataFrame, output_path: Path) -> None:
    """
    Generate a timeline plot visualizing grooming events from the timeline DataFrame.
    
    This function creates a horizontal timeline visualization where grooming events
    are color-coded according to their EventID. The x-axis represents frame numbers,
    and colored segments indicate frames where grooming occurs.
    
    Args:
        timeline_df: DataFrame containing timeline data with columns:
            - Frame: Frame number
            - GroomingFlag: Binary indicator (0 = no grooming, 1 = grooming)
            - EventID: Identifier for each grooming event
        output_path: Path where the PNG image will be saved
        
    Returns:
        None. The plot is saved to the specified output path.
        
    Raises:
        ValueError: If the input DataFrame is empty or doesn't have required columns
    """
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
    from matplotlib.collections import LineCollection
    import numpy as np
    
    # Check if DataFrame is valid
    if timeline_df is None or timeline_df.empty:
        raise ValueError("Timeline DataFrame is empty or None")
    
    required_columns = ['Frame', 'GroomingFlag', 'EventID']
    if not all(col in timeline_df.columns for col in required_columns):
        raise ValueError(f"Timeline DataFrame must contain all required columns: {required_columns}")
    
    # Create a new figure with appropriate size
    plt.figure(figsize=(12, 3))
    
    # Get unique event IDs (excluding 0, which means no grooming)
    event_ids = sorted(timeline_df[timeline_df['EventID'] > 0]['EventID'].unique())
    
    # Create a colormap for different events (excluding black, which we'll use for non-grooming)
    num_events = len(event_ids)
    if num_events > 0:
        # Choose a colormap that works well for the number of events
        # Avoid colors that are too light to see
        colormap = plt.get_cmap('tab10', num_events)
        colors = [colormap(i) for i in range(num_events)]
    else:
        colors = []
    
    # Map event IDs to colors
    event_colors = {event_id: colors[i] for i, event_id in enumerate(event_ids)}
    
    # Create segments for each grooming event
    segments = []
    colors_list = []
    
    # Map event IDs in the timeline to colors
    for event_id in event_ids:
        # Get frames for this event
        event_frames = timeline_df[timeline_df['EventID'] == event_id]['Frame'].values
        
        if len(event_frames) > 0:
            # Determine start and end frames for continuous blocks
            diffs = np.diff(event_frames)
            break_points = np.where(diffs > 1)[0]
            
            # Extract continuous segments
            start_idx = 0
            for end_idx in np.append(break_points, len(event_frames) - 1):
                segment_start = event_frames[start_idx]
                segment_end = event_frames[end_idx]
                
                # Add segment as a line
                segments.append([(segment_start, 1), (segment_end, 1)])
                colors_list.append(event_colors[event_id])
                
                start_idx = end_idx + 1
    
    # Create the line collection for the timeline
    if segments:
        lc = LineCollection(segments, colors=colors_list, linewidths=10)
        plt.gca().add_collection(lc)
    
    # Set the axes limits and labels
    plt.xlim(timeline_df['Frame'].min(), timeline_df['Frame'].max())
    plt.ylim(0.5, 1.5)
    plt.yticks([])  # Hide y-axis ticks as they're not meaningful
    plt.xlabel('Frame Number')
    plt.title('Grooming Timeline')
    
    # Add a grid to make it easier to identify frame ranges
    plt.grid(axis='x', alpha=0.3)
    
    # Create a legend for event IDs
    if event_ids:
        legend_elements = [plt.Line2D([0], [0], color=event_colors[event_id], lw=4, 
                                     label=f'Event {event_id}') 
                          for event_id in event_ids]
        plt.legend(handles=legend_elements, loc='upper center', 
                  bbox_to_anchor=(0.5, -0.15), ncol=min(5, len(event_ids)))
    
    # Adjust layout to make room for the legend
    plt.tight_layout()
    
    # Save the figure to the specified output path
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    logger.info(f"Saved timeline plot to {output_path}")


def generate_box_plot(event_list_df: pd.DataFrame, output_path: Path) -> None:
    """
    Generate a box plot showing the distribution of grooming event durations.
    
    This function calculates the duration of each grooming event (StopFrame - StartFrame + 1)
    and creates a box plot to visualize the distribution of these durations.
    
    Args:
        event_list_df: DataFrame containing event data with columns:
            - EventID: Identifier for each grooming event
            - StartFrame: Frame where the event begins
            - StopFrame: Frame where the event ends
        output_path: Path where the PNG image will be saved
        
    Returns:
        None. The plot is saved to the specified output path.
        
    Raises:
        ValueError: If the input DataFrame is empty or doesn't have required columns
    """
    import matplotlib.pyplot as plt
    import numpy as np
    
    # Check if DataFrame is valid
    if event_list_df is None or event_list_df.empty:
        raise ValueError("Event list DataFrame is empty or None")
    
    required_columns = ['EventID', 'StartFrame', 'StopFrame']
    if not all(col in event_list_df.columns for col in required_columns):
        raise ValueError(f"Event list DataFrame must contain all required columns: {required_columns}")
    
    # Calculate durations for each event
    durations = event_list_df['StopFrame'] - event_list_df['StartFrame'] + 1
    
    # Create a new figure
    plt.figure(figsize=(8, 6))
    
    # Create the box plot
    box = plt.boxplot(durations, patch_artist=True)
    
    # Customize box plot appearance
    for patch in box['boxes']:
        patch.set_facecolor('lightblue')
    
    # Add individual points to show the raw data distribution
    plt.scatter(np.ones(len(durations)), durations, 
               alpha=0.6, color='darkblue', s=30, zorder=3)
    
    # Add labels and title
    plt.ylabel('Duration (frames)')
    plt.title('Distribution of Grooming Event Durations')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Remove x-axis ticks since we only have one category
    plt.xticks([])
    
    # Add basic statistics as text
    if len(durations) > 0:
        stats_text = (
            f"n = {len(durations)}\n"
            f"Mean = {durations.mean():.1f}\n"
            f"Median = {durations.median():.1f}\n"
            f"Min = {durations.min():.0f}\n"
            f"Max = {durations.max():.0f}"
        )
        plt.text(1.3, durations.median(), stats_text, 
                va='center', ha='left', bbox=dict(facecolor='white', alpha=0.8))
    
    # Adjust layout
    plt.tight_layout()
    
    # Save the figure to the specified output path
    plt.savefig(output_path, dpi=300)
    plt.close()
    
    logger.info(f"Saved box plot to {output_path}")

def process_input(input_path: Path, output_path: Path, total_frames: int) -> Dict[str, Any]:
    """
    Process input file(s) and generate outputs.
    
    This function handles both single files and directories:
    - If input_path is a file, it processes that file only
    - If input_path is a directory, it processes all CSV files in that directory
    
    Args:
        input_path: Path to the input file or directory
        output_path: Path to the directory where outputs will be saved
        total_frames: Total number of frames to consider
        
    Returns:
        Dictionary containing summary statistics
    """
    # Create output directory - assumes it doesn't exist (checked by validate_args)
    output_path.mkdir(parents=True, exist_ok=False)
    
    # Initialize tracking variables
    error_logs = []
    file_summaries = []
    total_files = 0
    successful_files = 0
    all_event_durations = []  # Collect all event durations for overall stats
    
    # Determine files to process
    if input_path.is_file():
        files_to_process = [input_path]
    else:
        files_to_process = list(input_path.glob('*.csv'))
    
    # Process each file
    for csv_file in files_to_process:
        total_files += 1
        logger.info(f"Processing file: {csv_file.name}")
        
        # Initialize error log for this file
        error_log = {}
        
        # Process and validate the CSV file
        frames_df = process_csv(csv_file, error_log)
        
        if frames_df is None:
            # If processing failed, add the error log and continue to next file
            error_logs.append(error_log)
            logger.error(f"Failed to process {csv_file.name}: {error_log['details']}")
            continue
        
        try:
            # Extract filename without extension
            filename = csv_file.stem
            
            # Generate timeline
            timeline_df = generate_timeline(frames_df['Frame'], total_frames)
            
            # Generate event list
            event_list_df = generate_event_list(frames_df['Frame'])
            
            # Save timeline to CSV
            timeline_file = output_path / f"{filename}_timeline.csv"
            timeline_df.to_csv(timeline_file, index=False)
            logger.info(f"Saved timeline to {timeline_file}")
            
            # Save event list to CSV
            events_file = output_path / f"{filename}_events.csv"
            event_list_df.to_csv(events_file, index=False)
            logger.info(f"Saved event list to {events_file}")
            
            # Generate and save timeline plot
            timeline_plot_file = output_path / f"{filename}_timeline.png"
            generate_timeline_plot(timeline_df, timeline_plot_file)
            
            # Generate and save box plot
            box_plot_file = output_path / f"{filename}_boxplot.png"
            generate_box_plot(event_list_df, box_plot_file)
            
            # Calculate summary statistics for this file
            file_summary, event_durations = calculate_file_summary(
                filename, timeline_df, event_list_df, total_frames
            )
            file_summaries.append(file_summary)
            all_event_durations.extend(event_durations)
            
            successful_files += 1
            logger.info(f"Successfully processed {csv_file.name}")
            
        except Exception as e:
            # Log any errors that occur during processing
            error_log = {
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'filename': csv_file.name,
                'error_type': 'Processing Error',
                'details': str(e),
                'frame': None
            }
            error_logs.append(error_log)
            logger.error(f"Error processing {csv_file.name}: {str(e)}")
    
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