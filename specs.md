# Project Specification: Behavioral Annotation Data Conversion

## 1. Overview

The goal is to convert behavioral annotation data from Drosophila fly videos (annotated via ImageJ) into a more structured and analysis-friendly format. The input is a CSV file produced by ImageJ (when annotating grooming behaviors) where only the **Frame** column is relevant. The file lists alternating start and stop frame numbers for grooming events. The output consists of two main components along with visualizations and summary statistics.

---

## 2. Input & Assumptions

- **Input File:** CSV file from ImageJ containing columns: Number, Area, Mean, Min, Max, X, Y, Ch, Frame.
- **Relevant Data:** Only the **Frame** column is used.
- **Assumption:** The rows in the CSV represent alternating events: the first frame is the start of an event, the second is the stop, the third is the start of the next event, etc.
- **Frame Order:** Frame numbers must always be increasing. A frame number lower than the previous indicates an error.

---

## 3. Outputs

### 3.1 Timeline Table
- **Format:** CSV or Pandas DataFrame.
- **Rows:** Frame numbers 1 to *N* (default N = 8999; this should be parameterizable via an optional CLI parameter).
- **Columns:**
  - **Frame:** Integer sequence.
  - **GroomingFlag:** Binary indicator (0 = no grooming, 1 = grooming).
  - **EventID:** 0 if no grooming; for grooming frames, a unique positive integer assigned per event.

### 3.2 Event List
- **Format:** CSV file.
- **Columns:**
  - **EventID:** Identifier matching that in the Timeline Table.
  - **StartFrame:** Frame where the event begins.
  - **StopFrame:** Frame where the event ends.

### 3.3 Visualizations
- **Timeline Plot:** A static image (e.g., PNG) showing a continuous color-coded timeline marking grooming regions over frames 1 to *N* (without explicit markers at boundaries).
- **Box Plot:** A static image (PNG) representing the distribution of grooming event durations (calculated as StopFrame – StartFrame + 1).

### 3.4 Consolidated Summary Report
- **Content:** 
  - Per-file metrics: file name, number of grooming events, total grooming duration (in frames), average event duration, median event duration, standard deviation, and percentage of grooming frames relative to total.
  - Overall aggregated metrics across all processed files.
  - Aggregated counts: total number of files processed, number of successfully processed files, and number of faulty files (with error details).

---

## 4. Processing Logic

### 4.1 Data Extraction & Validation
- **Step 1:** Read the input CSV file using Pandas.
- **Step 2:** Extract the **Frame** column and convert values to integers.
- **Step 3:** Validate that:
  - The **Frame** column exists.
  - All frame entries are numeric.
  - The total number of frame entries is even; if odd, halt processing for that file with an error.
  - Frames are in strictly increasing order; if a frame is lower than the previous one, log an error.

### 4.2 Event Pairing & Timeline Creation
- **Pairing:** Interpret the rows as alternating start and stop values.
  - Verify that for each pair, the start frame is less than or equal to the stop frame.
  - Ensure all frame numbers lie within the valid range (1 to N).
- **Timeline Table Generation:**
  - Create a DataFrame with rows for frames 1 to N.
  - Initially set `GroomingFlag` and `EventID` to 0.
  - For each paired event, update rows from the start to stop frame (inclusive):
    - Set `GroomingFlag` = 1.
    - Assign a unique positive `EventID` to these rows.
  - Even if events are consecutive (i.e., one event ends and the next begins immediately), they must be assigned separate `EventID`s.

### 4.3 Event List Generation
- For each valid event pair, record:
  - **EventID**
  - **StartFrame**
  - **StopFrame**

### 4.4 Error Handling in Batch Processing
- **Batch Mode:** The script should process all CSV files in a specified directory.
- **Error Cases:** 
  - If a CSV file is missing the **Frame** column, contains an odd number of entries, or has non-increasing frame numbers, the script must log the error.
  - Instead of halting the entire batch, the faulty file is skipped.
- **Error Log:** For each faulty file, create an entry in an error log CSV (`errorLog.csv`) with the file name, error type, timestamp, and problematic frame (if applicable).

---

## 5. Architecture & Implementation

### 5.1 Environment & Dependencies
- **Language:** Python 3.
- **Environment:** Conda (project-specific environment).
- **Libraries:** 
  - Pandas and NumPy for data processing.
  - Matplotlib (or similar) for generating static visualizations.
  - argparse for command-line interface.
  - PyTest for unit tests.

### 5.2 CLI Interface
- **Parameters:**
  - Input file or directory.
  - Output directory.
  - Optional total frame count (default: 8999).
  - Optional logging level (if desired, but basic status messages are sufficient).

### 5.3 File & Folder Organization
- **Output Folder:** A new folder must be created inside the input folder. If the output folder already exists, the script should exit with an error message on the console.
- **Naming Convention:**
  - Each file’s outputs should be prefixed by the input file name:
    - Timeline Table: `<filename>_timeline.csv`
    - Event List: `<filename>_events.csv`
    - Timeline Plot: `<filename>_timeline.png`
    - Box Plot: `<filename>_boxplot.png`
  - A consolidated summary report (CSV) aggregating per-file and overall metrics.
  - Error log file: `errorLog.csv`.

### 5.4 Code Structure
- **Single Standalone Script:** The entire functionality will reside in one well-structured Python script.
- **Modules/Functions:** Organize the code into functions for:
  - Input processing and validation.
  - Event pairing and timeline generation.
  - Output file generation (CSV and images).
  - Error logging.
  - Summary report aggregation.
  - CLI argument parsing.
- **Documentation:** Include comprehensive inline documentation (docstrings) and a README file with installation and usage instructions.
- **Unit Testing:** Use PyTest to cover:
  - Input CSV parsing and validation.
  - Correct event pairing.
  - Timeline and event list generation.
  - Error handling scenarios (e.g., odd number of entries, non-increasing frames).

### 5.5 Status Messages
- The script should print a basic status message to the console for each file processed (e.g., "Processing file X...", "File Y processed successfully.", "Error in file Z: [error description].").

---

## 6. Testing & Continuous Integration

### 6.1 Unit Tests
- **Input Parsing:** Test with valid and invalid CSV files (missing column, odd number of frame entries).
- **Event Pairing:** Ensure correct pairing and error detection (start > stop, non-increasing frames).
- **Timeline & Event List:** Verify that the timeline table and event list correctly reflect the input data.
  
### 6.2 Integration Tests
- **Batch Processing:** Run the script on a directory with multiple CSV files (including faulty ones) and verify that:
  - All valid files produce the expected outputs.
  - Faulty files are skipped, with errors logged in `errorLog.csv`.
- **Output Validation:** Ensure that the consolidated summary report correctly aggregates per-file and overall statistics.

---

## 7. Final CLI Behavior

- **Execution:** The user invokes the script with required parameters (input folder, output folder, optional total frame count).
- **Output Folder:** If the output folder does not exist, it is created; if it exists, the script exits with a console error.
- **File Processing:** Each CSV in the input folder is processed independently. Valid files generate their Timeline Table, Event List, timeline plot, and box plot using the naming convention. Any errors are recorded in `errorLog.csv`.
- **Consolidated Report:** At the end, a summary CSV is generated, aggregating per-file metrics (number of events, grooming duration, etc.) and overall statistics (total files processed, success count, error count).

---

This specification provides a clear, modular, and robust design that meets all the requirements and ensures that the final product is both human- and machine-readable, with additional analytical outputs suitable for further processing (e.g., neural network inputs).