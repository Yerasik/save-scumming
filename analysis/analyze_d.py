import os
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def load_and_process_d(sim_dir="sim/out/D"):
    pattern = os.path.join(sim_dir, "D2_later_*.csv")
    files = glob.glob(pattern)
    if not files:
        raise FileNotFoundError(f"No Experiment D files found in {sim_dir}")
    
    all_data = []
    for fpath in files:
        fname = os.path.basename(fpath)
        if "removed" in fname:
            reward_val = 0
        else:
            try:
                num_str = [p for p in fname.split('_') if len(p)==3 and p.isdigit()][0]
                reward_val = int(num_str)
            except Exception:
                if "010" in fname: reward_val = 10
                elif "020" in fname: reward_val = 20
                elif "040" in fname: reward_val = 40
                elif "080" in fname: reward_val = 80
                elif "160" in fname: reward_val = 160
                else: reward_val = 0
                
        df = pd.read_csv(fpath)
        df['future_reward'] = reward_val
        all_data.append(df)
        
    combined = pd.concat(all_data, ignore_index=True)
    
    grouped = combined.groupby(['future_reward', 'strategy'])['reward'].agg(
        mean_reward='mean',
        std_reward='std',
        sample_count='count'
    ).reset_index()
    
    grouped['std_reward'] = grouped['std_reward'].fillna(0)
    grouped['standard_error'] = grouped['std_reward'] / np.sqrt(grouped['sample_count'].replace(0, 1))
    grouped['ci_95_margin'] = 1.96 * grouped['standard_error']
    return grouped.sort_values(['future_reward', 'strategy'])

def plot_d(stats_df, output_path="analysis/experiment_d_chart.png"):
    plt.figure(figsize=(10, 6))
    
    # Strictly the three strategies required by Yera & H3 spec
    target_strategies = ['dp', 'always', 'reward_greedy']
    styles = {
        'dp': {'fmt': '-o', 'color': 'darkorange', 'lw': 2.5, 'ms': 9, 'label': 'DP Strategy'},
        'always': {'fmt': '-s', 'color': 'crimson', 'lw': 2, 'ms': 7, 'label': 'Always-Reload'},
        'reward_greedy': {'fmt': '--^', 'color': 'purple', 'lw': 2, 'ms': 8, 'label': 'Reward-Greedy'}
    }
    
    for strat in target_strategies:
        sub = stats_df[stats_df['strategy'] == strat].copy()
        if sub.empty:
            continue
        
        x_numeric = sub['future_reward'].astype(int).values
        y_numeric = sub['mean_reward'].values
        y_err = sub['ci_95_margin'].values
        
        cfg = styles.get(strat, {'fmt': '-o', 'color': 'black', 'lw': 1.5, 'ms': 6, 'label': strat})
        
        plt.errorbar(x_numeric, y_numeric, yerr=y_err, 
                     fmt=cfg['fmt'], color=cfg['color'], capsize=5, linewidth=cfg['lw'], 
                     markersize=cfg['ms'], label=cfg['label'])
        
    plt.xlabel('Future Opportunity Reward Magnitude ($R_{future}$)', fontsize=11, fontweight='bold')
    plt.ylabel('Mean Total Reward', fontsize=11, fontweight='bold')
    plt.title('Experiment D: Impact of Future Opportunities (H3 Test - Proportional X-Axis)', fontsize=12, fontweight='bold')
    
    plt.xticks([0, 10, 20, 40, 80, 160], fontsize=10)
    plt.xlim(-5, 170)
    plt.ylim(-5, 115)
    
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend(frameon=True, fontsize=10, loc='upper left')
    
    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Saved publication-grade Experiment D chart to: {output_path}")

def main():
    df = load_and_process_d()
    print("=== EXPERIMENT D (H3) COMPARATIVE SUMMARY ===")
    print(df[df['strategy'].isin(['dp', 'always', 'reward_greedy'])].to_string(index=False))
    plot_d(df)

if __name__ == '__main__':
    main()