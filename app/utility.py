import pm4py
import os
from lxml import etree as ET
import re


def transform_to_svg(file_path: str):
    try:
        net, initial_marking, final_marking = pm4py.read.read_pnml(file_path)
        svg_name = os.path.splitext(os.path.basename(file_path))[0]
        directory = os.path.join(os.getcwd(), 'app', 'static', 'data', 'svg')

        if not os.path.exists(directory):
            os.makedirs(directory)

        svg_path = os.path.join(directory, f'{svg_name}.svg')
        pm4py.save_vis_petri_net(net, initial_marking, final_marking, svg_path)
        replace_text_with_shapes_from_file(svg_path)
        replace_font(svg_path)
    except Exception as e:
        raise RuntimeError(f"Error while transforming file to SVG: {str(e)}")


def get_guards(net):
    guards = {}
    for transition in net.transitions:
        guard = transition.properties.get('guard', None)
        if guard is not None:
            guards[transition.name] = guard

    return guards


def get_events(net):
    events = {transition.name: transition.label for transition in net.transitions}

    return events


def replace_text_with_shapes(svg_content):
    if svg_content.startswith('<?xml'):
        svg_content = '\n'.join(svg_content.split('\n')[1:])

    root = ET.fromstring(svg_content.encode('utf-8'))
    ns = {'svg': 'http://www.w3.org/2000/svg'}

    replacements = []

    for text in root.findall('.//svg:text', namespaces=ns):
        parent = text.getparent()
        content = text.text.strip()
        previous = text.getprevious()
        if content == '●':

            circle = ET.Element('circle', {
                'fill': 'black',
                'cx': previous.get('cx'),
                'cy': previous.get('cy'),
                'r': str(float(text.get('font-size', '34')) / 2)
            })

            replacements.append((parent, text, circle))

        elif content == '■':
            size = float(text.get('font-size', '32'))
            rx = float(previous.get('rx')) / 2
            ry = float(previous.get('ry')) / 2
            x = float(previous.get('cx')) - rx
            y = float(previous.get('cy')) - ry

            rect = ET.Element('rect', {
                'fill': 'black',
                'x': str(x),
                'y': str(y),
                'width': str(size),
                'height': str(size)
            })
            replacements.append((parent, text, rect))

    for parent, old, new in replacements:
        parent.replace(old, new)

    return ET.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8').decode()


def replace_text_with_shapes_from_file(input_file, output_file=None):
    with open(input_file, 'r', encoding='utf-8') as file:
        svg_content = file.read()

    modified_svg = replace_text_with_shapes(svg_content)

    if output_file is None:
        output_file = input_file

    with open(output_file, 'w', encoding='utf-8') as file:
        file.write(modified_svg)


def replace_font(input_file, output_file=None):
    with open(input_file, 'r', encoding='utf-8') as file:
        svg_content = file.read()

    modified_svg = svg_content.replace('Times New Roman,serif', 'Arial Narrow,sans-serif')

    if output_file is None:
        output_file = input_file
    with open(output_file, 'w', encoding='utf-8') as file:
        file.write(modified_svg)


def extract_prime_variables(conditions_dict, variable_dict):
    prime_variables_dict = {}

    for key, condition in conditions_dict.items():
        prime_variables = []

        for var in variable_dict.keys():
            pos = condition.find(var)
            while pos != -1:
                if pos + len(var) < len(condition) and condition[pos + len(var)] == "'":
                    prime_variable = var + "'"
                    regex_pattern = re.compile(re.escape(prime_variable) + r"\s*==\s*0")
                    if not regex_pattern.search(condition):
                        prime_variables.append(prime_variable)

                pos = condition.find(var, pos + 1)

        prime_variables = sorted(set(prime_variables))

        if prime_variables:
            prime_variables_dict[key] = prime_variables

    return prime_variables_dict


def transform_advanced_query(dpn, advanced_query):
    events = get_events(dpn.net)
    variables_dict = dpn.variable_information

    for key, event in events.items():
        advanced_query = re.sub(rf'\b{event}\b', f'globalStore.{key}', advanced_query)

    for variable in variables_dict.keys():
        advanced_query = re.sub(rf'\b{variable}\b', f'globalStore.{variable}', advanced_query)

    transformed_query = f"({advanced_query})"

    return transformed_query


def parse_string_to_dict(string, dpn):
    dictionary = {}
    temp_storage = {}
    cleared_string = ""

    events = get_events(dpn.net)
    for line in string.split('\n'):
        for event in events:
            if line.startswith(event):
                cleared_string += line + '\n'

    for line in cleared_string.split('\n'):
        if line:
            key, value = line.split(':')
            if len(key.split('_')) == 4:
                key = key.strip()
                value = value.strip()
                transition_key = key.split('_')[0]
                prime_variable = key.split('_')[1]
                prime_variable = prime_variable.replace("'", "")
                function_name = key.split('_')[2]
                function_name = function_name[0].lower() + function_name[1:]
                function_parameter_name = key.split('_')[3]

                if transition_key not in temp_storage:
                    temp_storage[transition_key] = {}

                if prime_variable not in temp_storage[transition_key]:
                    temp_storage[transition_key][prime_variable] = {
                        'function_name': function_name,
                        'parameters': {}
                    }

                temp_storage[transition_key][prime_variable]['parameters'][function_parameter_name] = value

    for transition_key, variables in temp_storage.items():
        if transition_key not in dictionary:
            dictionary[transition_key] = {}

        for prime_variable, func_details in variables.items():
            function_name = func_details['function_name']
            parameters = func_details['parameters']

            params_str = ', '.join([f"{k}: {v}" for k, v in parameters.items()])
            dictionary[transition_key][prime_variable] = (
                    f"globalStore.{{write_variable}} = {function_name}({{" + f"{{{params_str}}}" + "});"
            )

    return dictionary


def generate_error_message(simulation_query_display, simulation_query, filename):
    error_message = (
        f"Filename: {filename}\n"
        f"Simulation Query Display: {simulation_query_display}\n"
        f"Compiled Query: {simulation_query}\n\n"
    )
    return error_message

def escape_single_quote(value):
    return value.replace("'", "\\'")
