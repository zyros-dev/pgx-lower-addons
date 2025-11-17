#!/usr/bin/env python3

import sqlite3
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.colors import to_rgba, to_hex
import seaborn as sns
import os

DB_PATH = './graphs/data/benchmark.db'
PERF_STATS_DB = './graphs/data/perf-stats.db'
OUTPUT_DIR = './graphs/outputs'

os.makedirs(OUTPUT_DIR, exist_ok=True)

sns.set_style("whitegrid")
sns.set_palette("Set2")
POSTGRES_COLOR = '#1f77b4'
PGX_COLOR = '#ff7f0e'

def draw_bar_with_boxplot(ax, data_list, positions, colors, width=0.75, y_cap=None):
    medians = [np.median(d) for d in data_list]
    bars = ax.bar(positions, medians, width=width, color=colors, alpha=0.6, edgecolor='black', linewidth=1)

    outlier_info = []

    for pos, data, color in zip(positions, data_list, colors):
        q1 = np.percentile(data, 25)
        q3 = np.percentile(data, 75)
        whisker_low = np.percentile(data, 5)
        whisker_high = np.percentile(data, 95)
        median = np.median(data)

        ax.plot([pos, pos], [whisker_low, whisker_high], color='black', linewidth=2.5)
        ax.plot([pos - width/2, pos + width/2], [whisker_low, whisker_low], color='black', linewidth=2)
        ax.plot([pos - width/2, pos + width/2], [whisker_high, whisker_high], color='black', linewidth=2)

        light_color = to_hex(to_rgba(color, alpha=0.4))
        rect = mpatches.Rectangle((pos - width/3, q1), width*2/3, q3 - q1,
                                   linewidth=2, edgecolor='black', facecolor=light_color)
        ax.add_patch(rect)

        ax.plot([pos - width/3, pos + width/3], [median, median], color='black', linewidth=3)

        outliers_low = data[data < whisker_low]
        outliers_high = data[data > whisker_high]

        if y_cap is not None:
            on_chart_high = outliers_high[outliers_high <= y_cap]
            off_chart_high = outliers_high[outliers_high > y_cap]

            ax.scatter([pos] * len(outliers_low), outliers_low, facecolor='none', edgecolor='black', s=25, zorder=3)
            ax.scatter([pos] * len(on_chart_high), on_chart_high, facecolor='none', edgecolor='black', s=25, zorder=3)

            for val in off_chart_high:
                outlier_info.append((pos, val))
        else:
            ax.scatter([pos] * len(outliers_low), outliers_low, facecolor='none', edgecolor='black', s=25, zorder=3)
            ax.scatter([pos] * len(outliers_high), outliers_high, facecolor='none', edgecolor='black', s=25, zorder=3)

    return outlier_info

def cap_axis_with_outlier_arrows(ax, outlier_info):
    if not outlier_info:
        return

    y_limit = ax.get_ylim()[1]

    for pos, val in outlier_info:
        ax.annotate('', xy=(pos, y_limit * 0.95), xytext=(pos, y_limit * 0.88),
                   arrowprops=dict(arrowstyle='->', lw=1.5, color='black'))
        ax.text(pos, y_limit * 0.97, f'{val:.0f}', ha='center', va='bottom',
               fontsize=8, bbox=dict(boxstyle='round,pad=0.2',
               facecolor='white', edgecolor='gray', linewidth=0.8))

def extract_metrics(queries_df):
    def parse_metrics(row):
        try:
            exec_meta = json.loads(row['execution_metadata'])
            duration_ms = exec_meta.get('duration_ms')
        except:
            duration_ms = None

        try:
            metrics = json.loads(row['metrics_json'])
            memory_peak_mb = metrics.get('memory_peak_mb')
        except:
            memory_peak_mb = None

        return pd.Series({
            'duration_ms': duration_ms,
            'memory_peak_mb': memory_peak_mb
        })

    metrics = queries_df.apply(parse_metrics, axis=1)
    return pd.concat([queries_df, metrics], axis=1)

