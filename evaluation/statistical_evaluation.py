from datetime import datetime
import os
import pandas as pd
import pm4py
import matplotlib.pyplot as plt
import seaborn as sns

from sdmetrics.single_column import KSComplement
from process_mining_eval_functions import (calculate_throughput_time,
                                           calculate_trace_length_distribution, calc_hellinger,
                                           compare_logs,
                                           save_descriptive_stats_to_yaml,
                                           create_process_metrics_df,
                                           calculate_petri_nets, save_petri_nets,
                                           calculate_earth_mover_distance
                                           )

sns.set_theme(style="whitegrid")


def plot_event_distribution(df_real: pd.DataFrame, df_declare_checked: pd.DataFrame, save_path: str):
    """Plots the relative distribution of event names for real and declare_checked logs."""
    real_counts = df_real['concept:name'].value_counts(normalize=True).reset_index()
    real_counts.columns = ['Activity', 'Proportion']
    real_counts['Log'] = 'Real'

    declare_checked_counts = df_declare_checked['concept:name'].value_counts(normalize=True).reset_index()
    declare_checked_counts.columns = ['Activity', 'Proportion']
    declare_checked_counts['Log'] = 'Declare Checked'

    combined_counts = pd.concat([real_counts, declare_checked_counts])

    plt.figure(figsize=(12, 6))
    sns.barplot(data=combined_counts, x='Activity', y='Proportion', hue='Log', palette='viridis')
    plt.title('Relative Event Distribution')
    plt.xlabel('Activity')
    plt.ylabel('Relative Frequency (Proportion)')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()


def plot_numerical_attribute_distribution(df_real_col: pd.Series, df_declare_checked_col: pd.Series, column_name: str,
                                          save_path: str):
    """Plots the distribution of a numerical attribute for real and declare_checked logs."""
    plt.figure(figsize=(8, 5))
    sns.histplot(df_real_col.dropna(), color='skyblue', label='Real', kde=True, stat='density', common_norm=False)
    sns.histplot(df_declare_checked_col.dropna(), color='lightcoral', label='Declare Checked', kde=True, stat='density',
                 common_norm=False)
    plt.title(f'Distribution of Numerical Attribute: {column_name}')
    plt.xlabel(column_name)
    plt.ylabel('Density')
    plt.legend()
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()


def plot_categorical_attribute_distribution(df_real_col: pd.Series, df_declare_checked_col: pd.Series, column_name: str,
                                            save_path: str):
    """Plots the distribution of a categorical attribute for real and declare_checked logs."""
    real_counts = df_real_col.value_counts(normalize=True).reset_index()
    real_counts.columns = ['Category', 'Proportion']
    real_counts['Log'] = 'Real'

    declare_checked_counts = df_declare_checked_col.value_counts(normalize=True).reset_index()
    declare_checked_counts.columns = ['Category', 'Proportion']
    declare_checked_counts['Log'] = 'Declare Checked'

    combined_counts = pd.concat([real_counts, declare_checked_counts])

    plt.figure(figsize=(10, 6))
    sns.barplot(data=combined_counts, x='Category', y='Proportion', hue='Log', palette='viridis')
    plt.title(f'Relative Distribution of Categorical Attribute: {column_name}')
    plt.xlabel('Category')
    plt.ylabel('Relative Frequency (Proportion)')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()


log_name = "simple_auction"

# Read Event Log (Original)
log_filename = "simple_auction_org.xes"
real_event_log = pm4py.read_xes(log_filename)

# Read Declare Checked Event Log
declare_checked_log_filename = "simple_auction_declare_checked.xes"
declare_checked_event_log = pm4py.read_xes(declare_checked_log_filename)

print(f"Loaded real event log with {len(real_event_log)} traces.")
print(f"Loaded declare_checked event log with {len(declare_checked_event_log)} traces.")  # Updated print

# Convert logs to dataframes
df_real = pm4py.convert_to_dataframe(real_event_log)
df_declare_checked = pm4py.convert_to_dataframe(declare_checked_event_log)  # Updated variable name

# Pre-processing
# Dropping non-attribute columns for attribute evaluation
attribute_cols_to_drop = ['time:timestamp', 'case:concept:name', 'concept:name']
df_real_for_attr = df_real.drop(columns=[col for col in attribute_cols_to_drop if col in df_real.columns], axis=1)
df_declare_checked_for_attr = df_declare_checked.drop(
    columns=[col for col in attribute_cols_to_drop if col in df_declare_checked.columns],
    axis=1)  # Updated variable name

