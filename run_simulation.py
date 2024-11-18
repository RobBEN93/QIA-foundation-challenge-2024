from application import AnonymousTransmissionProgram

from squidasm.run.stack.config import StackNetworkConfig
from squidasm.run.stack.run import run

nodes = ["Alice", "Bob", "Charlie", "David"]

# import network configuration from file
cfg = StackNetworkConfig.from_file("config.yaml")

# Create instances of programs to run
alice_program = AnonymousTransmissionProgram(node_name="Alice", node_names=nodes, send_bit=True)
bob_program = AnonymousTransmissionProgram(node_name="Bob", node_names=nodes)
charlie_program = AnonymousTransmissionProgram(node_name="Charlie", node_names=nodes)
david_program = AnonymousTransmissionProgram(node_name="David", node_names=nodes)

# Run the simulation. Programs argument is a mapping of network node labels to programs to run on that node
run(config=cfg, programs={"Alice": alice_program, "Bob": bob_program,
                          "Charlie": charlie_program, "David": david_program}, num_times=1)