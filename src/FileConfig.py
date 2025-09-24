from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Files:
    client: str
    dashboard: str
    output: str
    carrier: str = "Atlasat"  # default carrier
    rate: Optional[float] = None
    rate_type: Optional[str] = "per_minute"

    # Special number-rate mapping
    number1: Optional[str] = None
    number1_rate: Optional[float] = None
    number1_rate_type: Optional[str] = "per_minute"
    number1_chargeable_call_types: List[str] = field(default_factory=list)
    number2: Optional[str] = None
    number2_rate: Optional[float] = None
    number2_rate_type: Optional[str] = "per_minute"
    number2_chargeable_call_types: List[str] = field(default_factory=list)

    # S2C logic
    s2c: Optional[str] = None
    s2c_rate: Optional[float] = None
    s2c_rate_type: Optional[str] = "per_minute"

    # General
    chargeable_call_types: List[str] = field(default_factory=list)