# Make dataframes with only numeric/categorical columns
df_real_numeric = df_real_for_attr.select_dtypes(include=['number'])
df_declare_checked_numeric = df_declare_checked_for_attr.select_dtypes(include=['number'])  # Updated variable name
df_real_categorical = df_real_for_attr.select_dtypes(include=['object', 'category'])
df_declare_checked_categorical = df_declare_checked_for_attr.select_dtypes(
    include=['object', 'category'])  # Updated variable name

# Attribute Perspective Evaluation
results = {}
average_ks = []
for col in df_real_numeric.columns:
    # Compare only columns present in both dataframes
    if col in df_declare_checked_numeric.columns and not (
            df_real_numeric[col].isna().all() or df_declare_checked_numeric[col].isna().all()):  # Updated variable name
        data_real = df_real_numeric[col].dropna()
        data_declare_checked = df_declare_checked_numeric[col].dropna()  # Updated variable name
        ks_statistic = KSComplement.compute(real_data=data_real,
                                            synthetic_data=data_declare_checked)  # sdmetrics still uses synthetic_data arg name
        average_ks.append(ks_statistic)

average_tv = []
for col in df_real_categorical.columns:
    # Compare only columns present in both dataframes
    if col in df_declare_checked_categorical.columns and not (
            df_real_categorical[col].isna().all() or df_declare_checked_categorical[col].isna().all()):
        data_real = df_real_categorical[col].dropna().astype(str)
        data_declare_checked = df_declare_checked_categorical[col].dropna().astype(str)
        tv_statistic = 1 - calc_hellinger(data_real, data_declare_checked)
        average_tv.append(tv_statistic)

results["average_ks"] = sum(average_ks) / len(average_ks) if average_ks else None
results["average_tv"] = sum(average_tv) / len(average_tv) if average_tv else None

# Event-based metrics
data_real_events = df_real["concept:name"].dropna()
data_declare_checked_events = df_declare_checked["concept:name"].dropna()
results["tv_statistic_event_distribution"] = 1 - calc_hellinger(data_real_events,
                                                                data_declare_checked_events)

# Trace length distribution
trace_length_real = calculate_trace_length_distribution(real_event_log)
trace_length_declare_checked = calculate_trace_length_distribution(declare_checked_event_log)
results["hellinger_distance_trace_length_distribution"] = 1 - calc_hellinger(trace_length_real,
                                                                             trace_length_declare_checked,
                                                                             input_type="distribution")

# Throughput time distribution
throughput_time_real = calculate_throughput_time(real_event_log)
throughput_time_declare_checked = calculate_throughput_time(declare_checked_event_log)
results["ks_statistic_throughput_time_distribution"] = KSComplement.compute(
    real_data=throughput_time_real,
    synthetic_data=throughput_time_declare_checked
)

variants_real = pm4py.get_variants(
    real_event_log,
    activity_key='concept:name',
    case_id_key='case:concept:name',
    timestamp_key='time:timestamp'
)

variants_declare_checked = pm4py.get_variants(
    declare_checked_event_log,
    activity_key='concept:name',
    case_id_key='case:concept:name',
    timestamp_key='time:timestamp'
)

# Add number of trace variants to results
results["num_trace_variants_real"] = len(variants_real)
results["num_trace_variants_declare_checked"] = len(variants_declare_checked)

print(f"Number of real trace variants: {results['num_trace_variants_real']}")
print(f"Number of declare_checked trace variants: {results['num_trace_variants_declare_checked']}")

# Calculate earth movers distance
try:

    emd = calculate_earth_mover_distance(real_event_log, declare_checked_event_log)
    results['earth_mover_distance'] = emd
except Exception as e:
    print(f"Error calculating Earth Mover's Distance: {e}")
    results['earth_mover_distance'] = float('nan')

# Process Perspective Metrics
try:
    process_metrics = compare_logs(real_event_log, declare_checked_event_log, threshold=0.25)
    df_regular, df_transposed = create_process_metrics_df(process_metrics)
except Exception as e:
    print(f"Error calculating process metrics: {e}")
    process_metrics = None
    df_transposed = pd.DataFrame()

