from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR / "dataset" / "eta_training_v2.csv"

df = pd.read_csv(DATASET_PATH)

print("=" * 50)
print("DATASET OVERVIEW")
print("=" * 50)
print(f"Shape:           {df.shape}")
print(f"Null values:     {df.isnull().sum().sum()}")
print(f"Unique routes:   {df['route'].nunique()}")
print(f"Unique products: {df['product_name'].nunique()}")
print(f"Terminals:       {df['origin_terminal'].unique()}")
print()
print("TARGET VARIABLE — actual_duration_minutes")
print(df['actual_duration_minutes'].describe())
print()
print(f"In hours — mean: {df['actual_duration_minutes'].mean()/60:.1f}h  "
    f"min: {df['actual_duration_minutes'].min()/60:.1f}h  "
    f"max: {df['actual_duration_minutes'].max()/60:.1f}h")
print()
print("CORRELATIONS WITH TARGET:")
numeric_cols = ['distance_km', 'base_eta_minutes', 'departure_hour',
                'day_of_week', 'quantity_litres', 'load_utilization']
corr = df[numeric_cols + ['actual_duration_minutes']].corr()['actual_duration_minutes'].drop('actual_duration_minutes')
print(corr.sort_values(ascending=False))

# Plot 1 — Target distribution
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
fig.suptitle('Figure 1 — Target Variable Distribution', fontsize=13, fontweight='bold')

axes[0].hist(df['actual_duration_minutes'] / 60, bins=40,
            color='#1E3A5F', edgecolor='white', alpha=0.85)
axes[0].axvline(df['actual_duration_minutes'].mean() / 60,
                color='#F5920A', linestyle='--', linewidth=2,
                label=f'Mean: {df["actual_duration_minutes"].mean()/60:.1f}h')
axes[0].set_xlabel('Actual Duration (hours)')
axes[0].set_ylabel('Frequency')
axes[0].set_title('Distribution of Actual Trip Duration')
axes[0].legend()

axes[1].scatter(df['base_eta_minutes']/60, df['actual_duration_minutes']/60,
                alpha=0.3, color='#1E3A5F', s=10)
max_val = max(df['base_eta_minutes'].max(), df['actual_duration_minutes'].max()) / 60
axes[1].plot([0, max_val], [0, max_val], 'r--', linewidth=1.5, label='Perfect baseline')
axes[1].set_xlabel('Base ETA (hours)')
axes[1].set_ylabel('Actual Duration (hours)')
axes[1].set_title('Actual vs Base ETA — Variance Introduced')
axes[1].legend()

plt.tight_layout()
plt.savefig('fig1_target_distribution.png', dpi=150, bbox_inches='tight')
plt.show()
print("Saved: fig1_target_distribution.png")

# Plot 2 — Feature effects
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('Figure 2 — Feature Effects on Trip Duration', fontsize=13, fontweight='bold')

# By terminal
t_means = df.groupby('origin_terminal')['actual_duration_minutes'].mean().sort_values()
axes[0,0].barh(t_means.index, t_means.values/60, color='#1E3A5F', alpha=0.85)
axes[0,0].set_xlabel('Mean Duration (hours)')
axes[0,0].set_title('Average Duration by Origin Terminal')

# By hour
h_means = df.groupby('departure_hour')['actual_duration_minutes'].mean()
axes[0,1].bar(h_means.index, h_means.values/60, color='#F5920A', alpha=0.85)
axes[0,1].set_xlabel('Departure Hour')
axes[0,1].set_ylabel('Mean Duration (hours)')
axes[0,1].set_title('Average Duration by Departure Hour')

# By day
day_labels = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
d_means = df.groupby('day_of_week')['actual_duration_minutes'].mean()
axes[1,0].bar([day_labels[d] for d in d_means.index], d_means.values/60,
            color='#1E3A5F', alpha=0.85)
axes[1,0].set_xlabel('Day of Week')
axes[1,0].set_ylabel('Mean Duration (hours)')
axes[1,0].set_title('Average Duration by Day of Week')

# Distance vs actual
axes[1,1].scatter(df['distance_km'], df['actual_duration_minutes']/60,
                alpha=0.2, color='#1E3A5F', s=8)
axes[1,1].set_xlabel('Distance (km)')
axes[1,1].set_ylabel('Actual Duration (hours)')
axes[1,1].set_title('Distance vs Actual Duration')

plt.tight_layout()
plt.savefig('fig2_feature_effects.png', dpi=150, bbox_inches='tight')
plt.show()
print("Saved: fig2_feature_effects.png")
