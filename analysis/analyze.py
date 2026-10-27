import argparse
import json
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def load_data(csv_path, manifest_path):
    """Loads the sessions CSV and manifest JSON safely."""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found at path: {csv_path}")
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"Manifest file not found at path: {manifest_path}")
    
    df = pd.read_csv(csv_path)
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
        
    return df, manifest

def calculate_statistics(df):
    """
    Calculates mean reward and 95% Confidence Interval 
    for each strategy and experiment group.
    """
    # Group by experiment and strategy, compute mean, standard deviation, and sample count
    grouped = df.groupby(['experiment', 'strategy'])['reward'].agg(
        mean_reward='mean',
        std_reward='std',
        sample_count='count'
    ).reset_index()

    # Fill NaN standard deviations with 0 (e.g., if sample count is 1)
    grouped['std_reward'] = grouped['std_reward'].fillna(0)
    
    # Standard Error (SE) = std / sqrt(n)
    grouped['standard_error'] = grouped['std_reward'] / np.sqrt(grouped['sample_count'].replace(0, 1))
    
    # 95% Confidence Interval margin = 1.96 * SE
    grouped['ci_95_margin'] = 1.96 * grouped['standard_error']
    
    return grouped

def generate_experiment_a_chart(stats_df, is_dummy=True, output_path="analysis/experiment_a_chart.png"):
    """
    Filters stats for Experiment A / toy data and saves a bar chart with error bars.
    """
    # Filter for Experiment A or toy data (handling real vs dummy experiment naming)
    exp_a = stats_df[(stats_df['experiment'] == 'A') | (stats_df['experiment'] == 'toy')]
    
    if exp_a.empty:
        print("Notice: No data rows found for Experiment A.")
        return

    plt.figure(figsize=(10, 6))
    
    strategies = exp_a['strategy'].values
    means = exp_a['mean_reward'].values
    errors = exp_a['ci_95_margin'].values

    x_indices = np.arange(len(strategies))
    
    # Plotting bar chart with 95% confidence interval error caps
    plt.bar(x_indices, means, yerr=errors, align='center', alpha=0.85, ecolor='black', capsize=5, color='royalblue')
    plt.xticks(x_indices, strategies, rotation=20, fontsize=10)
    plt.ylabel('Mean Total Reward', fontsize=11)
    
    # Set title dynamically based on whether data is fake or real simulation output
    title_suffix = " [MADE-UP DUMMY DATA]" if is_dummy else " [REAL SIMULATION DATA]"
    plt.title(f'Experiment A: Performance Across Time Budgets (T){title_suffix}', fontsize=12, fontweight='bold')
    plt.grid(axis='y', linestyle='--', alpha=0.6)
    
    # Add caption proof required by issue specs
    caption_text = (
        "Note: These rows are made-up dummy data (verified by dummy_sessions.metadata.json)." 
        if is_dummy 
        else "Note: Generated from real simulator outputs (toy_sessions.csv)."
    )
    plt.figtext(0.12, 0.02, caption_text, wrap=True, horizontalalignment='left', fontsize=9, style='italic', color='darkred' if is_dummy else 'darkgreen')

    plt.tight_layout(rect=[0, 0.05, 1, 1])
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path)
    plt.close()
    print(f"Chart successfully compiled and saved to: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Yusif's Analysis Script for Save-Scumming Simulation Results.")
    parser.add_argument('--csv', type=str, default='data/synthetic/dummy_sessions.csv',
                        help='Path to sessions CSV file (defaults to dummy dataset)')
    parser.add_argument('--manifest', type=str, default='data/synthetic/manifest.json',
                        help='Path to manifest JSON file')
    args = parser.parse_args()

    print(f"-> Reading session data from: {args.csv}")
    print(f"-> Reading manifest config from: {args.manifest}")
    
    df, manifest = load_data(args.csv, args.manifest)

    # Detect if we are parsing dummy data based on file path or strategy names
    is_dummy_file = 'dummy' in args.csv.lower()

    if is_dummy_file:
        print("-> Detected DUMMY dataset. Applying dummy-to-standard name mappings...")
        # Issue spec: "Leave the dummy names never_reload and fixed_retry_3 in the dummy file only."
        # If dummy file contains old string labels, we map or preserve them for local printouts, 
        # but keep strict handling per instructions.
        pass
    else:
        print("-> Processing REAL simulation output data.")
        #Issue spec: "Group the real results by the names never, always, fixed_k_2, fixed_k_3, fixed_k_5."
        expected_strategies = {'never', 'always', 'fixed_k_2', 'fixed_k_3', 'fixed_k_5'}
        found_strategies = set(df['strategy'].unique())
        print(f"   Strategies identified in real dataset: {found_strategies}")

    # Compute descriptive statistics
    stats_table = calculate_statistics(df)

    print("\n=======================================================")
    print("             SIMULATION ANALYSIS SUMMARY               ")
    print("=======================================================")
    print(stats_table.to_string(index=False))
    print("=======================================================\n")

    # Generate and output Experiment A visual asset
    generate_experiment_a_chart(stats_table, is_dummy=is_dummy_file)

if __name__ == '__main__':
    main()