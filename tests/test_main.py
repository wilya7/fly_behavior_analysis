#!/usr/bin/env python3
"""
Test cases for the Behavioral Annotation Data Conversion Tool.
"""
import pytest
import pandas as pd
import numpy as np
import tempfile
import os
import sys
import io
import contextlib
from pathlib import Path
from datetime import datetime

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the module to test
from main import (process_csv, DataValidationError, generate_timeline, generate_event_list,
                 calculate_file_summary, process_input, generate_timeline_plot, generate_box_plot)

@pytest.fixture
def valid_csv():
    """Create a temporary CSV file with valid frame data."""
    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp:
        # Create valid CSV with even number of entries in increasing order
        df = pd.DataFrame({
            'Number': [1, 2, 3, 4],
            'Area': [100, 100, 100, 100],
            'Mean': [0.5, 0.5, 0.5, 0.5],
            'Min': [0, 0, 0, 0],
            'Max': [1, 1, 1, 1],
            'X': [10, 10, 10, 10],
            'Y': [20, 20, 20, 20],
            'Ch': [1, 1, 1, 1],
            'Frame': [100, 150, 200, 250]  # Strictly increasing frame numbers
        })
        df.to_csv(temp.name, index=False)
        yield temp.name
        # Clean up
        os.unlink(temp.name)

@pytest.fixture
def no_frame_column_csv():
    """Create a temporary CSV file missing the 'Frame' column."""
    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp:
        df = pd.DataFrame({
            'Number': [1, 2, 3, 4],
            'Area': [100, 100, 100, 100],
            # Missing 'Frame' column
        })
        df.to_csv(temp.name, index=False)
        yield temp.name
        os.unlink(temp.name)

@pytest.fixture
def non_numeric_frame_csv():
    """Create a temporary CSV file with non-numeric values in the 'Frame' column."""
    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp:
        df = pd.DataFrame({
            'Number': [1, 2, 3, 4],
            'Frame': [100, 'abc', 200, 250]  # Non-numeric value
        })
        df.to_csv(temp.name, index=False)
        yield temp.name
        os.unlink(temp.name)

@pytest.fixture
def odd_entries_csv():
    """Create a temporary CSV file with an odd number of frame entries."""
    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp:
        df = pd.DataFrame({
            'Number': [1, 2, 3],
            'Frame': [100, 150, 200]  # Odd number of entries
        })
        df.to_csv(temp.name, index=False)
        yield temp.name
        os.unlink(temp.name)

@pytest.fixture
def non_increasing_frames_csv():
    """Create a temporary CSV file with non-increasing frame numbers."""
    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp:
        df = pd.DataFrame({
            'Number': [1, 2, 3, 4],
            'Frame': [100, 150, 140, 250]  # Third value (140) is less than second (150)
        })
        df.to_csv(temp.name, index=False)
        yield temp.name
        os.unlink(temp.name)

@pytest.fixture
def sample_frames():
    """Create sample frame data for timeline generation tests."""
    return pd.Series([100, 200, 300, 400])  # Two events: (100-200) and (300-400)

@pytest.fixture
def invalid_frame_pair():
    """Create sample frame data with an invalid pair (start > stop)."""
    return pd.Series([200, 100, 300, 400])  # First pair is invalid: 200 > 100

@pytest.fixture
def out_of_range_frames():
    """Create sample frame data with frames outside the valid range."""
    return pd.Series([0, 50, 480, 600])  # One event starts before 1, one ends after total_frames=500

def test_valid_csv(valid_csv):
    """Test processing of a valid CSV file."""
    result = process_csv(valid_csv)
    assert result is not None
    assert 'Frame' in result.columns
    assert len(result) == 4
    assert list(result['Frame']) == [100, 150, 200, 250]

def test_missing_frame_column(no_frame_column_csv):
    """Test validation of a CSV file missing the 'Frame' column."""
    error_log = {}
    result = process_csv(no_frame_column_csv, error_log)
    assert result is None
    assert error_log['error_type'] == 'Missing Column'
    # Test without error_log (should raise exception)
    with pytest.raises(DataValidationError):
        process_csv(no_frame_column_csv)

def test_non_numeric_frame(non_numeric_frame_csv):
    """Test validation of a CSV file with non-numeric values in the 'Frame' column."""
    error_log = {}
    result = process_csv(non_numeric_frame_csv, error_log)
    assert result is None
    assert error_log['error_type'] == 'Non-numeric Values'
    # Test without error_log (should raise exception)
    with pytest.raises(DataValidationError):
        process_csv(non_numeric_frame_csv)

def test_odd_entries(odd_entries_csv):
    """Test validation of a CSV file with an odd number of frame entries."""
    error_log = {}
    result = process_csv(odd_entries_csv, error_log)
    assert result is None
    assert error_log['error_type'] == 'Odd Entry Count'
    # Test without error_log (should raise exception)
    with pytest.raises(DataValidationError):
        process_csv(odd_entries_csv)

