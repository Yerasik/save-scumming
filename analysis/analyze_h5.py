import os
import glob
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def load_and_process_h5(sim_dir="sim/out/H5"):
    pattern = os.path.join(sim_dir, "H5_*.csv")
    files = glob.glob(pattern)
    if not files:
        raise FileNotFoundError(f"No Experiment H5 files found in {sim_dir}")
    
    all_data = []
    for fpath in files:
        fname = os.path.basename(fpath)
        
        if "known" in fname:
            label = "Known p=0.02"
            sort_val = 1.0
        elif "beta" in fname:
            a_match = re.search(r'a([0-9p]+)', fname)
            b_match = re.search(r'b([0-9p]+)', fname)
            a_str = a_match.group(1).replace('p', '.') if a_match else "1"
            b_str = b_match.group(1).replace('p', '.') if b_match else "1"
            a_val, b_val = float(a_str), float(b_str)
            label = f"Beta (a={a_str}, b={b_str})"
            sort_val = a_val / (a_val + b_val) if (a_val + b_val) > 0 else 0.0
        else:
            label = fname
            sort_val = 99.0
            
        df = pd.read_csv(fpath)
        df['condition'] = label
        df['sort_key'] = sort_val
        all_data.append(df)
        
    combined = pd.concat(all_data, ignore_index=True)
    
    grouped = combined.groupby(['condition', 'sort_key', 'strategy'])['reward'].agg(
        mean_reward='mean',
        std_reward='std',
        sample_count='count'
    ).reset_index()
    
    grouped['std_reward'] = grouped['std_reward'].fillna(0)
    grouped['standard_error'] = grouped['std_reward'] / np.sqrt(grouped['sample_count'].replace(0, 1))
    grouped['ci_95_margin'] = 1.96 * grouped['standard_error']
    return grouped.sort_values(['sort_key', 'strategy'])

def plot_h5(stats_df, output_path="analysis/experiment_h5_chart.png"):
    plt.figure(figsize=(11, 6))
    
    conditions_ordered = stats_df.sort_values('sort_key')['condition'].unique()
    cond_map = {cond: i for i, cond in enumerate(conditions_ordered)}
    
    target_strategies = ['dp', 'always', 'fixed_k_3', 'fixed_k_5']
    styles = {
        'dp': {'fmt': '-o', 'color': 'purple', 'lw': 2.5, 'ms': 8, 'label': 'DP Strategy'},
        'always': {'fmt': '-s', 'color': 'crimson', 'lw': 2, 'ms': 7, 'label': 'Always-Reload'},
        'fixed_k_3': {'fmt': '-^', 'color': 'teal', 'lw': 1.5, 'ms': 7, 'label': 'Cap k=3'},
        'fixed_k_5': {'fmt': '-d', 'color': 'dodgerblue', 'lw': 1.5, 'ms': 7, 'label': 'Cap k=5'}
    }
    
    x_pos = np.arange(len(conditions_ordered))
    
    for strat in target_strategies:
        sub = stats_df[stats_df['strategy'] == strat]
        if sub.empty:
            continue
        sub_sorted = sub.sort_values('sort_key')
        x_vals = [cond_map[c] for c in sub_sorted['condition']]
        cfg = styles.get(strat, {'fmt': '-o', 'color': 'black', 'lw': 1.5, 'ms': 6, 'label': strat})
        
        plt.errorbar(x_vals, sub_sorted['mean_reward'], yerr=sub_sorted['ci_95_margin'], 
                     fmt=cfg['fmt'], color=cfg['color'], capsize=5, linewidth=cfg['lw'], 
                     markersize=cfg['ms'], label=cfg['label'])
        
    plt.xticks(x_pos, conditions_ordered, fontsize=10, fontweight='bold')
    plt.xlabel('Prior Belief Distribution Condition', fontsize=11, fontweight='bold')
    plt.ylabel('Mean Total Reward', fontsize=11, fontweight='bold')
    plt.title('Experiment H5: Strategy Performance Across Prior Beliefs (Multi-Series)', fontsize=12, fontweight='bold')
    
    plt.ylim(0, 170)
    plt.grid(True, linestyle='--', alpha=0.6)
    
    # Placed legend in center-right to prevent obscuring data points on the bottom-right
    plt.legend(frameon=True, fontsize=10, loc='center right')
    
    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Saved publication-grade Experiment H5 chart to: {output_path}")

def main():
    df = load_and_process_h5()
    print("=== EXPERIMENT H5 COMPARATIVE SUMMARY ===")
    print(df[df['strategy'].isin(['dp', 'always', 'fixed_k_3', 'fixed_k_5'])].drop(columns=['sort_key']).to_string(index=False))
    plot_h5(df)

if __name__ == '__main__':
    main()