import os

import pm4py
from pm4py.objects.log.obj import EventLog

from pnml_to_webppl.functions.create_log import find_npm_global_path
from declare_constraint_checker.declare_component import generate_declare_checked_log, load_declare_model

# Run the webPPL file
full_path = os.path.abspath('webppl_files/simple_auction.wppl')

# Find path to webppl executable on your system (C:\Users\...\AppData\Roaming\npm\webppl.cmd for windows machines)
path_to_webppl = find_npm_global_path()

# Load declare model
declare_model = load_declare_model("declare_model.decl")

# Generate log with declare constraints
synthetic_log: EventLog = generate_declare_checked_log(full_path, path_to_webppl, declare_model, samples=1000000,  min_fitness=1.0,
                                             tries=100)

print("Len: ", len(pm4py.convert_to_dataframe(synthetic_log)))

# Save the generated log
pm4py.write_xes(synthetic_log, 'xes_files/simple_auction_declare_checked.xes')
