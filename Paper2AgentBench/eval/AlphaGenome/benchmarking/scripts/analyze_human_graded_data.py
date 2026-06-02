#!/usr/bin/env python3
"""
Script to analyze human-graded CSV files from AlphaGenome benchmarking data.

This script loads all CSV files with suffix 'human_graded.csv' from the 
AlphaGenome/benchmarking/data directory, concatenates them with unique dataset labels,
and creates five summary plots using plotnine:
1. Bar plot comparing correct answers by dataset, faceted by tutorial/novel
2. Box plot comparing run time distributions by dataset, faceted by tutorial/novel  
3. Box plot comparing cost per question between MCP and Claude datasets, faceted by tutorial/novel
4. Box plot showing run time performance relative to Paper2Agent (baseline = 1.0)
5. Box plot showing cost performance relative to Paper2Agent (baseline = 1.0)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from plotnine import *
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')
import argparse


def load_human_graded_data(data_dir):
    """
    Load all CSV files with 'human_graded.csv' suffix and concatenate them.
    
    Args:
        data_dir (str): Path to the data directory
        
    Returns:
        pd.DataFrame: Concatenated dataframe with unique dataset labels
    """
    data_path = Path(data_dir)
    csv_files = list(data_path.glob("*human_graded.csv"))
    
    if not csv_files:
        raise ValueError(f"No files with 'human_graded.csv' suffix found in {data_dir}")
    
    print(f"Found {len(csv_files)} human-graded CSV files:")
    for file in csv_files:
        print(f"  - {file.name}")
    
    dataframes = []
    
    for file in csv_files:
        # Extract dataset type from filename
        filename = file.stem.replace('_human_graded', '')
        
        # Determine dataset label based on filename
        if 'mcp_responses' in filename:
            dataset_label = 'Paper2Agent'
        elif 'claude_and_repo_only_responses' in filename:
            dataset_label = 'Claude + Repo'
        elif 'biomni_responses' in filename:
            dataset_label = 'Biomni'
        else:
            dataset_label = 'Unknown'
        
        # Load the CSV file
        df = pd.read_csv(file)
        
        # Add dataset label
        df['dataset'] = dataset_label
        
        # Add question type (tutorial vs novel) if not already present
        if 'type' not in df.columns:
            if 'tutorial' in filename:
                df['type'] = 'Tutorial-based benchmark'
            elif 'novel' in filename:
                df['type'] = 'Novel benchmark'
            else:
                df['type'] = 'unknown'
        else:
            # Update existing type values
            df['type'] = df['type'].replace({
                'tutorial': 'Tutorial-based benchmark',
                'novel': 'Novel benchmark'
            })
        
        dataframes.append(df)
        print(f"Loaded {len(df)} rows from {file.name} (Dataset: {dataset_label})")
    
    # Concatenate all dataframes
    combined_df = pd.concat(dataframes, ignore_index=True)
    
    # Set factor levels for consistent ordering
    # Agent order: Paper2Agent, Claude + Repo, Biomni
    agent_levels = ['Paper2Agent', 'Claude + Repo', 'Biomni']
    combined_df['dataset'] = pd.Categorical(combined_df['dataset'], categories=agent_levels, ordered=True)
    
    # Type order: Tutorial-based benchmark, Novel benchmark
    type_levels = ['Tutorial-based benchmark', 'Novel benchmark']
    combined_df['type'] = pd.Categorical(combined_df['type'], categories=type_levels, ordered=True)
    
    print(f"\nCombined dataset contains {len(combined_df)} total rows")
    print(f"Datasets: {combined_df['dataset'].unique()}")
    print(f"Question types: {combined_df['type'].unique()}")
    
    return combined_df

def create_barplot_correct_answers(df, axis_label_size=14, facet_title_size=None, label_text_size=None):
    """
    Create bar plot comparing number of correct answers by dataset, faceted by tutorial/novel.
    
    Args:
        df (pd.DataFrame): Combined dataframe
        axis_label_size (int): Font size for axis labels
        facet_title_size (int): Font size for facet titles (defaults to axis_label_size)
        label_text_size (int): Font size for percentage labels on bars (defaults to axis_label_size)
        
    Returns:
        ggplot: Bar plot
    """
    # Count correct answers (assuming grade column contains correctness info)
    # Assuming grade = 1 means correct, grade = 0 means incorrect
    correct_counts = df.groupby(['dataset', 'type']).apply(
        lambda x: (x['grade'] == 'correct').sum() if 'grade' in x.columns else 0
    ).reset_index(name='correct_count')
    
    total_counts = df.groupby(['dataset', 'type']).size().reset_index(name='total_count')
    
    # Merge to calculate percentages
    plot_data = correct_counts.merge(total_counts, on=['dataset', 'type'])
    plot_data['correct_percentage'] = (plot_data['correct_count'] / plot_data['total_count']) * 100
    plot_data['label_text'] = plot_data['correct_percentage'].round(1).astype(str) + '%'
    
    # Set default facet title size if not provided
    if facet_title_size is None:
        facet_title_size = axis_label_size
    
    # Set default label text size if not provided
    if label_text_size is None:
        label_text_size = axis_label_size
    
    p = (ggplot(plot_data, aes(x='dataset', y='correct_percentage', fill='dataset')) +
         geom_col(alpha=0.8) +
         geom_text(aes(label='label_text'), 
                  position=position_dodge(width=0.9), 
                  va='bottom', size=label_text_size, nudge_y=2) +
         facet_wrap('~type', scales='fixed') +
         labs(title='Percentage of Correct Answers by Agent',
              x='',
              y='Percentage Correct (%)') +
         theme_bw() +
         theme(axis_text_x=element_text(angle=45, hjust=1, size=axis_label_size),
               axis_text_y=element_text(size=axis_label_size),
               axis_title_y=element_text(size=axis_label_size),
               strip_text=element_text(size=facet_title_size),
               plot_title=element_text(size=12, ha='center'),
               legend_position='none') +
         scale_fill_brewer(type='qual', palette='Dark2') +
         ylim(0, 105))

    return p

def create_boxplot_runtime(df, axis_label_size=14, facet_title_size=None):
    """
    Create boxplot comparing run time distributions by dataset, faceted by tutorial/novel.
    
    Args:
        df (pd.DataFrame): Combined dataframe
        axis_label_size (int): Font size for axis labels
        facet_title_size (int): Font size for facet titles (defaults to axis_label_size)
        
    Returns:
        ggplot: Box plot
    """
    # Filter out rows with missing run_time_seconds
    runtime_data = df.dropna(subset=['run_time_seconds'])
    
    # Set default facet title size if not provided
    if facet_title_size is None:
        facet_title_size = axis_label_size
    
    p = (ggplot(runtime_data, aes(x='dataset', y='run_time_seconds', color='dataset')) +
         geom_jitter(alpha=0.6, width=0.3) +
         geom_boxplot(alpha=0.3, width=0.5) +
         facet_wrap('~type', scales='fixed') +
         labs(title='Distribution of Run Times by Agent',
              x='',
              y='Run Time (seconds)') +
         theme_bw() +
         theme(axis_text_x=element_text(angle=45, hjust=1, size=axis_label_size),
               axis_text_y=element_text(size=axis_label_size),
               axis_title_y=element_text(size=axis_label_size),
               strip_text=element_text(size=facet_title_size),
               plot_title=element_text(size=12, ha='center'),
               legend_position='none') +
         scale_y_log10() +
         scale_color_brewer(type='qual', palette='Dark2'))
    
    return p

def create_boxplot_cost(df, axis_label_size=14, facet_title_size=None):
    """
    Create boxplot comparing cost per question between MCP and Claude datasets.
    
    Args:
        df (pd.DataFrame): Combined dataframe
        axis_label_size (int): Font size for axis labels
        facet_title_size (int): Font size for facet titles (defaults to axis_label_size)
        
    Returns:
        ggplot: Box plot
    """
    # Filter for Paper2Agent and Claude + Repo datasets
    cost_data = df[df['dataset'].isin(['Paper2Agent', 'Claude + Repo'])].copy()
    
    # Remove rows with missing cost data
    cost_data = cost_data.dropna(subset=['total_cost_usd'])
    
    if len(cost_data) == 0:
        print("Warning: No cost data available for Paper2Agent and Claude + Repo datasets")
        return None
    
    # Set default facet title size if not provided
    if facet_title_size is None:
        facet_title_size = axis_label_size
    
    # Create a comparison plot
    p = (ggplot(cost_data, aes(x='dataset', y='total_cost_usd', color='dataset')) +
         geom_jitter(alpha=0.6, width=0.3) +
         geom_boxplot(alpha=0.3, width=0.5) +
         facet_wrap('~type', scales='fixed') +
         labs(title='Cost per Question: Paper2Agent vs Claude + Repo',
              x='',
              y='Total Cost (USD)') +
         theme_bw() +
         theme(axis_text_x=element_text(angle=45, hjust=1, size=axis_label_size),
               axis_text_y=element_text(size=axis_label_size),
               axis_title_y=element_text(size=axis_label_size),
               strip_text=element_text(size=facet_title_size),
               plot_title=element_text(size=12, ha='center'),
               legend_position='none') +
         scale_y_log10() +
         scale_color_brewer(type='qual', palette='Dark2'))
    
    return p

def create_relative_runtime_boxplot(df, axis_label_size=14, facet_title_size=None):
    """
    Create boxplot comparing run time distributions relative to Paper2Agent performance.
    Calculates relative performance for each individual query by matching questions across agents.
    
    Args:
        df (pd.DataFrame): Combined dataframe
        axis_label_size (int): Font size for axis labels
        facet_title_size (int): Font size for facet titles (defaults to axis_label_size)
        
    Returns:
        tuple: (ggplot plot, relative performance dataframe)
    """
    # Filter out rows with missing run_time_seconds or question
    runtime_data = df.dropna(subset=['run_time_seconds', 'question']).copy()
    
    if len(runtime_data) == 0:
        print("Warning: No runtime data with questions available for relative comparison")
        return None, None
    
    # Set default facet title size if not provided
    if facet_title_size is None:
        facet_title_size = axis_label_size
    
    # Create baseline dataframe with Paper2Agent runtimes for each question
    baseline_data = runtime_data[
        runtime_data['dataset'] == 'Paper2Agent'
    ][['question', 'type', 'run_time_seconds']].rename(
        columns={'run_time_seconds': 'baseline_runtime'}
    )
    
    if len(baseline_data) == 0:
        print("Warning: No Paper2Agent baseline data available for relative runtime comparison")
        return None, None
    
    # Merge with baseline data to get relative performance
    relative_df = runtime_data.merge(
        baseline_data, 
        on=['question', 'type'], 
        how='inner'
    )
    
    # Calculate relative runtime (Paper2Agent = 1.0)
    relative_df['relative_runtime'] = relative_df['run_time_seconds'] / relative_df['baseline_runtime']
    
    # Keep baseline_runtime column for analysis
    
    # Remove Paper2Agent from the plot since it will always be 1.0 (baseline)
    relative_df = relative_df[relative_df['dataset'] != 'Paper2Agent']
    
    if len(relative_df) == 0:
        print("Warning: No data available for relative runtime comparison")
        return None, None
    
    p = (ggplot(relative_df, aes(x='dataset', y='relative_runtime', color='dataset')) +
         geom_jitter(aes(shape='grade'), alpha=0.6, width=0.3) +
         geom_boxplot(alpha=0.3, width=0.5) +
         geom_hline(yintercept=1.0, linetype='dashed', color='red', alpha=0.7) +
         facet_wrap('~type', scales='fixed') +
         labs(title='Run Time Performance Relative to Paper2Agent (Per Query)',
              x='',
              y='Relative Run Time (Paper2Agent = 1.0)',
              caption='Red dashed line indicates Paper2Agent baseline (1.0)\nValues > 1.0 = slower than Paper2Agent for same query\nPoint shapes indicate answer correctness') +
         theme_bw() +
         theme(axis_text_x=element_text(angle=45, hjust=1, size=axis_label_size),
               axis_text_y=element_text(size=axis_label_size),
               axis_title_y=element_text(size=axis_label_size),
               strip_text=element_text(size=facet_title_size),
               plot_title=element_text(size=12, ha='center'),
               legend_position='right',
               plot_caption=element_text(size=9, ha='left')) +
         scale_y_log10() +
         scale_color_brewer(type='qual', palette='Dark2', guide=None) +
         scale_shape_manual(values={'correct': 'o', 'incorrect': 'x'}, name='Response grade'))
    
    return p, relative_df

def create_relative_cost_boxplot(df, axis_label_size=14, facet_title_size=None):
    """
    Create boxplot comparing cost per question relative to Paper2Agent performance.
    Calculates relative performance for each individual query by matching questions across agents.
    
    Args:
        df (pd.DataFrame): Combined dataframe
        axis_label_size (int): Font size for axis labels
        facet_title_size (int): Font size for facet titles (defaults to axis_label_size)
        
    Returns:
        tuple: (ggplot plot, relative performance dataframe)
    """
    # Filter for Paper2Agent and Claude + Repo datasets
    cost_data = df[df['dataset'].isin(['Paper2Agent', 'Claude + Repo'])].copy()
    
    # Remove rows with missing cost data or question
    cost_data = cost_data.dropna(subset=['total_cost_usd', 'question'])
    
    if len(cost_data) == 0:
        print("Warning: No cost data with questions available for relative comparison")
        return None, None
    
    # Set default facet title size if not provided
    if facet_title_size is None:
        facet_title_size = axis_label_size
    
    # Create baseline dataframe with Paper2Agent costs for each question
    baseline_data = cost_data[
        cost_data['dataset'] == 'Paper2Agent'
    ][['question', 'type', 'total_cost_usd']].rename(
        columns={'total_cost_usd': 'baseline_cost'}
    )
    
    if len(baseline_data) == 0:
        print("Warning: No Paper2Agent baseline data available for relative cost comparison")
        return None, None
    
    # Merge with baseline data to get relative performance
    relative_df = cost_data.merge(
        baseline_data, 
        on=['question', 'type'], 
        how='inner'
    )
    
    # Calculate relative cost (Paper2Agent = 1.0)
    relative_df['relative_cost'] = relative_df['total_cost_usd'] / relative_df['baseline_cost']
    
    # Keep baseline_cost column for analysis
    
    # Remove Paper2Agent from the plot since it will always be 1.0 (baseline)
    relative_df = relative_df[relative_df['dataset'] != 'Paper2Agent']
    
    if len(relative_df) == 0:
        print("Warning: No data available for relative cost comparison")
        return None, None
    
    p = (ggplot(relative_df, aes(x='dataset', y='relative_cost', color='dataset')) +
         geom_jitter(aes(shape='grade'), alpha=0.6, width=0.3) +
         geom_boxplot(alpha=0.3, width=0.5) +
         geom_hline(yintercept=1.0, linetype='dashed', color='red', alpha=0.7) +
         facet_wrap('~type', scales='fixed') +
         labs(title='Cost Performance Relative to Paper2Agent (Per Query)',
              x='',
              y='Relative Cost (Paper2Agent = 1.0)',
              caption='Red dashed line indicates Paper2Agent baseline (1.0)\nValues > 1.0 = more expensive than Paper2Agent for same query\nPoint shapes indicate answer correctness') +
         theme_bw() +
         theme(axis_text_x=element_text(angle=45, hjust=1, size=axis_label_size),
               axis_text_y=element_text(size=axis_label_size),
               axis_title_y=element_text(size=axis_label_size),
               strip_text=element_text(size=facet_title_size),
               plot_title=element_text(size=12, ha='center'),
               legend_position='right',
               plot_caption=element_text(size=9, ha='left')) +
         scale_y_log10() +
         scale_color_brewer(type='qual', palette='Dark2', guide=None) +
         scale_shape_manual(values={'correct': 'o', 'incorrect': 'x'}, name='Response grade'))
    
    return p, relative_df

def main():
    """Main function to run the analysis."""
    # Set up paths
    script_dir = Path(__file__).parent
    data_dir = script_dir.parent / "data"  # Go up one level from scripts to benchmarking, then to data
    
    # CLI arguments
    parser = argparse.ArgumentParser(description="Analyze human-graded AlphaGenome benchmarking data")
    args = parser.parse_args()
    
    # Generate date suffix for output files
    date_suffix = datetime.now().strftime("%Y-%m-%d")
    
    print("Loading human-graded CSV files...")
    df = load_human_graded_data(data_dir)
    
    print("\nCreating visualizations...")
    
    # Set font size for axis labels
    axis_label_size = 16
    facet_title_size = axis_label_size  # Match facet title size to axis label size
    label_text_size = axis_label_size   # Match label text size to axis label size
    
    # Create plots
    print("1. Creating bar plot for correct answers...")
    bar_plot = create_barplot_correct_answers(df, axis_label_size, facet_title_size, label_text_size)
    barplot_filename = f"correct_answers_barplot_{date_suffix}.png"
    bar_plot.save(data_dir / barplot_filename, dpi=300, width=10, height=6)
    print(f"   Saved: {data_dir / barplot_filename}")
    
    print("2. Creating boxplot for run times...")
    boxplot_runtime = create_boxplot_runtime(df, axis_label_size, facet_title_size)
    boxplot_filename = f"runtime_boxplot_{date_suffix}.png"
    boxplot_runtime.save(data_dir / boxplot_filename, dpi=300, width=10, height=6)
    print(f"   Saved: {data_dir / boxplot_filename}")
    
    print("3. Creating boxplot for costs...")
    boxplot_cost = create_boxplot_cost(df, axis_label_size, facet_title_size)
    if boxplot_cost is not None:
        cost_filename = f"cost_boxplot_{date_suffix}.png"
        boxplot_cost.save(data_dir / cost_filename, dpi=300, width=10, height=6)
        print(f"   Saved: {data_dir / cost_filename}")
    else:
        print("   Skipped: No cost data available")
    
    print("4. Creating relative runtime boxplot...")
    relative_runtime_plot, relative_runtime_data = create_relative_runtime_boxplot(df, axis_label_size, facet_title_size)
    if relative_runtime_plot is not None:
        relative_runtime_filename = f"relative_runtime_boxplot_{date_suffix}.png"
        relative_runtime_plot.save(data_dir / relative_runtime_filename, dpi=300, width=10, height=6)
        print(f"   Saved: {data_dir / relative_runtime_filename}")
    else:
        print("   Skipped: No runtime data available for relative comparison")
    
    print("5. Creating relative cost boxplot...")
    relative_cost_plot, relative_cost_data = create_relative_cost_boxplot(df, axis_label_size, facet_title_size)
    if relative_cost_plot is not None:
        relative_cost_filename = f"relative_cost_boxplot_{date_suffix}.png"
        relative_cost_plot.save(data_dir / relative_cost_filename, dpi=300, width=10, height=6)
        print(f"   Saved: {data_dir / relative_cost_filename}")
    else:
        print("   Skipped: No cost data available for relative comparison")
    
    print("\nAnalysis complete!")
    
    # Print summary statistics
    print("\nSummary Statistics:")
    print("=" * 50)
    
    # Grade distribution
    if 'grade' in df.columns:
        print("\nGrade Distribution:")
        grade_summary = df.groupby(['dataset', 'type', 'grade']).size().unstack(fill_value=0)
        print(grade_summary)
    
    # Runtime statistics
    if 'run_time_seconds' in df.columns:
        print("\nRuntime Statistics (seconds):")
        runtime_summary = df.groupby(['dataset', 'type'])['run_time_seconds'].agg(['count', 'mean', 'median', 'std', 'min', 'max']).round(2)
        print(runtime_summary)
    
    # Cost statistics
    if 'total_cost_usd' in df.columns:
        print("\nCost Statistics (USD):")
        cost_summary = df.groupby(['dataset', 'type'])['total_cost_usd'].agg(['count', 'mean', 'median', 'std', 'min', 'max']).round(4)
        print(cost_summary)
    
    # Relative performance statistics
    print("\nRelative Performance Statistics:")
    print("=" * 50)
    
    # Relative runtime statistics
    if relative_runtime_data is not None and len(relative_runtime_data) > 0:
        print("\nRelative Runtime Performance (Paper2Agent = 1.0):")
        relative_runtime_summary = relative_runtime_data.groupby(['dataset', 'type'])['relative_runtime'].agg(['count', 'mean', 'median', 'std', 'min', 'max']).round(3)
        print(relative_runtime_summary)
    else:
        print("\nRelative Runtime Performance: No data available")
    
    # Relative cost statistics
    if relative_cost_data is not None and len(relative_cost_data) > 0:
        print("\nRelative Cost Performance (Paper2Agent = 1.0):")
        relative_cost_summary = relative_cost_data.groupby(['dataset', 'type'])['relative_cost'].agg(['count', 'mean', 'median', 'std', 'min', 'max']).round(3)
        print(relative_cost_summary)
    else:
        print("\nRelative Cost Performance: No data available")
    
    # Extreme performance analysis
    print("\nExtreme Performance Analysis:")
    print("=" * 50)
    
    # Find queries where Paper2Agent is >60x faster than Claude + Repo
    if relative_runtime_data is not None and len(relative_runtime_data) > 0:
        print("\nQueries where Paper2Agent performed >60x faster than Claude + Repo:")
        
        # Filter for Claude + Repo data with relative runtime > 60 (meaning Paper2Agent was >60x faster)
        extreme_cases = relative_runtime_data[
            (relative_runtime_data['dataset'] == 'Claude + Repo') & 
            (relative_runtime_data['relative_runtime'] > 60)
        ]
        
        if len(extreme_cases) > 0:
            print(f"Found {len(extreme_cases)} extreme cases:")
            print("-" * 80)
            
            # Sort by relative runtime (highest first)
            extreme_cases_sorted = extreme_cases.sort_values('relative_runtime', ascending=False)
            
            for idx, row in extreme_cases_sorted.iterrows():
                print(f"\nQuestion: {row['question']}")
                print(f"Benchmark Type: {row['type']}")
                print(f"Relative Performance: {row['relative_runtime']:.1f}x (Paper2Agent faster)")
                print(f"Paper2Agent Runtime: {row['baseline_runtime']:.2f} seconds")
                print(f"Claude + Repo Runtime: {row['run_time_seconds']:.2f} seconds")
                print(f"Grade: {row['grade']}")
                
                # Print Claude's full response JSON if available
                if 'full_agent_response_json' in row and pd.notna(row['full_agent_response_json']):
                    print(f"\nClaude + Repo's Full Response JSON:")
                    print("-" * 40)
                    print(row['full_agent_response_json'])
                    print("-" * 40)
                else:
                    print("\nClaude + Repo's Full Response JSON: Not available")
                
                print("-" * 80)
        else:
            print("No cases found where Paper2Agent was >60x faster than Claude + Repo")
    else:
        print("\nExtreme Performance Analysis: No relative runtime data available")

if __name__ == "__main__":
    main()
