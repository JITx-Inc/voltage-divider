# FIXME: Only OPERATING_TEMPERATURE is used in the voltage divider. See about reconciling with jsl port to python
from jitx.toleranced import Toleranced

# ============================================
# ====== Design/Part Selection Settings ======
# ============================================

# Operating temperature range (default: 0.0 to 25.0 C)
OPERATING_TEMPERATURE = Toleranced.min_max(0.0, 25.0)
"""
Default operating temperature range for the design, as a Toleranced value.
Equivalent to OPERATING-TEMPERATURE in settings.stanza.
"""
