"""

This file depicts an example of how individual monitors should be run locally. This file should be copied and modified to meet the users specific needs. 

This script may be replicated in an example notebook that will show how to stream in data from AWS on the Roman Research Nexus and run the desired monitors on them.

"""

import asdf

from rdmt_spire.manager import MonitorManager
from rdmt_spire.monitors.noise_1f import Noise1fMonitor

# Open the file using ASDF package
path_to_file = "PATH TO DESIRED FILE"

# NOTE: The "ignore_" keywords are not needed but can be helpful to remove many warnings that can arise from mismatches in python packages that do not affect performance. They can be removed to ensure the package versions match, or kept in for quick debugging.
asdf_file = asdf.open(path_to_file, 
                      ignore_missing_extensions=True, 
                      ignore_unrecognized_tag=True)

# Run a monitor individually without the manager
noise_monitor = Noise1fMonitor(asdf_file)
noise_monitor.check_input()
noise_monitor.run()

# or you can run the implemented steps individually
noise_monitor.calculate_metrics()
noise_monitor.evaluate_metrics() # NOTE: "evaluate_metrics()" must be run after "calculate_metrics()"

# After running to print all the metric names
print(f"\n1/f noise monitor data cards: {noise_monitor.get_data_card('all')}\n")

# Use the monitor manager to run sets or specific monitors
manager = MonitorManager(input_file=asdf_file, monitor_name="noise_1f")
manager.process()
print(f"Monitor manager response for lambda: {manager.response_for_lambda()}\n")