def load_data():
    conn = sqlite3.connect(DB_PATH)

    query = """
    SELECT
        q.query_name,
        q.iteration,
        q.pgx_enabled,
        q.execution_metadata,
        q.metrics_json,
        r.label,
        r.scale_factor
    FROM queries q
    JOIN runs r ON q.run_id = r.run_id
    ORDER BY r.label, q.query_name, q.iteration
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    df = extract_metrics(df)

    df = df.dropna(subset=['duration_ms', 'memory_peak_mb'])

    df['pgx_label'] = df['pgx_enabled'].map({1: 'pgx-lower', 0: 'PostgreSQL'})

    return df

def load_perf_stats():
    conn = sqlite3.connect(PERF_STATS_DB)

    query = """
    SELECT
        run_id,
        query_name,
        pgx_enabled,
        iteration,
        ipc,
        llc_miss_rate,
        branch_miss_rate,
        branches
    FROM perf_stats
    ORDER BY run_id, query_name, iteration
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    # Drop rows with missing values in key metrics
    df = df.dropna(subset=['ipc', 'llc_miss_rate', 'branch_miss_rate', 'branches'])

    # Use run_id as label and convert pgx_enabled to label
    df['label'] = df['run_id']
    df['pgx_label'] = df['pgx_enabled'].map({1: 'pgx-lower', 0: 'PostgreSQL'})

    return df

def reorder_labels(labels):
    sorted_labels = sorted(labels)
    if len(sorted_labels) >= 2:
        sorted_labels[0], sorted_labels[1] = sorted_labels[1], sorted_labels[0]
    return sorted_labels

def create_box_plot_pdf(df):
    labels = reorder_labels(df['label'].unique())
    n_labels = len(labels)
    n_cols = 3
    n_rows = (n_labels + n_cols - 1) // n_cols

    with PdfPages(f'{OUTPUT_DIR}/box_plots.pdf') as pdf:
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(18, 5 * n_rows))
        axes = axes.flatten()

        for idx, label in enumerate(labels):
            ax = axes[idx]
            label_data = df[df['label'] == label]
            queries = sorted(label_data['query_name'].unique())

            need_cap = 'SF=0.01, indexes disabled - excluding postgres' in label
            y_cap = None

            if need_cap:
                all_values = label_data['duration_ms'].values
                y_cap = np.percentile(all_values, 98)

            pos = 0
            tick_positions = []
            all_outliers = []

            for query in queries:
                query_data = label_data[label_data['query_name'] == query]
                tick_positions.append(pos + 0.5)

                plot_data = []
                positions = []
                colors = []

                for pgx_label in ['PostgreSQL', 'pgx-lower']:
                    subset = query_data[query_data['pgx_label'] == pgx_label]['duration_ms']
                    if len(subset) > 0:
                        plot_data.append(subset.values)
                        positions.append(pos)
                        colors.append(POSTGRES_COLOR if pgx_label == 'PostgreSQL' else PGX_COLOR)
                        pos += 1

                if plot_data:
                    outliers = draw_bar_with_boxplot(ax, plot_data, positions, colors, y_cap=y_cap)
                    all_outliers.extend(outliers)

                pos += 0.3

            if need_cap and y_cap:
                ax.set_ylim(0, y_cap * 1.1)

            ax.set_xticks(tick_positions)
            ax.set_xticklabels(queries, rotation=45, ha='right', fontsize=8)
            ax.set_ylabel('Duration (ms)', fontweight='bold')
            ax.set_title(label, fontsize=10, fontweight='bold')
            ax.grid(axis='y', alpha=0.3)

            if need_cap:
                cap_axis_with_outlier_arrows(ax, all_outliers)

        for idx in range(n_labels, len(axes)):
            axes[idx].axis('off')

        postgres_patch = mpatches.Patch(facecolor=POSTGRES_COLOR, alpha=0.6, edgecolor='black', label='PostgreSQL')
        pgx_patch = mpatches.Patch(facecolor=PGX_COLOR, alpha=0.6, edgecolor='black', label='pgx-lower')
        fig.legend(handles=[postgres_patch, pgx_patch], loc='upper right', fontsize=10)

        fig.suptitle('Execution Time Distribution. Lower is better', fontsize=16, fontweight='bold', y=0.995)
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)