def test_non_increasing_frames(non_increasing_frames_csv):
    """Test validation of a CSV file with non-increasing frame numbers."""
    error_log = {}
    result = process_csv(non_increasing_frames_csv, error_log)
    assert result is None
    assert error_log['error_type'] == 'Non-increasing Frames'
    assert error_log['frame'] == 140  # The problematic frame
    # Test without error_log (should raise exception)
    with pytest.raises(DataValidationError):
        process_csv(non_increasing_frames_csv)

def test_generate_timeline_basic(sample_frames):
    """Test basic functionality of generate_timeline with valid input."""
    total_frames = 500
    timeline = generate_timeline(sample_frames, total_frames)
    
    # Verify timeline has correct shape and columns
    assert len(timeline) == total_frames
    assert all(col in timeline.columns for col in ['Frame', 'GroomingFlag', 'EventID'])
    
    # Verify frames 1-99 have no grooming
    assert all(timeline.loc[0:98, 'GroomingFlag'] == 0)
    assert all(timeline.loc[0:98, 'EventID'] == 0)
    
    # Verify frames 100-200 have grooming with EventID 1
    assert all(timeline.loc[99:199, 'GroomingFlag'] == 1)
    assert all(timeline.loc[99:199, 'EventID'] == 1)
    
    # Verify frames 201-299 have no grooming
    assert all(timeline.loc[200:298, 'GroomingFlag'] == 0)
    assert all(timeline.loc[200:298, 'EventID'] == 0)
    
    # Verify frames 300-400 have grooming with EventID 2
    assert all(timeline.loc[299:399, 'GroomingFlag'] == 1)
    assert all(timeline.loc[299:399, 'EventID'] == 2)
    
    # Verify frames 401-500 have no grooming
    assert all(timeline.loc[400:499, 'GroomingFlag'] == 0)
    assert all(timeline.loc[400:499, 'EventID'] == 0)

def test_generate_timeline_invalid_pair(invalid_frame_pair):
    """Test generate_timeline with invalid frame pair (start > stop)."""
    total_frames = 500
    
    # Should raise ValueError for invalid pair
    with pytest.raises(ValueError) as excinfo:
        generate_timeline(invalid_frame_pair, total_frames)
    
    # Check that the error message mentions the invalid pair
    assert "start (200) > stop (100)" in str(excinfo.value)

def test_generate_timeline_out_of_range(out_of_range_frames):
    """Test generate_timeline with frames outside the valid range."""
    total_frames = 500
    
    # The function should adjust the ranges to be within bounds
    # but we need to capture warnings to verify they're logged properly
    timeline = generate_timeline(out_of_range_frames, total_frames)
    
    # First event should be adjusted to start at frame 1 instead of 0
    assert timeline.loc[0, 'GroomingFlag'] == 1
    assert timeline.loc[0, 'EventID'] == 1
    
    # Second event should be truncated to end at frame 500 instead of 600
    assert timeline.loc[479, 'GroomingFlag'] == 1  # Frame 480
    assert timeline.loc[479, 'EventID'] == 2
    assert timeline.loc[499, 'GroomingFlag'] == 1  # Frame 500
    assert timeline.loc[499, 'EventID'] == 2

def test_timeline_from_csv_file(valid_csv):
    """Test end-to-end processing from CSV file to timeline generation."""
    total_frames = 500
    
    # Process the CSV file
    frames_df = process_csv(valid_csv)
    assert frames_df is not None
    
    # Generate timeline from the processed frames
    timeline = generate_timeline(frames_df['Frame'], total_frames)
    
    # Verify the timeline has expected structure
    assert len(timeline) == total_frames
    assert all(col in timeline.columns for col in ['Frame', 'GroomingFlag', 'EventID'])
    
    # Verify events are correctly marked in the timeline
    # First event: frames 100-150
    assert all(timeline.loc[99:149, 'GroomingFlag'] == 1)
    assert all(timeline.loc[99:149, 'EventID'] == 1)
    
    # Second event: frames 200-250
    assert all(timeline.loc[199:249, 'GroomingFlag'] == 1)
    assert all(timeline.loc[199:249, 'EventID'] == 2)

def test_generate_event_list_basic(sample_frames):
    """Test basic functionality of generate_event_list with valid input."""
    # Sample frames is [100, 200, 300, 400] representing two events
    event_list = generate_event_list(sample_frames)
    
    # Verify event list has correct shape and columns
    assert len(event_list) == 2  # Should have 2 events
    assert all(col in event_list.columns for col in ['EventID', 'StartFrame', 'StopFrame'])
    
    # Verify first event
    assert event_list.loc[0, 'EventID'] == 1
    assert event_list.loc[0, 'StartFrame'] == 100
    assert event_list.loc[0, 'StopFrame'] == 200
    
    # Verify second event
    assert event_list.loc[1, 'EventID'] == 2
    assert event_list.loc[1, 'StartFrame'] == 300
    assert event_list.loc[1, 'StopFrame'] == 400

