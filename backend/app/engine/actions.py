from __future__ import annotations

from typing import Dict, List

ACTION_CATALOG: List[Dict[str, object]] = [
    {
        "action_type": "defend",
        "label": "Defend",
        "needs_target": True,
        "description": "Publicly defend someone to build trust with them but risk drawing attention.",
    },
    {
        "action_type": "accuse",
        "label": "Accuse",
        "needs_target": True,
        "description": "Accuse a participant to increase suspicion on them and create polarization.",
    },
    {
        "action_type": "quiet",
        "label": "Stay Quiet",
        "needs_target": False,
        "description": "Limit exposure this round; reduces heat but slows alliance growth.",
    },
    {
        "action_type": "share_info",
        "label": "Share Info",
        "needs_target": True,
        "description": "Share strategic observations with a target to raise bilateral trust.",
    },
    {
        "action_type": "build_alliance",
        "label": "Build Alliance",
        "needs_target": True,
        "description": "Attempt a visible alliance pact that can protect you in votes.",
    },
    {
        "action_type": "spread_doubt",
        "label": "Spread Doubt",
        "needs_target": True,
        "description": "Subtly cast doubt on someone; less direct than accuse.",
    },
]

VALID_ACTIONS = {item["action_type"] for item in ACTION_CATALOG}
