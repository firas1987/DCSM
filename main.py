import numpy as np
import networkx as nx
from collections import defaultdict

class Switch:
    """Represents an OpenFlow switch."""
    def __init__(self, sid, node, initial_rate=0.0):
        self.id = sid
        self.node = node                # node ID in the graph
        self.request_rate = initial_rate   # packet‑in rate (packets/sec)
        self.controller = None          # ID of master controller

class Controller:
    """Represents an SDN controller with resource capacities."""
    def __init__(self, cid, node, capacity, cpu_weight=0.5, mem_weight=0.5):
        self.id = cid
        self.node = node
        self.capacity = capacity        # max packet‑in rate it can handle
        self.cpu_weight = cpu_weight
        self.mem_weight = mem_weight
        self.switches = []               # list of switch IDs
        self.load = 0.0                  # real‑time load ratio L_real (eq 4‑6)
        self.cpu_util = 0.0
        self.mem_util = 0.0

    def update_load(self, switches_dict):
        """Compute load from assigned switches (eq 4‑6)."""
        total_req = sum(switches_dict[sid].request_rate for sid in self.switches)
        self.load = total_req / self.capacity
        # Simulate cpu/memory utilisation as proportional to load
        self.cpu_util = self.load
        self.mem_util = self.load
        return self.load

class Network:
    """Holds the topology, controllers, switches and provides utility methods."""
    def __init__(self, graph, controller_nodes, switch_nodes, controller_capacities=None):
        self.graph = graph
        self.hop = dict(nx.all_pairs_shortest_path_length(graph))
        self.controllers = {}
        self.switches = {}

        # Create controllers
        for i, node in enumerate(controller_nodes):
            cap = controller_capacities[i] if controller_capacities else 1000.0
            self.controllers[i] = Controller(i, node, cap)

        # Create switches
        for i, node in enumerate(switch_nodes):
            self.switches[i] = Switch(i, node, initial_rate=0.0)

        # Initial assignment: each switch to nearest controller
        self._initial_assignment()
        self.update_all_loads()

    def _initial_assignment(self):
        for sid, sw in self.switches.items():
            min_dist = float('inf')
            best_cid = None
            for cid, ctrl in self.controllers.items():
                dist = self.hop[sw.node][ctrl.node]
                if dist < min_dist:
                    min_dist = dist
                    best_cid = cid
            sw.controller = best_cid
            self.controllers[best_cid].switches.append(sid)

    def update_all_loads(self):
        for ctrl in self.controllers.values():
            ctrl.update_load(self.switches)

    def get_loads(self):
        return [ctrl.load for ctrl in self.controllers.values()]

    def get_mean_load(self):
        loads = self.get_loads()
        return np.mean(loads)

    def get_balance_index(self):
        """Balance Index BI (eq 4‑9)."""
        loads = self.get_loads()
        mean = np.mean(loads)
        if mean == 0:
            return 0.0
        std = np.std(loads)
        return std / mean

    def get_triggering_factor(self, cid):
        """Triggering factor φ (eq 4‑11)."""
        mean = self.get_mean_load()
        if mean == 0:
            return 1.0
        return self.controllers[cid].load / mean