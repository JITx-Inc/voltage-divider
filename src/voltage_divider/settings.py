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

# Part selection parameters
OPTIMIZE_FOR = ["area"]  # Tuple[str], default is ["area"]
MAX_Z = 500.0
MIN_PKG = "0402"
PREFERRED_MOUNTING = "smd"  # values in ["smd", "through-hole"]
MIN_CAP_VOLTAGE = 10.0  # Minimum voltage to allow for capacitors
DEFAULT_ALLOW_ALL_VENDOR_PART_NUMBERS = False

# Landpattern variables
DENSITY_LEVEL = "DensityLevelC"  # Could be an Enum if needed

MIN_OUTER_LAYER_PAD_SIZE = 0.2032  # mm
MAX_HOLE_SIZE_TOLERANCE = 0.0508   # mm
MIN_HOLE_SIZE_TOLERANCE = 0.0508   # mm
HOLE_POSITION_TOLERANCE = 0.0508   # mm

# ============================================
# ====== BOM Generator configuration =========
# ============================================

APPROVED_DISTRIBUTOR_LIST = [
    "Arrow",
    "Avnet",
    "DigiKey",
    "JLCPCB",
    "LCSC",
    "Mouser",
    "Newark",
]

DESIGN_QUANTITY = 100
ALLOW_NON_STOCK = True 