def create_diff_plot_pdf(df):
    labels = reorder_labels(df['label'].unique())
    n_labels = len(labels)
    n_cols = 3
    n_rows = (n_labels + n_cols - 1) // n_cols

    with PdfPages(f'{OUTPUT_DIR}/diff_plots.pdf') as pdf:
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(18, 5 * n_rows))
        axes = axes.flatten()

        for idx, label in enumerate(labels):
            ax = axes[idx]
            label_data = df[df['label'] == label]
            queries = sorted(label_data['query_name'].unique())

            all_diffs = []
            pos = 0
            tick_positions = []
            plot_data_list = []

            for query in queries:
                query_data = label_data[label_data['query_name'] == query]
                postgres_times = query_data[query_data['pgx_label'] == 'PostgreSQL'].sort_values('iteration')['duration_ms'].values
                pgx_times = query_data[query_data['pgx_label'] == 'pgx-lower'].sort_values('iteration')['duration_ms'].values

                min_len = min(len(postgres_times), len(pgx_times))
                if min_len > 0:
                    diffs = postgres_times[:min_len] - pgx_times[:min_len]
                    all_diffs.extend(diffs)
                    tick_positions.append(pos)
                    plot_data_list.append((pos, diffs))

                pos += 1

            if all_diffs:
                y_max = np.percentile(np.abs(all_diffs), 98)
                all_outliers = []

                for pos, diffs in plot_data_list:
                    outliers = draw_bar_with_boxplot(ax, [diffs], [pos], ['#2ecc71'], y_cap=y_max)
                    all_outliers.extend(outliers)

                max_val = max(np.abs(all_diffs))
                if max_val > y_max:
                    ax.set_ylim(-y_max * 1.1, y_max * 1.1)
                    cap_axis_with_outlier_arrows(ax, all_outliers)

            ax.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
            ax.set_xticks(tick_positions)
            ax.set_xticklabels(queries, rotation=45, ha='right', fontsize=8)
            ax.set_ylabel('Difference (ms)', fontweight='bold')
            ax.set_title(label, fontsize=10, fontweight='bold')
            ax.grid(axis='y', alpha=0.3)

        for idx in range(n_labels, len(axes)):
            axes[idx].axis('off')

        diff_patch = mpatches.Patch(facecolor='#2ecc71', alpha=0.6, edgecolor='black', label='PostgreSQL - pgx-lower')
        fig.legend(handles=[diff_patch], loc='upper right', fontsize=10)

        fig.suptitle('Performance Difference. Higher means pgx-lower is faster than PostgreSQL', fontsize=16, fontweight='bold', y=0.995)
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)

def create_memory_plot_pdf(df):
    labels = reorder_labels(df['label'].unique())
    n_labels = len(labels)
    n_cols = 3
    n_rows = (n_labels + n_cols - 1) // n_cols

    with PdfPages(f'{OUTPUT_DIR}/memory_plots.pdf') as pdf:
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(18, 5 * n_rows))
        axes = axes.flatten()

        for idx, label in enumerate(labels):
            ax = axes[idx]
            label_data = df[df['label'] == label]
            queries = sorted(label_data['query_name'].unique())

            pos = 0
            tick_positions = []

            for query in queries:
                query_data = label_data[label_data['query_name'] == query]
                tick_positions.append(pos + 0.5)

                plot_data = []
                positions = []
                colors = []

                for pgx_label in ['PostgreSQL', 'pgx-lower']:
                    subset = query_data[query_data['pgx_label'] == pgx_label]['memory_peak_mb']
                    if len(subset) > 0:
                        plot_data.append(subset.values)
                        positions.append(pos)
                        colors.append(POSTGRES_COLOR if pgx_label == 'PostgreSQL' else PGX_COLOR)
                        pos += 1

                if plot_data:
                    draw_bar_with_boxplot(ax, plot_data, positions, colors)

                pos += 0.3

            ax.set_xticks(tick_positions)
            ax.set_xticklabels(queries, rotation=45, ha='right', fontsize=8)
            ax.set_ylabel('Peak Memory (MB)', fontweight='bold')
            ax.set_title(label, fontsize=10, fontweight='bold')
            ax.grid(axis='y', alpha=0.3)

        for idx in range(n_labels, len(axes)):
            axes[idx].axis('off')

        postgres_patch = mpatches.Patch(facecolor=POSTGRES_COLOR, alpha=0.6, edgecolor='black', label='PostgreSQL')
        pgx_patch = mpatches.Patch(facecolor=PGX_COLOR, alpha=0.6, edgecolor='black', label='pgx-lower')
        fig.legend(handles=[postgres_patch, pgx_patch], loc='upper right', fontsize=10)

        fig.suptitle('Peak Memory Usage Distribution. Lower is better', fontsize=16, fontweight='bold', y=0.995)
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)

