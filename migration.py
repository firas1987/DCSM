def perform_migration(network, switch_id, from_cid, to_cid):
    """
    Execute switch migration: update controller‑switch mappings and loads.
    """
    sw = network.switches[switch_id]
    # Remove from old controller
    network.controllers[from_cid].switches.remove(switch_id)
    # Add to new controller
    network.controllers[to_cid].switches.append(switch_id)
    sw.controller = to_cid
    network.update_all_loads()