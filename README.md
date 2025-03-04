# Behavioral Annotation Data Conversion

A Python tool for converting behavioral annotation data from Drosophila fly videos (annotated via ImageJ) into a structured and analysis-friendly format.

## Features
- Converts ImageJ CSV files to structured timeline and event data
- Generates visualizations of grooming events
- Produces summary statistics
- Provides batch processing capabilities

## Installation
### Prerequisites
- Python 3.x
- Conda (for environment management)

### Setup
1. Clone this repository
2. Create the conda environment:
 conda env create -f environment.yml 
3. Activate the environment:
 conda activate fly_analysis 
4. Install required packages:
conda install pandas numpy matplotlib pytest

## Usage
Run the script with the following command:

python main.py --input <input_path> --output <output_path> [--total_frames <n>]
### Arguments
- `--input`: Path to input CSV file or directory containing CSV files (required)
- `--output`: Path to output directory for storing results (required)
- `--total_frames`: Total number of frames to consider (default: 8999)

### Example

python main.py --input data/annotations/ --output results/fly_analysis --total_frames 10000

## Output Structure
For each processed file, the following outputs are generated:
- Timeline Table: `<filename>_timeline.csv`
- Event List: `<filename>_events.csv`
- Timeline Plot: `<filename>_timeline.png`
- Box Plot: `<filename>_boxplot.png`

Additionally, the tool generates:
- Consolidated summary report
- Error log (if applicable)

## Testing
Run tests using pytest: