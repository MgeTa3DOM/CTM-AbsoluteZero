"""
LIVING CODE: Self-Introspecting, Self-Modifying, Cooperative Intelligence

L = Logging Self-Introspection  (soul.py)
I = Information-Native Execution
V = Versioned Self-Modification  (skill.py)
I = Integrally Transparent
N = Network Cooperative          (network.py)
G = Growth-Optimized             (growth.py)
"""

from .soul import Soul, Thought, get_soul, set_soul
from .skill import Skill, SkillVersion
from .network import Agent, Collective, SharedMemory, Message
from .growth import GrowthTracker, GrowthSnapshot

__all__ = [
    "Soul", "Thought", "get_soul", "set_soul",
    "Skill", "SkillVersion",
    "Agent", "Collective", "SharedMemory", "Message",
    "GrowthTracker", "GrowthSnapshot",
]
