"""T2A-ESS slot model -> SysML v2 textual model converter.

Consumes a Text2Activity Extraction Slot (T2A-ESS) JSON (produced upstream by
text2activity) and emits a SysML v2 textual activity model, following the
conversion rules in ``docs/Text2Activity-Extraction-Slot-Schema.md`` (§SysML
v2/KerML mapping rules).
"""

from .model import T2AModel, load_model, load_model_from_dict
from .converter import convert_model, convert_file
from .state_converter import (
    STATE_CONVERTER_VERSION,
    convert_state_file,
    convert_state_model,
    state_summary,
)
from .validate import (
    Issue,
    REGISTERED_CUSTOM_TYPES,
    RELATION_CONTRACT,
    summarize,
    validate_effbd,
    validate_schema,
)

__all__ = [
    "T2AModel",
    "load_model",
    "load_model_from_dict",
    "convert_model",
    "convert_file",
    "convert_state_model",
    "convert_state_file",
    "state_summary",
    "STATE_CONVERTER_VERSION",
    "validate_effbd",
    "validate_schema",
    "summarize",
    "Issue",
    "RELATION_CONTRACT",
    "REGISTERED_CUSTOM_TYPES",
]
