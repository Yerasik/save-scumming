import os
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def load_experiment_d_csvs(sim_dir="sim/out/D"):
    """Loads all Experiment D CSV files and extracts future reward levels."""
    pattern = os.path.join(sim_dir, "D2_later_*.csv")
    files = glob.glob(pattern)
    
    if not files:
        raise FileNotFoundError(f"No Experiment D CSV files found in {sim_dir}")
    
    all_data = []
    for fpath in files:
        fname = os.path.basename(fpath)
        # Parse reward level from filename (e.g., D2_later_reward_040.csv -> 0.40 or removed -> 0.0)
        if "removed" in fname:
            reward_val = 0.0
            label = "Removed (No Future Reward)"
        else:
            try:
                reward_str = fname.split('_')[3].replace('.csv', '')
                reward_val = float(reward_str) / 100.0  # e.g., 040 -> 0.40
                label = f"Future Reward: {reward_val}"
            except Exception:
                reward_val = 0.0
                label = "Unknown"
                
        df = pd.read_csv(fpath)
        df['future_reward'] = reward_val
        df['condition'] = label
        all_data.append(df)
        
    return pd.concat(all_data, ignore_index=True)

def calculate_d_stats(df):
    """Computes statistics grouped by future reward level."""
    grouped = df.groupby(['future_reward', 'condition'])['reward'].agg(
        mean_reward='mean',
        std_reward='std',
        sample_count='count'
    ).reset_index()
    
    grouped['std_reward'] = grouped['std_reward'].fillna(0)
    grouped['standard_error'] = grouped['std_reward'] / np.sqrt(grouped['sample_count'].replace(0, 1))
    grouped['ci_95_margin'] = 1.96 * grouped['standard_error']
    
    return grouped.sort_values('future_reward')

def plot_experiment_d(stats_df, output_path="analysis/experiment_d_chart.png"):
    """Generates the Experiment D performance chart testing Hypothesis 3."""
    plt.figure(figsize=(10, 6))
    
    rewards = stats_df['future_reward'].values
    means = stats_df['mean_reward'].values
    errors = stats_df['ci_95_margin'].values

    plt.errorbar(rewards, means, yerr=errors, fmt='-s', color='darkorange', ecolor='black', 
                 capsize=5, linewidth=2, markersize=8, label='DP Strategy (H3 Test)')
    
    plt.xlabel('Future Opportunity Reward Magnitude', fontsize=11, fontweight='bold')
    plt.ylabel('Mean Total Reward', fontsize=11, fontweight='bold')
    plt.title('Experiment D: Impact of Future Opportunities on Strategy Performance (H3)', fontsize=12, fontweight='bold')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend(frameon=True)

    plt.figtext(0.12, 0.02, "Note: Generated from simulator outputs in sim/out/D/ (Hypothesis 3 verification).", 
                wrap=True, horizontalalignment='left', fontsize=9, style='italic', color='darkgreen')

    plt.tight_layout(rect=[0, 0.05, 1, 1])
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path)
    plt.close()
    print(f"Experiment D chart successfully saved to: {output_path}")

def main():
    print("-> Loading Experiment D simulation outputs...")
    df = load_experiment_d_csvs("sim/out/D")
    
    stats = calculate_d_stats(df)
    
    print("\n=======================================================")
    print("            EXPERIMENT D: H3 ANALYSIS SUMMARY          ")
    print("=======================================================")
    print(stats.to_string(index=False))
    print("=======================================================\n")
    
    plot_experiment_d(stats)

if __name__ == '__main__':
    main()