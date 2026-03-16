import numpy as np

def compute_balance_index(loads):
    """Compute BI from a list of controller loads."""
    mean = np.mean(loads)
    if mean == 0:
        return 0.0
    return np.std(loads) / mean

def migration_cost(network, switch_id, from_cid, to_cid, w_sc=0.5, w_cltc=0.5):
    """
    Migration Cost MC (eq 4‑16 to 4‑18).
    """
    sw = network.switches[switch_id]
    oc = network.controllers[from_cid]
    tc = network.controllers[to_cid]
    hop_to_target = network.hop[sw.node][tc.node]
    hop_to_oc = network.hop[sw.node][oc.node]

    SC = sw.request_rate * hop_to_target
    CLTC = sw.request_rate * (hop_to_target - hop_to_oc)
    MC = w_sc * SC + w_cltc * CLTC
    return MC

def valuation_function(sw_request_rate, hop_to_target, RU_j):
    """
    Valuation function ξ (eq 4‑21). RU_j is the remaining utilisation of target pool.
    """
    if (1 - RU_j) == 0:
        return float('inf')
    return (sw_request_rate * RU_j) / (hop_to_target * (1 - RU_j))

def remaining_utilization(network, underloaded_cids):
    """
    Remaining utilisation RU_j (eq 4‑20). Returns a single value for the whole underloaded pool.
    """
    total_spare = 0.0
    total_capacity = 0.0
    for uid in underloaded_cids:
        ctrl = network.controllers[uid]
        total_spare += (ctrl.capacity - ctrl.load * ctrl.capacity)
        total_capacity += ctrl.capacity
    if total_capacity == 0:
        return 0.0
    return total_spare / total_capacity