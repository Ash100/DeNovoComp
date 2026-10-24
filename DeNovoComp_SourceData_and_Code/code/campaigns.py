"""The four design specifications, declared a priori (before any run)."""

# A — general drug-like: the pipeline's default specification, unchanged.
SPEC_A = {
    "name": "A", "title": "General drug-like",
    "properties": {
        "MW":            {"mode": "range",    "min": 250, "max": 450, "weight": 1.0},
        "LogP":          {"mode": "range",    "min": 1.0, "max": 4.0, "weight": 1.0},
        "TPSA":          {"mode": "range",    "min": 40,  "max": 120, "weight": 1.0},
        "HBD":           {"mode": "max_cap",  "cap": 3,                "weight": 0.5},
        "HBA":           {"mode": "max_cap",  "cap": 7,                "weight": 0.5},
        "RotB":          {"mode": "max_cap",  "cap": 8,                "weight": 0.5},
        "AromaticRings": {"mode": "range",    "min": 1,   "max": 3,    "weight": 0.5},
        "QED":           {"mode": "maximize", "lo": 0.30, "hi": 0.90,  "weight": 1.0},
    },
    "reference_smiles": None,
    "similarity": {"min": 0.35, "max": 0.70, "weight": 1.0},
    "required_smarts": [],
    "forbidden_smarts": ["[N+](=O)[O-]"],
    "include_sa": True, "sa_target": 3.0, "sa_weight": 0.8,
    "aggregation": "geometric",
}

# B — CNS / blood-brain-barrier oriented.
SPEC_B = {
    "name": "B", "title": "CNS-oriented",
    "properties": {
        "MW":            {"mode": "range",    "min": 200, "max": 400, "weight": 1.0},
        "LogP":          {"mode": "range",    "min": 2.0, "max": 4.0, "weight": 1.0},
        "TPSA":          {"mode": "max_cap",  "cap": 90,               "weight": 1.5},
        "HBD":           {"mode": "max_cap",  "cap": 2,                "weight": 1.0},
        "HBA":           {"mode": "max_cap",  "cap": 7,                "weight": 0.5},
        "RotB":          {"mode": "max_cap",  "cap": 8,                "weight": 0.5},
        "AromaticRings": {"mode": "range",    "min": 1,   "max": 3,    "weight": 0.5},
        "QED":           {"mode": "maximize", "lo": 0.30, "hi": 0.90,  "weight": 1.0},
    },
    "reference_smiles": None,
    "similarity": {"min": 0.35, "max": 0.70, "weight": 1.0},
    "required_smarts": [],
    "forbidden_smarts": ["[N+](=O)[O-]"],
    "include_sa": True, "sa_target": 3.0, "sa_weight": 0.8,
    "aggregation": "geometric",
}

# C — analogue design anchored on celecoxib.
SPEC_C = {
    "name": "C", "title": "Analogue design (celecoxib reference)",
    "properties": {
        "MW":            {"mode": "range",    "min": 250, "max": 450, "weight": 1.0},
        "LogP":          {"mode": "range",    "min": 1.0, "max": 4.5, "weight": 1.0},
        "TPSA":          {"mode": "range",    "min": 40,  "max": 120, "weight": 0.5},
        "HBD":           {"mode": "max_cap",  "cap": 3,                "weight": 0.5},
        "QED":           {"mode": "maximize", "lo": 0.30, "hi": 0.90,  "weight": 0.5},
    },
    "reference_smiles": "Cc1ccc(cc1)-c1cc(nn1-c1ccc(cc1)S(N)(=O)=O)C(F)(F)F",
    "similarity": {"min": 0.15, "max": 0.50, "weight": 2.0},
    "required_smarts": [],
    "forbidden_smarts": ["[N+](=O)[O-]"],
    "include_sa": True, "sa_target": 3.0, "sa_weight": 0.8,
    "aggregation": "geometric",
}

# D — substructure-constrained: pyridine mandatory, nitro forbidden.
SPEC_D = {
    "name": "D", "title": "Substructure-constrained (pyridine required)",
    "properties": {
        "MW":            {"mode": "range",    "min": 250, "max": 450, "weight": 1.0},
        "LogP":          {"mode": "range",    "min": 1.0, "max": 4.0, "weight": 1.0},
        "TPSA":          {"mode": "range",    "min": 40,  "max": 120, "weight": 1.0},
        "HBD":           {"mode": "max_cap",  "cap": 3,                "weight": 0.5},
        "HBA":           {"mode": "max_cap",  "cap": 7,                "weight": 0.5},
        "RotB":          {"mode": "max_cap",  "cap": 8,                "weight": 0.5},
        "AromaticRings": {"mode": "range",    "min": 1,   "max": 3,    "weight": 0.5},
        "QED":           {"mode": "maximize", "lo": 0.30, "hi": 0.90,  "weight": 1.0},
    },
    "reference_smiles": None,
    "similarity": {"min": 0.35, "max": 0.70, "weight": 1.0},
    "required_smarts": ["c1ccncc1"],
    "forbidden_smarts": ["[N+](=O)[O-]"],
    "include_sa": True, "sa_target": 3.0, "sa_weight": 0.8,
    "aggregation": "geometric",
}

SPECS = [SPEC_A, SPEC_B, SPEC_C, SPEC_D]
