import os
import sys
from io import StringIO
import json

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from app.utility import (transform_to_svg, get_events, get_guards, extract_prime_variables, transform_advanced_query,
                         parse_string_to_dict, generate_error_message, escape_single_quote)
from pnml_to_webppl.converter import convert_dpn_to_webPPL
from pnml_to_webppl.functions.create_log import generate_event_log, find_npm_global_path
from pnml_to_webppl.dpn import DPN

app = Flask(__name__, template_folder='app/templates', static_folder='app/static')
app.secret_key = 'your_secret_key'
app.jinja_env.filters['escape_single_quote'] = escape_single_quote


@app.route('/')
def index():
    session['upload_complete'] = False
    session['configuration_complete'] = False
    session['results_complete'] = False
    return render_template('index.html')


@app.route('/upload_page')
def upload_page():
    return render_template('upload.html')


@app.route('/dpn_visualizer')
def dpn_visualizer():
    if not session.get('upload_complete'):
        return redirect(url_for('upload_page'))

    filename = session.get('uploaded_filename', '')
    svg_filename = filename.split('.')[0] + '.svg'
    return render_template('dpn_visualizer.html', filename=filename, svg_filename=svg_filename)


@app.route('/configuration')
def configuration():
    filename = session.get('uploaded_filename', '')
    distributions = {}

    dpn = DPN(os.path.join('app/static/data/dpn', filename), distributions)
    with open('app/static/distribution_configurations/available_distributions.json') as f:
        distribution_configuration = json.load(f)
    with open('app/static/distribution_configurations/default_distribution.json') as f:
        default_distributions = json.load(f)

    events = get_events(dpn.net)
    guards_test = get_guards(dpn.net)
    variables_dict = dpn.variable_information

    prime_variables_dict = extract_prime_variables(guards_test, variables_dict)
    nested_dict_with_relevant_variables = {
        key: {
            'event': events[key],
            'guard': guards_test[key],
            'relevant_variables': prime_variables_dict[key]
        }
        for key in prime_variables_dict
    }

    variables_dict = {key + "'": value for key, value in variables_dict.items()}
    nested_dict_with_relevant_variables['variables'] = variables_dict

    return render_template('configuration.html', filename=filename,
                           nested_dict=nested_dict_with_relevant_variables, events=events,
                           distributions=distribution_configuration, default_distributions=default_distributions)


@app.route('/generate', methods=['POST'])
def generate():
    input_string = ""
    for key, value in request.form.items():
        input_string += f"{key}: {value}\n"

    filename = session.get('uploaded_filename', '')
    distributions = {}
    dpn = DPN(os.path.join('app/static/data/dpn', filename), distributions)
    distributions = parse_string_to_dict(input_string, dpn)

    simulation_query = ""
    simulation_query_display = ""

    query_type = request.form.get('queryToggle')
    specific_event = request.form.get('specificEvent')
    advanced_query = request.form.get('queryComments')
    simulator_loops = request.form.get('simulatorLoops')
    num_samples = request.form.get('numSamples')

    if query_type == 'event':
        simulation_query = f'(globalStore.{specific_event} > 0)'
        events = get_events(dpn.net)
        specific_event_display = events[specific_event]
        simulation_query_display = f'({specific_event_display} > 0)'
    if query_type == 'advanced':
        simulation_query = transform_advanced_query(dpn, advanced_query)
        simulation_query_display = f'({advanced_query})'
    if query_type == 'finalMarking':
        simulation_query = "final_marking"
        simulation_query_display = "Final Marking is reached"

    session['distributions'] = distributions
    session['simulation_query_display'] = simulation_query_display

    return redirect(
        url_for('loading', filename=filename, simulation_query=simulation_query, simulator_loops=simulator_loops,
                num_samples=num_samples))


@app.route('/loading')
def loading():
    filename = request.args.get('filename')
    simulation_query = request.args.get('simulation_query')
    simulator_loops = request.args.get('simulator_loops')
    num_samples = request.args.get('num_samples')

    return redirect(
        url_for('process', filename=filename, simulation_query=simulation_query, simulator_loops=simulator_loops,
                num_samples=num_samples))


