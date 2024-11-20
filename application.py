from copy import copy
from typing import Optional, Generator

from squidasm.sim.stack.program import Program, ProgramContext, ProgramMeta
from netqasm.sdk.classical_communication.socket import Socket
from netqasm.sdk.epr_socket import EPRSocket

from squidasm.util.routines import create_ghz

import netsquid as ns

class AnonymousTransmissionProgram(Program):
    def __init__(self, node_name: str, node_names: list, send_byte: int = None, apply_corr: bool = False):
        """
        Initializes the AnonymousTransmissionProgram.

        :param node_name: Name of the current node.
        :param node_names: List of all node names in the network, in sequence.
        :param send_bit: The bit to be transmitted; set to None for nodes that are not the sender.
        """
        self.node_name = node_name
        self.send_byte = send_byte
        self.apply_corr = apply_corr

        # Find what nodes are next and prev based on the node_names list
        node_index = node_names.index(node_name)
        self.next_node_name = node_names[node_index+1] if node_index + 1 < len(node_names) else None
        self.prev_node_name = node_names[node_index-1] if node_index - 1 >= 0 else None

        # The remote nodes are all the nodes, but without current node. Copy the list to make the pop operation local
        self.remote_node_names = copy(node_names)
        self.remote_node_names.pop(node_index)

        # next and prev sockets, will be fetched from the ProgramContext using setup_next_and_prev_sockets
        self.next_socket: Optional[Socket] = None
        self.next_epr_socket: Optional[EPRSocket] = None
        self.prev_socket: Optional[Socket] = None
        self.prev_epr_socket: Optional[EPRSocket] = None

    @property
    def meta(self) -> ProgramMeta:
        # Filter next and prev node name for None values
        epr_node_names = [node for node in [self.next_node_name, self.prev_node_name] if node is not None]

        return ProgramMeta(
            name="anonymous_transmission_program",
            csockets=self.remote_node_names,
            epr_sockets=epr_node_names,
            max_qubits=2,
        )

    def run(self, context: ProgramContext):
        
        # Initialize next and prev sockets using the provided context
        self.setup_next_and_prev_sockets(context)
        
        recv_byte = []
        
        if self.send_byte is not None:

            binary_string = str(self.send_byte)

            # Check if the input is a valid byte (8 bits)
            if len(binary_string) != 8 or not all(bit in "01" for bit in binary_string):
                raise ValueError("Input must be an 8-bit binary number (e.g., 10101011)")

            # Iterate through each bit
            for bit in binary_string:
                
                # Convert bit (char) to integer for comparison
                bit = int(bit)
                
                # Run the anonymous transmission protocol and retrieve the received bit
                received_bit = yield from self.anonymous_transmit_bit(context, bit, self.apply_corr)
                
                recv_byte.append(received_bit)
                    
        else:
            
            # Iterate through each bit
            for _ in range(8):
                
                # Run the anonymous transmission protocol and retrieve the received bit
                received_bit = yield from self.anonymous_transmit_bit(context)
                
                recv_byte.append(received_bit)
        
        # Convert the list to a string
        recv_byte_string = ''.join(map(str,recv_byte))

        print(f"{self.node_name} has received the byte: {recv_byte_string}")
        
        run_time = ns.sim_time()
        
        return {"name": self.node_name, "run_time": run_time, "recvd_byte": recv_byte_string}

    def anonymous_transmit_bit(self, context: ProgramContext, send_bit: bool = None, correction: bool = False) -> Generator[None, None, bool]:
        """
        Anonymously transmits a bit to other nodes in the network as part of the protocol.

        :param context: The program's execution context.
        :param send_bit: Bit to be sent by the sender node; receivers should leave this as None.
        :param correction: If True applies repetition code of length three.
        :return: The bit received through the protocol, or the sent bit if this node is the sender.
        """
        
        if correction:
            
            encoded_recv_bit=[]
            
            for _ in range(3):
                
                # Save GHZ qubit at current node
                self.qubit = yield from self.gen_ghz(context) 
                
                if send_bit == 1:
                    self.qubit.Z()
                    yield from context.connection.flush()
                
                self.qubit.H()
                q_measure = self.qubit.measure()
                
                yield from context.connection.flush()
                        
                message = f"{q_measure}"
                
                self.broadcast_message(context,message)
                
                # Recieve classical message from all nodes
                recv_message = yield from self.receive_message(context)
                
                # Add current node's result
                recv_message.append(int(message))
                
                # Check measurements parity
                is_odd = sum(recv_message) % 2 != 0

                # Asign bit value based on parity
                if is_odd:
                    recv_bit = 1
                else:
                    recv_bit = 0
                
                encoded_recv_bit.append(recv_bit)
                
            ones = encoded_recv_bit.count(1)
            zeros = encoded_recv_bit.count(0)
            
            # Use majority voting to decode
            if ones > zeros:
                corrected_bit = 1
            else:
                corrected_bit = 0
            
            return corrected_bit
        
        else:
            # Save GHZ qubit at current node
            self.qubit = yield from self.gen_ghz(context)
            
            if send_bit == 1:
                self.qubit.Z()
                yield from context.connection.flush()
                    
            self.qubit.H()
            q_measure = self.qubit.measure()
            
            yield from context.connection.flush()
                    
            message = f"{q_measure}"
            
            self.broadcast_message(context,message)
            
            # Recieve classical message from all nodes
            recv_message = yield from self.receive_message(context)
            
            # Add current node's result
            recv_message.append(int(message))
            
            # Check measurements parity
            is_odd = sum(recv_message) % 2 != 0

            # Asign bit value based on parity
            if is_odd:
                recv_bit = 1
            else:
                recv_bit = 0
            
            return recv_bit

    def broadcast_message(self, context: ProgramContext, message: str):
        """Broadcasts a message to all nodes in the network."""
        for remote_node_name in self.remote_node_names:
            socket = context.csockets[remote_node_name]
            socket.send(message)
            
    def receive_message(self, context: ProgramContext):
        """Receives message from each node in the network."""
        message = []
        for remote_node_name in self.remote_node_names:
            socket = context.csockets[remote_node_name]
            socket_message = yield from socket.recv()
            message.append(int(socket_message))
        return message
        
    def setup_next_and_prev_sockets(self, context: ProgramContext):
        """Initializes next and prev sockets using the given context."""
        if self.next_node_name:
            self.next_socket = context.csockets[self.next_node_name]
            self.next_epr_socket = context.epr_sockets[self.next_node_name]

        if self.prev_node_name:
            self.prev_socket = context.csockets[self.prev_node_name]
            self.prev_epr_socket = context.epr_sockets[self.prev_node_name]
            
    def gen_ghz(self, context: ProgramContext):
        """Generates GHZ state on the whole network."""
        qubit, m = yield from create_ghz(
            context.connection,
            self.prev_epr_socket,
            self.next_epr_socket,
            self.prev_socket,
            self.next_socket,
            do_corrections=True,
        )

        yield from context.connection.flush()
        
        return qubit