import os
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def load_and_process_a(sim_dir="sim/out/A"):
    pattern = os.path.join(sim_dir, "A_budget_T*.csv")
    files = glob.glob(pattern)
    if not files:
        raise FileNotFoundError(f"No Experiment A files found in {sim_dir}")
    
    all_data = []
    for fpath in files:
        fname = os.path.basename(fpath)
        try:
            budget_str = fname.split('_')[2].replace('T', '').replace('min.csv', '')
            budget_val = int(budget_str)
        except Exception:
            budget_val = 0
            
        df = pd.read_csv(fpath)
        df['budget'] = budget_val
        all_data.append(df)
        
    combined = pd.concat(all_data, ignore_index=True)
    
    grouped = combined.groupby(['budget', 'strategy'])['reward'].agg(
        mean_reward='mean',
        std_reward='std',
        sample_count='count'
    ).reset_index()
    
    grouped['std_reward'] = grouped['std_reward'].fillna(0)
    grouped['standard_error'] = grouped['std_reward'] / np.sqrt(grouped['sample_count'].replace(0, 1))
    grouped['ci_95_margin'] = 1.96 * grouped['standard_error']
    return grouped.sort_values(['budget', 'strategy'])

def plot_a(stats_df, output_path="analysis/experiment_a_chart.png"):
    plt.figure(figsize=(10, 6))
    
    target_strategies = ['dp', 'always', 'efficiency_greedy', 'reward_greedy']
    styles = {
        'dp': {'fmt': '-o', 'color': 'royalblue', 'lw': 2.5, 'label': 'DP Strategy'},
        'always': {'fmt': '-s', 'color': 'crimson', 'lw': 2, 'label': 'Always-Reload'},
        'efficiency_greedy': {'fmt': '-^', 'color': 'forestgreen', 'lw': 2, 'label': 'Efficiency-Greedy'},
        'reward_greedy': {'fmt': '-d', 'color': 'darkorange', 'lw': 1.5, 'label': 'Reward-Greedy'}
    }
    
    for strat in target_strategies:
        sub = stats_df[stats_df['strategy'] == strat].copy()
        if sub.empty:
            continue
        
        # Ensure budget is explicit integer for true numerical X coordinates
        x_numeric = sub['budget'].astype(int).values
        y_numeric = sub['mean_reward'].values
        y_err = sub['ci_95_margin'].values
        
        cfg = styles.get(strat, {'fmt': '-o', 'color': 'black', 'lw': 1.5, 'label': strat})
        
        # Plot directly on continuous numerical X coordinates
        plt.errorbar(x_numeric, y_numeric, yerr=y_err, 
                     fmt=cfg['fmt'], color=cfg['color'], capsize=5, linewidth=cfg['lw'], 
                     markersize=8, label=cfg['label'])
        
    plt.xlabel('Time Budget ($T$ in minutes)', fontsize=11, fontweight='bold')
    plt.ylabel('Mean Total Reward', fontsize=11, fontweight='bold')
    plt.title('Experiment A: Strategy Comparison across Time Budgets (H1 Test)', fontsize=12, fontweight='bold')
    
    # Force explicit numerical ticks at data points while preserving true scale
    plt.xticks([10, 20, 30, 60, 120])
    plt.xlim(0, 125)
    
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend(frameon=True, fontsize=10)
    
    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Saved truly proportional Experiment A chart to: {output_path}")

def main():
    df = load_and_process_a()
    print("=== EXPERIMENT A (H1) COMPARATIVE SUMMARY ===")
    print(df[df['strategy'].isin(['dp', 'always', 'efficiency_greedy', 'reward_greedy'])].to_string(index=False))
    plot_a(df)

if __name__ == '__main__':
    main()