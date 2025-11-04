"""
IR phase name mapping and filtering.

Maps raw IR phase names to user-friendly display names.
Phases mapped to None are omitted from output.
"""

# Mapping of IR phase names to display names
# Use None to omit a phase from output
IR_PHASE_NAME_MAP = {
    # Phase 3a - RelAlg optimization
    "Phase 3a before optimization": "RelAlg: Before Optimization",
    "Phase 3a AFTER: RelAlg -> Optimised RelAlg": "RelAlg: After Optimization",
    "Phase 3a AFTER: RelAlg -> DB+DSA+Util": "DB+DSA+Util",

    # Phase 3b - DB+DSA to Standard
    "Phase 3b BEFORE: DB+DSA -> Standard": None,  # Omit

    # DSA standard pipeline passes
    "After dsa standard pipeline pm1": "DSA Pipeline: Pass 1",
    "After dsa standard pipeline pm2": "DSA Pipeline: Pass 2",

    # Function pipeline
    "After func pipeline": "Function Pipeline",

    # Phase 3c - Standard to LLVM
    "Phase 3c BEFORE: Standard -> LLVM": None,  # Omit
    "Phase 3c AFTER: Standard -> LLVM": "Standard: After LLVM Lowering",
}


def normalize_ir_phase_name(raw_name: str):
    """
    Convert raw IR phase name to display name.

    Args:
        raw_name: Raw IR phase name from pgx-lower

    Returns:
        User-friendly display name, or None if phase should be omitted
    """
    return IR_PHASE_NAME_MAP.get(raw_name, raw_name)
