# DCSM: Dynamic Controller‑Switch Mapping for Load Balancing in SDN
This repository contains the complete implementation of the **DCSM** framework. 
DCSM dynamically balances the load among distributed SDN controllers by intelligently migrating switches from overloaded to underloaded controllers. The framework consists of three main modules:
- **Imbalance Detection** – Multi‑metric assessment of controller load.
- **Victim Switch Selection** – Choosing the best switch to migrate.
- **Destination Controller Selection** – Selecting the optimal target controller using a cost‑benefit model.
