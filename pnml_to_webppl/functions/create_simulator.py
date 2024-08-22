def create_simulator_enabled_transitions_function(function_str, dpn, verbose, simulation_query):
    # Start the JS function string
    function_str += "var enabledTransitions = filter(function(x) {\nreturn "

    # Dynamically generate conditions based on transition names
    conditions = []
    for i, transition in enumerate(dpn.net.transitions):
        condition = f"(x == {i} && globalStore.enabled_{transition.name})"
        conditions.append(condition)

    # Join all conditions with '||'
    joined_conditions = "||\n".join(conditions)
    indices = ", ".join(str(i) for i in range(len(dpn.net.transitions)))

    # Finish constructing the function string
    function_str += f"{joined_conditions};\n}}, [{indices}]);\n\n"

    # Add the check for no enabled transitions
    function_str += """if (steps <= 0) {\nreturn;\n}\n\n"""
    function_str += """if (enabledTransitions.length == 0) {\nreturn;\n}\n\n"""

    if simulation_query == "final_marking":
        function_str += """if (globalStore.""" + str(list(dpn.final_marking.keys())[0]) + """ > 0) {\nreturn;\n}\n\n"""
    else:
        function_str += f"if ({simulation_query})" + "{\nreturn;\n}\n\n"

    return function_str


def create_simulator_sample_transition_function(function_str, net, verbose):
    function_str += """var transition = sample(Categorical({vs: enabledTransitions}));\n\n"""
    for i, transition in enumerate(net.transitions):
        if i == 0:
            function_str += f"if (transition == {i}) {{\n"
        else:
            function_str += f"else if (transition == {i}) {{\n"

        function_str += f"log_transition(\"{transition.label}\");\n"
        function_str += f"fire_{transition.name}();\n"
        function_str += "}\n"

    function_str += """else {\nconsole.log("Selected illegal transition; should never happen.");\n}\nsimulator_loop(steps - 1);\n}\n\n"""
    return function_str


def create_simulator_init_function(function_str, verbose):
    function_str += """var simulator_loop = function(steps) {\n\n"""

    function_str += """globalStore.xesOutput = "";\n\n"""

    return function_str


def create_simulator_loop_function(function_str, dpn, verbose, simulation_query):
    function_str = create_simulator_init_function(function_str, verbose)
    function_str = create_simulator_enabled_transitions_function(function_str, dpn, verbose, simulation_query)
    function_str = create_simulator_sample_transition_function(function_str, dpn.net, verbose)

    return function_str


def create_simulator_function(function_str, steps, sample_size, dpn, verbose, simulation_query):
    # Initialize the JavaScript function string
    function_str += "var simulator = function(){\ninit();\n"

    # Dynamically add update_enabled_ function calls based on transitions
    for transition in dpn.net.transitions:
        function_str += f"update_enabled_{transition.name}();\n"

    function_str += "\n"

    # Add conditional logging

    function_str += """globalStore.trace += "<trace>\\n";\n\n"""

    # Add the simulator loop with the dynamic steps argument
    function_str += f"simulator_loop({steps});\n\n"

    # Add conditional logging

    function_str += """globalStore.trace += "</trace>\\n";\n\n"""
    function_str += """console.log(globalStore.trace);\n\n"""

    # Add the return statement
    if simulation_query == "final_marking":
        function_str += f"return (globalStore." + str(list(dpn.final_marking.keys())[0]) + " > 0)" + ";\n}\n\n"
    else:
        function_str += "return " + str(simulation_query) + ";\n}\n\n"

    # Remove in later versions
    function_str += f"var dist = Infer({{\nmethod: 'MCMC', \nsamples: {sample_size},\n}},simulator);\n\n"

    # Extract the samples from the distribution
    function_str += "// Extract the samples from the distribution\n"
    function_str += "var samplesArray = dist.samples;\n"
    function_str += "var params = dist.params;\n\n"

    # Convert the samples array to a JSON string
    function_str += "// Convert the samples array to a JSON string\n"
    function_str += """var jsonString = JSON.stringify({"dist":dist});\n\n"""

    # Output the JSON string
    function_str += "// Output the JSON string\n"
    function_str += "jsonString;\n"

    return function_str