# Create DataFrame with results (including trace variants)
df_results = pd.DataFrame([results])

# Create timestamp
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

results_dir = 'evaluation_results'
if not os.path.exists(results_dir):
    os.makedirs(results_dir)

eval_dir = os.path.join(results_dir, f'{log_name}_{timestamp}')
if not os.path.exists(eval_dir):
    os.makedirs(eval_dir)

# Event Distribution Figure
event_dist_path = os.path.join(eval_dir, 'event_distribution.png')
# Ensure 'concept:name' column exists before plotting
if 'concept:name' in df_real.columns and 'concept:name' in df_declare_checked.columns:
    try:
        plot_event_distribution(df_real, df_declare_checked, event_dist_path)
        print(f"Saved event distribution plot to {event_dist_path}")
    except Exception as e:
        print(f"Error generating event distribution plot: {e}")
else:
    print("Skipping event distribution plot: 'concept:name' column not found.")

# Numerical Attribute Figures
numeric_plots_dir = os.path.join(eval_dir, 'numerical_attribute_plots')
if not os.path.exists(numeric_plots_dir):
    os.makedirs(numeric_plots_dir)

for col in df_real_numeric.columns:
    if col in df_declare_checked_numeric.columns:
        plot_path = os.path.join(numeric_plots_dir, f'{col}_distribution.png')
        try:
            plot_numerical_attribute_distribution(df_real_numeric[col], df_declare_checked_numeric[col], col,
                                                  plot_path)
            print(f"Saved numerical attribute plot for '{col}' to {plot_path}")
        except Exception as e:
            print(f"Error generating numerical attribute plot for '{col}': {e}")
    else:
        print(f"Skipping numerical attribute plot for '{col}': Column not found in declare_checked log.")

# Categorical Attribute Figures
categorical_plots_dir = os.path.join(eval_dir, 'categorical_attribute_plots')
if not os.path.exists(categorical_plots_dir):
    os.makedirs(categorical_plots_dir)

for col in df_real_categorical.columns:
    if col in df_declare_checked_categorical.columns:
        plot_path = os.path.join(categorical_plots_dir, f'{col}_distribution.png')
        try:
            plot_categorical_attribute_distribution(df_real_categorical[col], df_declare_checked_categorical[col], col,
                                                    plot_path)
            print(f"Saved categorical attribute plot for '{col}' to {plot_path}")
        except Exception as e:
            print(f"Error generating categorical attribute plot for '{col}': {e}")
    else:
        print(f"Skipping categorical attribute plot for '{col}': Column not found in declare_checked log.")

# Save descriptive stats YAML files
yaml_path_real = os.path.join(eval_dir, 'descriptive_stats_real.yaml')
yaml_path_declare_checked = os.path.join(eval_dir, 'descriptive_stats_declare_checked.yaml')
try:
    save_descriptive_stats_to_yaml(df_real, yaml_path_real)
    save_descriptive_stats_to_yaml(df_declare_checked, yaml_path_declare_checked)
except Exception as e:
    print(f"Error saving descriptive stats YAMLs: {e}")

# Save process metrics Excel file
process_metrics_path = os.path.join(eval_dir, 'process_metrics.xlsx')
if not df_transposed.empty:
    try:
        df_transposed.to_excel(process_metrics_path, index=False)
    except Exception as e:
        print(f"Error saving process metrics Excel: {e}")
else:
    print("Process metrics DataFrame is empty, not saving process_metrics.xlsx")

# Save Petri Nets
try:
    petri_net_dict_real = calculate_petri_nets(real_event_log, threshold=0.25)
    petri_net_dict_declare_checked = calculate_petri_nets(declare_checked_event_log,
                                                          threshold=0.25)

    # Save both real and declare_checked Petri nets
    save_petri_nets(petri_net_dict_real, eval_dir, f'{log_name}_org')
    save_petri_nets(petri_net_dict_declare_checked, eval_dir, f'{log_name}_declare_checked')
except Exception as e:
    print(f"Error calculating or saving Petri nets: {e}")

# Save general metrics Excel file
metrics_path = os.path.join(eval_dir, 'evaluation_metrics.xlsx')
try:
    df_results.to_excel(metrics_path, index=False)
except Exception as e:
    print(f"Error saving evaluation metrics Excel: {e}")