@app.route('/process/<filename>/<simulation_query>/<simulator_loops>/<num_samples>')
def process(filename, simulation_query, simulator_loops, num_samples):
    distributions = session.get('distributions', {})

    path_pnml = os.path.abspath(f'app/static/data/dpn/{filename}')
    path_to_webppl_engine = find_npm_global_path()
    webPPL_file = convert_dpn_to_webPPL(path_pnml, verbose=True, simulation_steps=simulator_loops,
                                        sample_size=num_samples, simulation_query=simulation_query,
                                        distributions=distributions)

    directory = os.path.join(os.getcwd(), 'app', 'static', 'data', 'webppl_files')
    if not os.path.exists(directory):
        os.makedirs(directory)

    path_to_webppl_file = os.path.join(directory, f'{filename.split(".")[0]}.wppl')
    full_path_to_webppl_file = os.path.abspath(path_to_webppl_file)

    with open(full_path_to_webppl_file, 'w') as f:
        f.write(webPPL_file)

    captured_output = StringIO()

    # Redirect sys.stdout to the StringIO object
    output_temp = sys.stdout
    sys.stdout = captured_output

    synthetic_log = generate_event_log(path_to_webppl_engine, full_path_to_webppl_file)
    sys.stdout = output_temp
    directory = os.path.join(os.getcwd(), 'app', 'static', 'data', 'xes_files')

    if not os.path.exists(directory):
        os.makedirs(directory)

    path_to_xes = os.path.join(directory, f'{filename.split(".")[0]}.xes')

    with open(path_to_xes, 'w') as f:
        f.write(synthetic_log)

    # Reset sys.stdout to its original value (console)
    sys.stdout = sys.__stdout__
    captured_output_str = captured_output.getvalue()
    captured_output.close()
    json_objects = []

    for line in captured_output_str.splitlines():
        if line.startswith('{"dist":{"probs'):
            try:
                json_obj = json.loads(line)
                json_objects.append(json_obj)
            except json.JSONDecodeError:
                pass

    if not json_objects:
        print("syntax_error occured")
        error_message_query = generate_error_message(session.get('simulation_query_display', ''), simulation_query,
                                                     filename)
        session['error_message'] = error_message_query
        return redirect(url_for('error_message'))

    directory = os.path.join(os.getcwd(), 'app', 'static', 'data', 'query_result')

    if not os.path.exists(directory):
        os.makedirs(directory)

    path_to_resultjson = os.path.join(directory, f'{filename.split(".")[0]}.json')

    with open(path_to_resultjson, "w") as file:
        json.dump(json_objects, file, indent=4)

    session['query_result'] = json_objects
    session['configuration_complete'] = True

    return redirect(url_for('view_statistics'))


@app.route('/view_statistics')
def view_statistics():
    if not session.get('upload_complete') or not session.get('configuration_complete'):
        return redirect(url_for('upload_page'))

    query_result = session.get('query_result')
    simulation_query_display = session.get('simulation_query_display')

    return render_template('view_statistics.html', query_result=query_result, simulation_query=simulation_query_display)


@app.route('/upload_dpn', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return redirect(request.url)

    file = request.files['file']
    if file.filename == '':
        return redirect(request.url)

    if not file.filename.lower().endswith('.pnml'):
        return "Error: Only .pnml files are allowed.", 400

    if file:
        filename = file.filename
        filename = os.path.basename(filename)
        directory = os.path.join(os.getcwd(), 'app', 'static', 'data', 'dpn')

        if not os.path.exists(directory):
            os.makedirs(directory)

        filepath = os.path.join(directory, filename)
        file.save(filepath)

        try:
            transform_to_svg(filepath)
        except Exception as e:
            return f"Error: Could not transform file to SVG. {str(e)}", 500

        session['uploaded_filename'] = filename
        session['upload_complete'] = True
        session['configuration_complete'] = False
        session['results_complete'] = False

        return redirect(url_for('dpn_visualizer'))


@app.route('/download_xes')
def download_xes():
    filename = session.get('uploaded_filename', '')
    return redirect(url_for('static', filename=f'data/xes_files/{filename.split(".")[0]}.xes'))


@app.route('/download_webppl')
def download_webppl():
    filename = session.get('uploaded_filename', '')
    return redirect(url_for('static', filename=f'data/webppl_files/{filename.split(".")[0]}.wppl'))


@app.route('/get_distribution_config', methods=['GET'])
def get_distribution_config():
    distribution = request.args.get('distribution')
    config_file_path = "app/static/distribution_configurations/available_distributions.json"

    try:
        with open(config_file_path, 'r') as config_file:
            config_data = json.load(config_file)
        distribution_config = config_data["distributions"].get(distribution)

        if distribution_config is None:
            return jsonify({"error": "Distribution not found: " + distribution}), 404

        return jsonify(distribution_config)

    except FileNotFoundError:
        return jsonify({"error": "Configuration file not found"}), 500
    except json.JSONDecodeError:
        return jsonify({"error": "Error decoding JSON"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/error_message')
def error_message():
    session['results_complete'] = False
    error_message_query = session.get('error_message', '')
    return render_template('error_message.html', error_message=error_message_query)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