def create_memory_diff_pdf(df):
    labels = reorder_labels(df['label'].unique())
    n_labels = len(labels)
    n_cols = 3
    n_rows = (n_labels + n_cols - 1) // n_cols

    with PdfPages(f'{OUTPUT_DIR}/memory_diffs.pdf') as pdf:
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(18, 5 * n_rows))
        axes = axes.flatten()

        for idx, label in enumerate(labels):
            ax = axes[idx]
            label_data = df[df['label'] == label]
            queries = sorted(label_data['query_name'].unique())

            all_diffs = []
            pos = 0
            tick_positions = []
            plot_data_list = []

            for query in queries:
                query_data = label_data[label_data['query_name'] == query]
                postgres_mem = query_data[query_data['pgx_label'] == 'PostgreSQL'].sort_values('iteration')['memory_peak_mb'].values
                pgx_mem = query_data[query_data['pgx_label'] == 'pgx-lower'].sort_values('iteration')['memory_peak_mb'].values

                min_len = min(len(postgres_mem), len(pgx_mem))
                if min_len > 0:
                    diffs = postgres_mem[:min_len] - pgx_mem[:min_len]
                    all_diffs.extend(diffs)
                    tick_positions.append(pos)
                    plot_data_list.append((pos, diffs))

                pos += 1

            if all_diffs:
                y_max = np.percentile(np.abs(all_diffs), 98)
                all_outliers = []

                for pos, diffs in plot_data_list:
                    outliers = draw_bar_with_boxplot(ax, [diffs], [pos], ['#9b59b6'], y_cap=y_max)
                    all_outliers.extend(outliers)

                max_val = max(np.abs(all_diffs))
                if max_val > y_max:
                    ax.set_ylim(-y_max * 1.1, y_max * 1.1)
                    cap_axis_with_outlier_arrows(ax, all_outliers)

            ax.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
            ax.set_xticks(tick_positions)
            ax.set_xticklabels(queries, rotation=45, ha='right', fontsize=8)
            ax.set_ylabel('Memory Difference (MB)', fontweight='bold')
            ax.set_title(label, fontsize=10, fontweight='bold')
            ax.grid(axis='y', alpha=0.3)

        for idx in range(n_labels, len(axes)):
            axes[idx].axis('off')

        diff_patch = mpatches.Patch(facecolor='#9b59b6', alpha=0.6, edgecolor='black', label='PostgreSQL - pgx-lower')
        fig.legend(handles=[diff_patch], loc='upper right', fontsize=10)

        fig.suptitle('Memory Usage Difference. Lower is better', fontsize=16, fontweight='bold', y=0.995)
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)

