"""Structured records for the Study hierarchy (see ARCHITECTURE.md).

Authoring files (YAML/Markdown under studies/ and domains/) are the source of
truth; these models define their shape and validate them on load. The
registry index (src/noam/registry/index.py) is a disposable, rebuildable
query layer over the same files -- never the other way around.
"""

from noam.models.capability import Capability
from noam.models.evidence import Evidence
from noam.models.experiment import Experiment
from noam.models.insight import Insight
from noam.models.model_hypothesis import ModelHypothesis
from noam.models.precedent import Precedent
from noam.models.requirement import Requirement
from noam.models.result import Result
from noam.models.rule_card import RuleCard
from noam.models.study import Study

__all__ = [
    "Capability",
    "Evidence",
    "Experiment",
    "Insight",
    "ModelHypothesis",
    "Precedent",
    "Requirement",
    "Result",
    "RuleCard",
    "Study",
]
