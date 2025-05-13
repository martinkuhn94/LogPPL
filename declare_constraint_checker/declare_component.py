import pprint
import ast
import os
import pandas as pd
from typing import Any
import tempfile

import pm4py
from pnml_to_webppl.functions.create_log import generate_event_log


def save_declare_model(model_dict: dict, filepath: str):
    """
    Saves a dictionary (Declare model) to a text file as a Python literal.

    Args:
        model_dict: The dictionary representing the Declare model.
        filepath: The path to the file where the model should be saved
                  (e.g., 'my_model.decl' or 'my_model.py').
    Returns:
        True if saving was successful, False otherwise.
    """
    if not isinstance(model_dict, dict):
        print("Error: Input 'model_dict' must be a dictionary.")
        return False
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            pprint.pprint(model_dict, stream=f, indent=2, width=120, sort_dicts=False)
        print(f"Declare model successfully saved to: {filepath}")
        return True
    except IOError as e:
        print(f"Error: Could not write to file '{filepath}': {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during saving: {e}")
        return False


def load_declare_model(filepath: str) -> dict | None:
    """
    Loads a dictionary (Declare model) from a text file saved as Python literal.

    Args:
        filepath: The path to the file containing the saved model.

    Returns:
        The loaded dictionary, or None if loading fails.
    """
    if not os.path.exists(filepath):
        print(f"Error: File not found at '{filepath}'")
        return None

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            file_content = f.read()
        model_dict = ast.literal_eval(file_content)
        if not isinstance(model_dict, dict):
            print(f"Error: Content loaded from '{filepath}' is not a dictionary.")
            return None

        print(f"Declare model successfully loaded from: {filepath}")
        return model_dict
    except FileNotFoundError:
        print(f"Error: File not found at '{filepath}'")
        return None
    except (SyntaxError, ValueError) as e:
        print(f"Error parsing file '{filepath}'. It might not contain a valid Python dictionary literal.")
        print(f"Parser Error: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during loading: {e}")
        return None


def check_declare_compliance(event_log: pd.DataFrame, declare_model: Any, min_fitness: float = 1.0) -> pd.DataFrame:
    """
    Checks compliance of a pandas DataFrame event log against a DECLARE model
    and returns conforming traces with their fitness.

    Args:
        event_log: The event log as a pandas DataFrame. Expected columns include
                   'case:concept:name' (or similar case identifier) and activity names.
        declare_model: The DECLARE model object (e.g., pm4py DeclareModel).
        min_fitness: The minimum fitness value a trace must have to be
                     considered conforming. Defaults to 1.0.

    Returns:
        A pandas DataFrame containing the conforming traces enriched with
        their calculated trace fitness.

    Raises:
        ValueError: If event_log or declare_model are None, or if
                    the conformance checking fails or returns an unexpected
                    format.
        KeyError: If expected column names are not found in the dataframes.
        TypeError: If event_log is not a pandas DataFrame or declare_model
                   is not of the expected type.
    """
    if event_log is None or declare_model is None:
        raise ValueError("event_log and declare_model cannot be None.")

    if not isinstance(event_log, pd.DataFrame):
        raise TypeError("event_log must be a pandas DataFrame.")

    try:
        conf_result = pm4py.conformance_declare(
            event_log, declare_model, return_diagnostics_dataframe=True
        )
    except Exception as e:
        raise ValueError(f"DECLARE conformance checking failed: {e}")

    if not isinstance(conf_result, pd.DataFrame) or conf_result.empty:
        raise ValueError("DECLARE conformance checking did not return a valid DataFrame.")

    try:
        fitness_column_mean = conf_result.iloc[:, 3].mean()
        print(f"Fitness: {fitness_column_mean}")

        fitness_col_name = str(conf_result.columns[3])
    except IndexError:
        raise KeyError("Could not find the expected fitness column (4th column) in conformance results.")
    except Exception as e:
        raise ValueError(f"Failed to process conformance results: {e}")

    conformance_result_filtered = conf_result[conf_result.iloc[:, 3] >= min_fitness].copy()

    try:
        conformance_fitness_info = conformance_result_filtered[['case_id', fitness_col_name]].copy()
        conformance_fitness_info.rename(columns={fitness_col_name: 'trace_fitness'}, inplace=True)
    except KeyError as e:
        raise KeyError(f"Expected column not found in conformance filtered results: {e}")

    try:
        case_name_col = 'case:concept:name'
        if case_name_col not in event_log.columns:
            case_cols = [col for col in event_log.columns if 'case:' in col and 'concept:name' in col]
            if not case_cols:
                raise KeyError(
                    f"Could not find case name column in event log DataFrame. Expected '{case_name_col}' or similar.")
            case_name_col = case_cols[0]

        conforming_traces_df = event_log[
            event_log[case_name_col].isin(conformance_fitness_info['case_id'])].copy()

    except KeyError as e:
        raise KeyError(f"Expected column not found in event log DataFrame or conformance info: {e}")

    conforming_traces_with_fitness = pd.merge(
        conforming_traces_df,
        conformance_fitness_info,
        how='left',
        left_on=case_name_col,
        right_on='case_id'
    )

    if 'case_id' in conforming_traces_with_fitness.columns:
        conforming_traces_with_fitness.drop(columns=['case_id'], inplace=True)

    return conforming_traces_with_fitness


def generate_declare_checked_log(path_webppl_file: str, path_webppl_installation: str, declare_model: Any, samples: int,
                                 min_fitness: float = 1.0, tries=10):
    """
    Generates an event log using a WebPPL script, checks its compliance
    against a DECLARE model, filters conforming traces, and returns the
    result as a pm4py EventLog. Writes the generated XES string to a
    temporary file for pm4py to read.

    Args:
        path_webppl_file: Path to the WebPPL script file.
        path_webppl_installation: Path to the WebPPL installation.
        declare_model: The DECLARE model object (e.g., pm4py DeclareModel).
        samples: The number of samples/traces to generate.
        min_fitness: The minimum fitness value a trace must have to be
                     considered conforming. Defaults to 1.0.
        tries: Number of time the function should retry to generate in case of an empty event log (default 10).

    Returns:
        A pm4py EventLog object containing the conforming traces with fitness,
        or None if an error occurs during log generation or processing.

    """
    samples = int(samples)
    tries = int(tries)
    temp_xes_file = None

    try:
        print("Calling generate_event_log...")
        xes_string = generate_event_log(path_webppl_installation, path_webppl_file)
        print("generate_event_log finished.")

        with tempfile.NamedTemporaryFile(mode='w+', suffix='.xes', delete=False) as tmp_file:
            tmp_file.write(xes_string)
            temp_xes_file = tmp_file.name

        generated_log = pm4py.read_xes(temp_xes_file)
        print(f"Xes event log read from temporary file: {temp_xes_file}")

        generated_df = pm4py.convert_to_dataframe(generated_log)
        conforming_traces_df = check_declare_compliance(generated_df, declare_model, min_fitness)
        final_event_log = pm4py.convert_to_event_log(conforming_traces_df)

        print("DECLARE compliance checking and filtering finished.")

    except Exception as e:
        print(f"Error during log generation or processing: {e}")
        return None
    finally:
        if temp_xes_file and os.path.exists(temp_xes_file):
            os.remove(temp_xes_file)
            print(f"Temporary file deleted: {temp_xes_file}")

    return final_event_log
