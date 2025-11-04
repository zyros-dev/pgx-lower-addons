IR_PHASE_NAME_MAP = {
    "Phase 3a before optimization": ("RelAlg: Before Optimization", 1),
    "Phase 3a AFTER: RelAlg -> Optimised RelAlg": ("RelAlg: After Optimization", 2),
    "Phase 3a AFTER: RelAlg -> DB+DSA+Util": ("DB+DSA+Util", 3),

    "Phase 3b BEFORE: DB+DSA -> Standard": (None, 999),

    "After dsa standard pipeline pm1": ("DSA Pipeline: Pass 1", 4),
    "After dsa standard pipeline pm2": ("DSA Pipeline: Pass 2", 5),

    "After func pipeline": ("Function Pipeline", 6),

    "Phase 3c BEFORE: Standard -> LLVM": (None, 999),
    "Phase 3c AFTER: Standard -> LLVM": ("Standard: After LLVM Lowering", 7),
}


def normalize_ir_phase_name(raw_name: str):
    result = IR_PHASE_NAME_MAP.get(raw_name)
    if result:
        return result[0]
    return raw_name


def get_ir_phase_order(raw_name: str):
    result = IR_PHASE_NAME_MAP.get(raw_name)
    if result:
        return result[1]
    return 999
