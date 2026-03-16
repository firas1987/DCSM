import random
import numpy as np
from .util import compute_balance_index, migration_cost, valuation_function, remaining_utilization

def imbalance_detection(network):
    """
    Algorithm 4.2: Identify overloaded (φ > 1) and underloaded (φ < 1) controllers.
    Returns (Cover, Cunder) as lists of controller IDs.
    """
    Cover = []
    Cunder = []
    mean_load = network.get_mean_load()
    for cid, ctrl in network.controllers.items():
        phi = ctrl.load / mean_load if mean_load > 0 else 1.0
        if phi > 1:
            Cover.append(cid)
        elif phi < 1:
            Cunder.append(cid)
    return Cover, Cunder

def victim_switch_selection(network, overloaded_cid, underloaded_cids):
    """
    Algorithm 4.3: Select best switch from overloaded controller to migrate,
    and the target controller that minimises the post‑migration Balance Index.
    Returns (best_switch_id, best_target_id) or (None,None) if none suitable.
    """
    oc = network.controllers[overloaded_cid]
    candidate_switches = oc.switches[:]
    if not candidate_switches:
        return None, None

    # Migration efficiency δ (eq 4‑12) – using hop to overloaded controller as cost
    delta = {}
    for sid in candidate_switches:
        sw = network.switches[sid]
        hop_to_oc = network.hop[sw.node][oc.node]
        if hop_to_oc == 0:
            hop_to_oc = 1   # avoid division by zero
        delta[sid] = sw.request_rate / hop_to_oc

    avg_delta = np.mean(list(delta.values())) if delta else 0

    best_bi_prime = float('inf')
    best_switch = None
    best_target = None
    loads_original = network.get_loads()

    for sid in candidate_switches:
        sw = network.switches[sid]
        for tid in underloaded_cids:
            tc = network.controllers[tid]

            # New loads after migration (eq 4‑13, 4‑14)
            li_new = oc.load - (sw.request_rate / oc.capacity)
            lj_new = tc.load + (sw.request_rate / tc.capacity)

            # Build temporary load vector
            loads = loads_original.copy()
            loads[overloaded_cid] = li_new
            loads[tid] = lj_new
            bi_prime = compute_balance_index(loads)

            # Condition: δ >= average δ and improves BI
            if delta[sid] >= avg_delta and bi_prime < best_bi_prime:
                best_bi_prime = bi_prime
                best_switch = sid
                best_target = tid

    return best_switch, best_target

def destination_controller_selection(network, overloaded_cid, switch_id, underloaded_cids):
    """
    Algorithm 4.4: For a given switch, select the best target controller
    based on the valuation function ξ and migration efficiency δ.
    Returns the best target controller ID.
    """
    sw = network.switches[switch_id]
    oc = network.controllers[overloaded_cid]
    current_bi = network.get_balance_index()
    best_psi = -float('inf')
    best_target = None
    loads_original = network.get_loads()

    # Precompute remaining utilisation for the whole underloaded pool
    RU_pool = remaining_utilization(network, underloaded_cids)

    for tid in underloaded_cids:
        tc = network.controllers[tid]

        # Post‑migration loads
        li_new = oc.load - (sw.request_rate / oc.capacity)
        lj_new = tc.load + (sw.request_rate / tc.capacity)
        loads = loads_original.copy()
        loads[overloaded_cid] = li_new
        loads[tid] = lj_new
        bi_prime = compute_balance_index(loads)

        # Migration Cost MC
        MC = migration_cost(network, switch_id, overloaded_cid, tid)

        # Migration efficiency δ_ij (eq 4‑19)
        delta_ij = abs(bi_prime - current_bi) / MC if MC != 0 else 0

        # Valuation function ξ (eq 4‑21)
        hop_to_target = network.hop[sw.node][tc.node]
        xi = valuation_function(sw.request_rate, hop_to_target, RU_pool)

        # Composite score ψ (eq 4‑22)
        w_xi, w_delta = 0.5, 0.5
        psi = w_xi * xi + w_delta * delta_ij

        if psi > best_psi:
            best_psi = psi
            best_target = tid

    return best_target

def dcsm_step(network):
    """
    One complete DCSM iteration.
    Returns True if a migration occurred.
    """
    Cover, Cunder = imbalance_detection(network)
    if not Cover or not Cunder:
        return False

    ocid = Cover[0]  # handle the first overloaded controller
    switch, target = victim_switch_selection(network, ocid, Cunder)
    if switch is not None and target is not None:
        # Refine target using destination selection
        target = destination_controller_selection(network, ocid, switch, Cunder)
        from .migration import perform_migration
        perform_migration(network, switch, ocid, target)
        return True
    return False

# ----- Comparison Algorithms -----

def smclbrt_step(network, threshold=0.8):
    """
    SMCLBRT: migrate a switch from any controller with load > threshold
    to the least loaded underloaded controller.
    """
    loads = network.get_loads()
    mean_load = network.get_mean_load()
    overloaded = [i for i, load in enumerate(loads) if load > threshold]
    if not overloaded:
        return False
    underloaded = [i for i, load in enumerate(loads) if load < mean_load]
    if not underloaded:
        return False

    ocid = overloaded[0]
    target = min(underloaded, key=lambda i: network.controllers[i].load)
    switches = network.controllers[ocid].switches[:]
    if not switches:
        return False
    # Switch with highest request rate
    switch = max(switches, key=lambda sid: network.switches[sid].request_rate)
    from .migration import perform_migration
    perform_migration(network, switch, ocid, target)
    return True

def dha_step(network, migration_prob=0.1):
    """
    Distributed Hopping Algorithm: each controller independently migrates
    a random switch to a random neighbour with probability migration_prob.
    """
    migrated = False
    for cid, ctrl in network.controllers.items():
        if random.random() < migration_prob and ctrl.switches:
            sid = random.choice(ctrl.switches)
            targets = [tid for tid in network.controllers if tid != cid]
            if not targets:
                continue
            tid = random.choice(targets)
            from .migration import perform_migration
            perform_migration(network, sid, cid, tid)
            migrated = True
    return migrated

def dlbmt_step(network, thresholds=[0.3, 0.6, 0.8]):
    """
    DLBMT: four‑level thresholds. Migrate a switch from an overloaded controller
    (load ≥ thresholds[2]) to the least loaded idle/normal controller.
    """
    loads = network.get_loads()
    idle = [i for i, load in enumerate(loads) if load < thresholds[0]]
    normal = [i for i, load in enumerate(loads) if thresholds[0] <= load < thresholds[1]]
    overload = [i for i, load in enumerate(loads) if load >= thresholds[2]]

    if not overload:
        return False
    target_pool = idle if idle else normal
    if not target_pool:
        return False

    ocid = overload[0]
    switches = network.controllers[ocid].switches[:]
    if not switches:
        return False
    # Switch with highest request rate
    sid = max(switches, key=lambda sid: network.switches[sid].request_rate)
    target = min(target_pool, key=lambda i: network.controllers[i].load)
    from .migration import perform_migration
    perform_migration(network, sid, ocid, target)
    return True