def test_generate_event_list_invalid_pair(invalid_frame_pair):
    """Test generate_event_list with invalid frame pair (start > stop)."""
    # Should raise ValueError for invalid pair
    with pytest.raises(ValueError) as excinfo:
        generate_event_list(invalid_frame_pair)
    
    # Check that the error message mentions the invalid pair
    assert "start (200) > stop (100)" in str(excinfo.value)

def test_generate_event_list_odd_entries():
    """Test generate_event_list with odd number of entries."""
    odd_frames = pd.Series([100, 200, 300])  # Odd number of entries
    
    # Should raise ValueError for odd number of entries
    with pytest.raises(ValueError) as excinfo:
        generate_event_list(odd_frames)
    
    # Check that the error message mentions even number of entries
    assert "even number" in str(excinfo.value).lower()

def test_event_list_from_csv_file(valid_csv):
    """Test end-to-end processing from CSV file to event list generation."""
    # Process the CSV file
    frames_df = process_csv(valid_csv)
    assert frames_df is not None
    
    # Generate event list from the processed frames
    event_list = generate_event_list(frames_df['Frame'])
    
    # Verify the event list has expected structure
    assert len(event_list) == 2  # Should have 2 events
    assert all(col in event_list.columns for col in ['EventID', 'StartFrame', 'StopFrame'])
    
    # Verify first event
    assert event_list.loc[0, 'EventID'] == 1
    assert event_list.loc[0, 'StartFrame'] == 100
    assert event_list.loc[0, 'StopFrame'] == 150
    
    # Verify second event
    assert event_list.loc[1, 'EventID'] == 2
    assert event_list.loc[1, 'StartFrame'] == 200
    assert event_list.loc[1, 'StopFrame'] == 250

# Helper function for batch processing tests
def create_test_file(path, df):
    """Helper function to create test CSV files."""
    df.to_csv(path, index=False)

def test_calculate_file_summary():
    """Test the calculation of file summary statistics."""
    # Create sample data
    timeline_df = pd.DataFrame({
        'Frame': range(1, 101),
        'GroomingFlag': [1] * 30 + [0] * 40 + [1] * 20 + [0] * 10,
        'EventID': [1] * 30 + [0] * 40 + [2] * 20 + [0] * 10
    })
    
    event_list_df = pd.DataFrame({
        'EventID': [1, 2],
        'StartFrame': [1, 71],
        'StopFrame': [30, 90]
    })
    
    total_frames = 100
    filename = "test_file"
    
    # Calculate summary
    summary, event_durations = calculate_file_summary(filename, timeline_df, event_list_df, total_frames)
    
    # Verify summary results
    assert summary['filename'] == filename
    assert summary['num_events'] == 2
    assert summary['total_grooming_frames'] == 50  # 30 + 20
    assert summary['grooming_percentage'] == 50.0  # 50/100 * 100
    
    # Verify event durations
    assert event_durations == [30, 20]  # (30-1+1), (90-71+1)

def test_process_input(tmp_path):
    """Test batch processing of multiple files."""
    # Create test directories
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    output_dir = tmp_path / "output"
    
    # Create valid test files
    valid_file1 = input_dir / "valid1.csv"
    create_test_file(valid_file1, pd.DataFrame({
        'Frame': [100, 150, 200, 250]
    }))
    
    valid_file2 = input_dir / "valid2.csv"
    create_test_file(valid_file2, pd.DataFrame({
        'Frame': [50, 75, 300, 400]
    }))
    
    # Create invalid test files
    invalid_file1 = input_dir / "invalid1.csv"
    create_test_file(invalid_file1, pd.DataFrame({
        'Frame': [100, 150, 200]  # Odd number of entries
    }))
    
    invalid_file2 = input_dir / "invalid2.csv"
    create_test_file(invalid_file2, pd.DataFrame({
        'NotFrame': [100, 150, 200, 250]  # Missing Frame column
    }))
    
    # Process the directory
    summary = process_input(input_dir, output_dir, 500)
    
    # Verify summary statistics
    assert summary['total_files'] == 4
    assert summary['successful_files'] == 2
    assert summary['faulty_files'] == 2
    
    # Verify output files exist for valid inputs
    assert (output_dir / "valid1_timeline.csv").exists()
    assert (output_dir / "valid1_events.csv").exists()
    assert (output_dir / "valid2_timeline.csv").exists()
    assert (output_dir / "valid2_events.csv").exists()
    
    # Verify visualization files exist
    assert (output_dir / "valid1_timeline.png").exists()
    assert (output_dir / "valid1_boxplot.png").exists()
    assert (output_dir / "valid2_timeline.png").exists()
    assert (output_dir / "valid2_boxplot.png").exists()
    
    # Verify summary report and error log
    assert (output_dir / "summary_report.csv").exists()
    assert (output_dir / "errorLog.csv").exists()
    
    # Check error log content
    error_log = pd.read_csv(output_dir / "errorLog.csv")
    assert len(error_log) == 2
    
    # Check that both invalid files are in the error log
    invalid_files_in_log = set(error_log['filename'])
    assert "invalid1.csv" in invalid_files_in_log
    assert "invalid2.csv" in invalid_files_in_log

