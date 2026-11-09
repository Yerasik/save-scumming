import os
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def load_budget_csvs(sim_dir="sim/out/A"):
    """Loads all budget CSV files from sim/out/A/ and tags them with their budget."""
    pattern = os.path.join(sim_dir, "A_budget_T*.csv")
    files = glob.glob(pattern)
    
    if not files:
        raise FileNotFoundError(f"No Experiment A budget CSV files found in {sim_dir}")
    
    all_data = []
    for fpath in files:
        # Extract budget integer from filename (e.g., A_budget_T030min.csv -> 30)
        fname = os.path.basename(fpath)
        try:
            budget_str = fname.split('_')[2].replace('T', '').replace('min.csv', '')
            budget_val = int(budget_str)
        except Exception:
            budget_val = 0
            
        df = pd.read_csv(fpath)
        df['budget'] = budget_val
        all_data.append(df)
        
    combined_df = pd.concat(all_data, ignore_index=True)
    return combined_df

def calculate_budget_stats(df):
    """Computes mean reward, std, count, and 95% CI for each budget."""
    grouped = df.groupby('budget')['reward'].agg(
        mean_reward='mean',
        std_reward='std',
        sample_count='count'
    ).reset_index()
    
    grouped['std_reward'] = grouped['std_reward'].fillna(0)
    grouped['standard_error'] = grouped['std_reward'] / np.sqrt(grouped['sample_count'].replace(0, 1))
    grouped['ci_95_margin'] = 1.96 * grouped['standard_error']
    
    return grouped.sort_values('budget')

def plot_experiment_a(stats_df, output_path="analysis/experiment_a_chart.png"):
    """Generates the DP vs Budget performance chart for Experiment A."""
    plt.figure(figsize=(10, 6))
    
    budgets = stats_df['budget'].values
    means = stats_df['mean_reward'].values
    errors = stats_df['ci_95_margin'].values

    # Plot line with error bars / markers
    plt.errorbar(budgets, means, yerr=errors, fmt='-o', color='royalblue', ecolor='black', 
                 capsize=5, linewidth=2, markersize=8, label='DP Strategy Performance')
    
    plt.xlabel('Time Budget ($T$ in minutes)', fontsize=11, fontweight='bold')
    plt.ylabel('Mean Total Reward', fontsize=11, fontweight='bold')
    plt.title('Experiment A: DP Performance Across Time Budgets ($T$)', fontsize=12, fontweight='bold')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend(frameon=True)

    plt.figtext(0.12, 0.02, "Note: Generated from multi-budget simulator outputs (sim/out/A/).", 
                wrap=True, horizontalalignment='left', fontsize=9, style='italic', color='darkgreen')

    plt.tight_layout(rect=[0, 0.05, 1, 1])
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path)
    plt.close()
    print(f"Experiment A chart successfully saved to: {output_path}")

def main():
    print("-> Loading Experiment A budget simulation outputs...")
    df = load_budget_csvs("sim/out/A")
    
    stats = calculate_budget_stats(df)
    
    print("\n=======================================================")
    print("            EXPERIMENT A: BUDGET ANALYSIS SUMMARY      ")
    print("=======================================================")
    print(stats.to_string(index=False))
    print("=======================================================\n")
    
    plot_experiment_a(stats)

if __name__ == '__main__':
    main()