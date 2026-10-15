"""
merge_logs.py
=============
Step 1 of the pipeline. The simulator writes one CSV event log per simulated
day inside each replicate folder. This script merges the CSV files of every
numbered sub-folder (1, 2, ..., 30) of a directory into a single XES log,
``merged_log.xes``, renumbering the case identifiers so that they are unique.

Usage (run it once per variant that is delivered as per-day CSV files, i.e. the
Planner-only and the Planner + intervention logs):

    python merge_logs.py data/logOro
    python merge_logs.py data/logDinamico

Requirements: pandas, pm4py.
"""

import os
import pandas as pd
import pm4py
from pathlib import Path

def merge_logs_in_folder(folder_path):
    """
    Merge all the CSV files of a folder into a single log.
    The case ids are renumbered so that they are unique.

    Args:
        folder_path: Path of the folder that contains the CSV logs

    Returns:
        DataFrame with the merged log
    """
    # List the CSV files of the folder
    csv_files = sorted([f for f in os.listdir(folder_path) if f.endswith('.csv')])

    if not csv_files:
        print(f"No CSV files found in {folder_path}")
        return None

    print(f"  Found {len(csv_files)} CSV files")

    all_events = []
    case_id_offset = 0

    for csv_file in csv_files:
        file_path = os.path.join(folder_path, csv_file)
        print(f"    Processing {csv_file}...")

        # Read the CSV
        df = pd.read_csv(file_path)

        # Renumber the case ids so that they are unique
        # Add the offset to all case ids
        df['case_id'] = df['case_id'] + case_id_offset

        # New offset for the next file
        # (current maximum case id + 1)
        max_case_id = df['case_id'].max()
        case_id_offset = max_case_id + 1

        # Append the events to the list
        all_events.append(df)

    # Concatenate all the DataFrames
    merged_df = pd.concat(all_events, ignore_index=True)

    # Sort by case id and timestamp
    merged_df = merged_df.sort_values(['case_id', 'time:timestamp:start'])
    merged_df = merged_df.reset_index(drop=True)

    print(f"  Merged log: {len(merged_df)} events, {merged_df['case_id'].nunique()} unique cases")

    return merged_df


def convert_to_event_log(df):
    """
    Convert a DataFrame into a format compatible with a pm4py event log.

    Args:
        df: DataFrame with columns case_id, activity, time:timestamp:start, time:timestamp:end

    Returns:
        pm4py event log
    """
    # Rename the columns to the standard pm4py names
    df_copy = df.copy()

    # Make sure that the timestamps are datetimes
    # Use format='mixed' to handle timestamps with and without microseconds
    df_copy['time:timestamp:start'] = pd.to_datetime(df_copy['time:timestamp:start'], format='mixed')
    df_copy['time:timestamp:end'] = pd.to_datetime(df_copy['time:timestamp:end'], format='mixed')

    # Rename the columns to the standard XES names
    df_copy = df_copy.rename(columns={
        'case_id': 'case:concept:name',
        'activity': 'concept:name',
        'time:timestamp:start': 'start_timestamp',
        'time:timestamp:end': 'time:timestamp'
    })

    # Convert case_id to string
    df_copy['case:concept:name'] = df_copy['case:concept:name'].astype(str)

    return df_copy


def process_all_subfolders(base_path):
    """
    Process every numbered subfolder of the base directory.

    Args:
        base_path: Path of the directory that contains the numbered sub-folders
    """
    base_path = Path(base_path)

    # List the numbered sub-folders
    subfolders = sorted([f for f in os.listdir(base_path) if f.isdigit()], key=int)

    print(f"Found {len(subfolders)} sub-folders to process\n")

    for subfolder in subfolders:
        subfolder_path = base_path / subfolder

        if not subfolder_path.is_dir():
            continue

        print(f"Processing folder {subfolder}...")

        # Merge the logs of this folder
        merged_df = merge_logs_in_folder(subfolder_path)

        if merged_df is None:
            continue

        # Convert to event-log format
        event_log_df = convert_to_event_log(merged_df)

        # Save as XES
        output_xes = subfolder_path / "merged_log.xes"

        # Convert to a pm4py event log
        event_log = pm4py.format_dataframe(
            event_log_df,
            case_id='case:concept:name',
            activity_key='concept:name',
            timestamp_key='time:timestamp'
        )

        # Export to XES
        pm4py.write_xes(event_log, str(output_xes))

        print(f"  ✓ Saved to {output_xes}\n")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        sys.exit("usage: python merge_logs.py <directory with the numbered replicate folders>")
    print("=== Merging logs ===\n")
    process_all_subfolders(Path(sys.argv[1]))
    print("=== Done ===")
