from application import AnonymousTransmissionProgram

from squidasm.run.stack.config import StackNetworkConfig
from squidasm.run.stack.run import run

nodes = ["Alice", "Bob", "Charlie", "David"]

# import network configuration from file
cfg = StackNetworkConfig.from_file("config.yaml")

byte = 11111111
exp_runs = 100

# Create instances of programs to run
alice_program = AnonymousTransmissionProgram(node_name="Alice", node_names=nodes)
bob_program = AnonymousTransmissionProgram(node_name="Bob", node_names=nodes,send_byte=byte, apply_corr=False)
charlie_program = AnonymousTransmissionProgram(node_name="Charlie", node_names=nodes)
david_program = AnonymousTransmissionProgram(node_name="David", node_names=nodes)

# Run the simulation. Programs argument is a mapping of network node labels to programs to run on that node
reg_results = run(config=cfg, programs={"Alice": alice_program, "Bob": bob_program,
                          "Charlie": charlie_program, "David": david_program}, num_times=exp_runs)

# Hamming distance for calculating success
def hamming(byte1, byte2):
    bbyte1 = int(str(byte1),2)
    bbyte2 = int(str(byte2),2)
    hamming_distance = bin(bbyte1^bbyte2).count('1')
    return hamming_distance

# Create instances of programs to run
alice_program = AnonymousTransmissionProgram(node_name="Alice", node_names=nodes)
bob_program = AnonymousTransmissionProgram(node_name="Bob", node_names=nodes,send_byte=byte, apply_corr=True)
charlie_program = AnonymousTransmissionProgram(node_name="Charlie", node_names=nodes)
david_program = AnonymousTransmissionProgram(node_name="David", node_names=nodes)

# Run the simulation. Programs argument is a mapping of network node labels to programs to run on that node
corr_results = run(config=cfg, programs={"Alice": alice_program, "Bob": bob_program,
                          "Charlie": charlie_program, "David": david_program}, num_times=exp_runs)

# Calculate and print Average Success Probability and Average Transmission Speed.

# Success probability
reg_total = 0
for experiment in reg_results[0]:
    rslt_byte = experiment['recvd_byte']
    reg_total += hamming(byte,rslt_byte)
    
reg_success_average = reg_total/exp_runs

print(f"Success average without correction: {reg_success_average}. (Ideal value = 0)")

# Average transmission speed
reg_total = 0
for node in reg_results:
    for experiment in node:
        run_time = experiment['run_time']
        speed = 10/run_time
        reg_total += speed

reg_transm_avg = reg_total/(len(nodes)*exp_runs)
    
print(f"Average transmission speed without correction: {reg_transm_avg} km/ns.")

# Success probability
corr_total = 0
for experiment in corr_results[0]:
    rslt_byte = experiment['recvd_byte']
    corr_total += hamming(byte,rslt_byte)
    
corr_success_average = corr_total/exp_runs

print(f"Corrected success average: {corr_success_average}. (Ideal value = 0)")

# Average transmission speed
corr_total = 0
for node in corr_results:
    for experiment in node:
        run_time = experiment['run_time']
        speed = 10/run_time
        corr_total += speed

corr_transm_avg = corr_total/(len(nodes)*exp_runs)

print(f"Corrected average transmission speed: {corr_transm_avg} km/ns.")