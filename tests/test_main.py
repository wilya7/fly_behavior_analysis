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