def create_perf_metric_plot_pdf(df, metric_column, metric_label, metric_units, filename, higher_better=False):
    labels = reorder_labels(df['label'].unique())
    n_labels = len(labels)
    n_cols = 2
    n_rows = (n_labels + n_cols - 1) // n_cols

    with PdfPages(f'{OUTPUT_DIR}/{filename}') as pdf:
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(14, 5 * n_rows))
        axes = axes.flatten()

        for idx, label in enumerate(labels):
            ax = axes[idx]
            label_data = df[df['label'] == label]
            queries = sorted(label_data['query_name'].unique())

            # Calculate y_cap at 98th percentile to detect outliers
            all_values = label_data[metric_column].values
            y_cap = np.percentile(all_values, 98)

            pos = 0
            tick_positions = []
            all_outliers = []

            for query in queries:
                query_data = label_data[label_data['query_name'] == query]
                tick_positions.append(pos + 0.5)

                plot_data = []
                positions = []
                colors = []

                for pgx_label in ['PostgreSQL', 'pgx-lower']:
                    subset = query_data[query_data['pgx_label'] == pgx_label][metric_column]
                    if len(subset) > 0:
                        plot_data.append(subset.values)
                        positions.append(pos)
                        colors.append(POSTGRES_COLOR if pgx_label == 'PostgreSQL' else PGX_COLOR)
                        pos += 1

                if plot_data:
                    outliers = draw_bar_with_boxplot(ax, plot_data, positions, colors, y_cap=y_cap)
                    all_outliers.extend(outliers)

                pos += 0.3

            if all_outliers and y_cap:
                ax.set_ylim(0, y_cap * 1.1)
                cap_axis_with_outlier_arrows(ax, all_outliers)

            ax.set_xticks(tick_positions)
            ax.set_xticklabels(queries, rotation=45, ha='right', fontsize=8)
            ax.set_ylabel(f'{metric_label} ({metric_units})', fontweight='bold')
            ax.set_title(label, fontsize=10, fontweight='bold')
            ax.grid(axis='y', alpha=0.3)

        for idx in range(n_labels, len(axes)):
            axes[idx].axis('off')

        postgres_patch = mpatches.Patch(facecolor=POSTGRES_COLOR, alpha=0.6, edgecolor='black', label='PostgreSQL')
        pgx_patch = mpatches.Patch(facecolor=PGX_COLOR, alpha=0.6, edgecolor='black', label='pgx-lower')
        fig.legend(handles=[postgres_patch, pgx_patch], loc='upper right', fontsize=10)

        better_text = 'Higher is better' if higher_better else 'Lower is better'
        fig.suptitle(f'{metric_label} Distribution. {better_text}', fontsize=16, fontweight='bold', x=0.35, y=0.995)
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)

def create_ipc_plot_pdf(df):
    """Create IPC (Instructions Per Cycle) plots"""
    create_perf_metric_plot_pdf(df, 'ipc', 'IPC', 'instructions/cycle', 'ipc_plots.pdf', higher_better=True)

def create_llc_miss_plot_pdf(df):
    """Create LLC miss rate plots"""
    create_perf_metric_plot_pdf(df, 'llc_miss_rate', 'LLC Miss Rate', '%', 'llc_miss_plots.pdf', higher_better=False)

def create_branch_miss_plot_pdf(df):
    """Create branch miss rate plots"""
    create_perf_metric_plot_pdf(df, 'branch_miss_rate', 'Branch Miss Rate', '%', 'branch_miss_plots.pdf', higher_better=False)

def create_branches_plot_pdf(df):
    """Create branches count plots"""
    create_perf_metric_plot_pdf(df, 'branches', 'Number of Branches', 'count', 'branches_plots.pdf', higher_better=False)

def main():
    print("Loading benchmark data...")
    df = load_data()
    print(f"Loaded {len(df)} data points from database")
    print(f"Labels: {sorted(df['label'].unique())}")

    print("\nGenerating box_plots.pdf...")
    create_box_plot_pdf(df)

    print("Generating diff_plots.pdf...")
    create_diff_plot_pdf(df)

    print("Generating memory_plots.pdf...")
    create_memory_plot_pdf(df)

    print("Generating memory_diffs.pdf...")
    create_memory_diff_pdf(df)

    print("\nLoading performance stats data...")
    try:
        perf_df = load_perf_stats()
        print(f"Loaded {len(perf_df)} perf stats data points from database")
        print(f"Labels: {sorted(perf_df['label'].unique())}")

        print("\nGenerating ipc_plots.pdf...")
        create_ipc_plot_pdf(perf_df)

        print("Generating llc_miss_plots.pdf...")
        create_llc_miss_plot_pdf(perf_df)

        print("Generating branch_miss_plots.pdf...")
        create_branch_miss_plot_pdf(perf_df)

        print("Generating branches_plots.pdf...")
        create_branches_plot_pdf(perf_df)
    except Exception as e:
        print(f"Warning: Could not load performance stats: {e}")

    print(f"\nDone! PDFs saved to {OUTPUT_DIR}/")

if __name__ == '__main__':
    main()