def test_process_single_file(tmp_path):
    """Test processing of a single file."""
    # Create test directories
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    output_dir = tmp_path / "output"
    
    # Create a valid test file
    valid_file = input_dir / "valid.csv"
    create_test_file(valid_file, pd.DataFrame({
        'Frame': [100, 150, 200, 250]
    }))
    
    # Process the single file
    summary = process_input(valid_file, output_dir, 500)
    
    # Verify summary statistics
    assert summary['total_files'] == 1
    assert summary['successful_files'] == 1
    assert summary['faulty_files'] == 0
    
    # Verify output files exist
    assert (output_dir / "valid_timeline.csv").exists()
    assert (output_dir / "valid_events.csv").exists()
    assert (output_dir / "valid_timeline.png").exists()
    assert (output_dir / "valid_boxplot.png").exists()
    assert (output_dir / "summary_report.csv").exists()
    
    # Verify no error log was created (since there were no errors)
    assert not (output_dir / "errorLog.csv").exists()

def test_generate_timeline_plot(tmp_path):
    """Test timeline plot generation."""
    # Create sample timeline data
    timeline_df = pd.DataFrame({
        'Frame': range(1, 101),
        'GroomingFlag': [0] * 20 + [1] * 30 + [0] * 20 + [1] * 20 + [0] * 10,
        'EventID': [0] * 20 + [1] * 30 + [0] * 20 + [2] * 20 + [0] * 10
    })
    
    # Define output path
    output_path = tmp_path / "timeline_test.png"
    
    # Generate the plot
    generate_timeline_plot(timeline_df, output_path)
    
    # Verify the plot file was created
    assert output_path.exists()
    assert output_path.stat().st_size > 0  # File should not be empty

def test_generate_timeline_plot_empty_input():
    """Test timeline plot generation with empty input."""
    # Create empty DataFrame
    empty_df = pd.DataFrame(columns=['Frame', 'GroomingFlag', 'EventID'])
    
    # Test with empty DataFrame
    with pytest.raises(ValueError) as excinfo:
        generate_timeline_plot(empty_df, Path("dummy.png"))
    
    # Check error message
    assert "empty" in str(excinfo.value).lower()

def test_generate_box_plot(tmp_path):
    """Test box plot generation."""
    # Create sample event list data
    event_list_df = pd.DataFrame({
        'EventID': [1, 2, 3, 4, 5],
        'StartFrame': [10, 50, 100, 200, 300],
        'StopFrame': [40, 70, 150, 220, 350]
    })
    
    # Define output path
    output_path = tmp_path / "boxplot_test.png"
    
    # Generate the plot
    generate_box_plot(event_list_df, output_path)
    
    # Verify the plot file was created
    assert output_path.exists()
    assert output_path.stat().st_size > 0  # File should not be empty

def test_generate_box_plot_empty_input():
    """Test box plot generation with empty input."""
    # Create empty DataFrame
    empty_df = pd.DataFrame(columns=['EventID', 'StartFrame', 'StopFrame'])
    
    # Test with empty DataFrame
    with pytest.raises(ValueError) as excinfo:
        generate_box_plot(empty_df, Path("dummy.png"))
    
    # Check error message
    assert "empty" in str(excinfo.value).lower()

def test_visualization_integration(valid_csv, tmp_path):
    """Test integration of visualization functions with processing pipeline."""
    # Process the CSV file
    frames_df = process_csv(valid_csv)
    assert frames_df is not None
    
    # Generate timeline and event list
    total_frames = 500
    timeline_df = generate_timeline(frames_df['Frame'], total_frames)
    event_list_df = generate_event_list(frames_df['Frame'])
    
    # Generate visualizations
    timeline_plot_path = tmp_path / "timeline_plot.png"
    box_plot_path = tmp_path / "box_plot.png"
    
    generate_timeline_plot(timeline_df, timeline_plot_path)
    generate_box_plot(event_list_df, box_plot_path)
    
    # Verify output files
    assert timeline_plot_path.exists()
    assert box_plot_path.exists()