import os
import glob
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def load_h5_csvs(sim_dir="sim/out/H5"):
    """Loads all Experiment H5 CSV files from sim/out/H5/ using robust regex parsing."""
    pattern = os.path.join(sim_dir, "H5_*.csv")
    files = glob.glob(pattern)
    
    if not files:
        raise FileNotFoundError(f"No Experiment H5 CSV files found in {sim_dir}")
    
    all_data = []
    for fpath in files:
        fname = os.path.basename(fpath)
        
        if "known" in fname:
            label = "Known $p=0.02$"
            sort_val = 1.0
        elif "beta" in fname:
            # Safely extract alpha and beta values using regex
            a_match = re.search(r'a([0-9p]+)', fname)
            b_match = re.search(r'b([0-9p]+)', fname)
            
            a_str = a_match.group(1).replace('p', '.') if a_match else "1"
            b_str = b_match.group(1).replace('p', '.') if b_match else "1"
            
            a_val, b_val = float(a_str), float(b_str)
            # Use raw string r"" so Python doesn't steal \alpha and \beta as escape codes
            label = rf"Beta Prior ($\alpha={a_str}, \beta={b_str}$)"
            sort_val = a_val / (a_val + b_val) if (a_val + b_val) > 0 else 0.0
        else:
            label = fname
            sort_val = 99.0
            
        df = pd.read_csv(fpath)
        df['condition'] = label
        df['sort_key'] = sort_val
        all_data.append(df)
        
    combined_df = pd.concat(all_data, ignore_index=True)
    return combined_df

def calculate_h5_stats(df):
    """Computes mean reward, std, count, and 95% CI for H5 prior conditions."""
    grouped = df.groupby(['condition', 'sort_key'])['reward'].agg(
        mean_reward='mean',
        std_reward='std',
        sample_count='count'
    ).reset_index()
    
    grouped['std_reward'] = grouped['std_reward'].fillna(0)
    grouped['standard_error'] = grouped['std_reward'] / np.sqrt(grouped['sample_count'].replace(0, 1))
    grouped['ci_95_margin'] = 1.96 * grouped['standard_error']
    
    return grouped.sort_values('sort_key')

def plot_experiment_h5(stats_df, output_path="analysis/experiment_h5_chart.png"):
    """Generates the Prior Sensitivity performance chart for Experiment H5."""
    plt.figure(figsize=(10, 6))
    
    conditions = stats_df['condition'].values
    means = stats_df['mean_reward'].values
    errors = stats_df['ci_95_margin'].values

    x_pos = np.arange(len(conditions))
    plt.errorbar(x_pos, means, yerr=errors, fmt='o', color='purple', ecolor='black', 
                 capsize=5, elinewidth=1.5, markersize=8, label='H5 Prior Sensitivity')
    
    plt.xticks(x_pos, conditions, rotation=10, fontsize=10)
    plt.xlabel('Prior Belief Distribution Condition', fontsize=11, fontweight='bold')
    plt.ylabel('Mean Total Reward', fontsize=11, fontweight='bold')
    plt.title('Experiment H5: Strategy Sensitivity Across Prior Belief Distributions', fontsize=12, fontweight='bold')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend(frameon=True)

    plt.figtext(0.12, 0.02, "Note: Generated from multi-seed simulator outputs in sim/out/H5/ (Hypothesis 5).", 
                wrap=True, horizontalalignment='left', fontsize=9, style='italic', color='darkgreen')

    plt.tight_layout(rect=[0, 0.05, 1, 1])
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path)
    plt.close()
    print(f"Experiment H5 chart successfully saved to: {output_path}")

def main():
    print("-> Loading Experiment H5 simulation outputs...")
    df = load_h5_csvs("sim/out/H5")
    
    stats = calculate_h5_stats(df)
    
    print("\n=======================================================")
    print("        EXPERIMENT H5: PRIOR SENSITIVITY SUMMARY       ")
    print("=======================================================")
    print(stats.drop(columns=['sort_key']).to_string(index=False))
    print("=======================================================\n")
    
    plot_experiment_h5(stats)

if __name__ == '__main__':
    main()