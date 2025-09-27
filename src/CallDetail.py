import math
from src.utils import (
    parse_phone_number,
    parse_iso_datetime,
    parse_time_duration,
    parse_call_memo,
    classify_number,
    call_hash,
    format_datetime_as_human_readable,
    format_timedelta,
    format_username,
)
from src.idn_area_codes import EMERGENCY_NUMBERS
from src.international_rates import INTERNATIONAL_RATES
from src.FileConfig import Files


class CallDetail:
    def __init__(
        self,
        client: str,
        sequence_id: str,
        user_name: str,
        call_from: str,
        call_to: str,
        call_type: str,
        dial_start_at: str,
        dial_answered_at: str,
        dial_end_at: str,
        ringing_time: str,
        call_duration: str,
        call_memo: str,
        carrier: str,
        config: Files,
    ):
        self.client = client
        self.sequence_id = sequence_id
        self.user_name = user_name
        self.call_from = parse_phone_number(call_from)
        self.call_to = parse_phone_number(call_to)
        self.call_type = call_type
        self.dial_start_at = parse_iso_datetime(dial_start_at)
        self.dial_answered_at = (
            parse_iso_datetime(dial_answered_at) if dial_answered_at != "-" else None
        )
        self.dial_end_at = parse_iso_datetime(dial_end_at)
        self.ringing_time = parse_time_duration(ringing_time)
        self.call_duration = parse_time_duration(call_duration)
        self.call_memo = parse_call_memo(call_memo)
        self.carrier = carrier
        self.config = config  # direct Files object
        self.number_type = classify_number(
            self.call_to, self.call_type, self.call_from, self.call_to
        )
        self.call_charge = self.calculate_call_charge()

    def calculate_per_minute_charge(self, rate: float) -> str:
        minutes = math.ceil(self.call_duration.total_seconds() / 60)
        return str(minutes * rate)

    def calculate_per_second_charge(self, rate: float) -> str:
        return str(self.call_duration.total_seconds() * rate)

    def _handle_number_charge(
        self, number, allowed_types, rate, rate_type, call_type, call_to, call_from
    ):
        if call_type in allowed_types and (call_to == number or call_from == number):
            if rate == 0:
                rate = 720
            if rate_type == "per_minute":
                return self.calculate_per_minute_charge(rate)
            elif rate_type == "per_second":
                return self.calculate_per_second_charge(rate)
        return None

    def calculate_call_charge(self) -> str:
        SPECIAL_ZERO_CHARGE_CALLERS = {
            "2150913403",
            "85161662298",
            "85157455618",
            "82248400487",
            "2150913400",
            "2131141271",
        }

        call_to = str(self.call_to or "").strip()
        call_from = str(self.call_from or "").strip()
        call_type = (self.call_type or "").strip().lower()
        number_type = self.number_type.lower() if self.number_type else ""

        # Default chargeable call types
        chargeable_types = (
            [ct.lower() for ct in (self.config.chargeable_call_types or [])]
            if self.config.chargeable_call_types
            else ["outbound call", "predictive dialer"]
        )

        # Siemens special handling
        if call_from in SPECIAL_ZERO_CHARGE_CALLERS and self.client == "siemens-id":
            return "0"

        # Excluded number type
        if number_type == "internal call":
            return self.calculate_per_minute_charge(0)

        # Premium / Toll-free / Emergency
        if number_type in ["premium call", "toll-free", "split charge"] or number_type in EMERGENCY_NUMBERS.values():
            rate = 1700
            return self.calculate_per_minute_charge(rate)

        # International call handling (always Indosat rates)
        rate_map = INTERNATIONAL_RATES.get("Indosat", INTERNATIONAL_RATES["Atlasat"])
        matched_key = next(
            (k for k in rate_map if k.lower() in number_type.lower() or number_type.lower() in k.lower()),
            None,
        )
        if matched_key:
            base_rate = rate_map[matched_key]
            return self.calculate_per_minute_charge(base_rate)

        # S2C logic
        s2c_target = call_to or call_from
        s2c_list = self.config.s2c if isinstance(self.config.s2c, list) else [self.config.s2c]
        if (s2c_target in s2c_list or number_type == "scancall"):
            if call_type in ["incoming call", "answering machine"]:
                if self.config.s2c_rate_type == "per_minute":
                    return self.calculate_per_minute_charge(self.config.s2c_rate)
                elif self.config.s2c_rate_type == "per_second":
                    return self.calculate_per_second_charge(self.config.s2c_rate)
            elif call_type in chargeable_types:
                if self.config.s2c_rate_type == "per_minute":
                    return self.calculate_per_minute_charge(self.config.s2c_rate)
                elif self.config.s2c_rate_type == "per_second":
                    return self.calculate_per_second_charge(self.config.s2c_rate)

        # Number 1
        number1_cts = [ct.lower() for ct in (self.config.number1_chargeable_call_types or [])]
        result = self._handle_number_charge(
            self.config.number1,
            number1_cts,
            self.config.number1_rate or 0,
            self.config.number1_rate_type or "per_minute",
            call_type,
            call_to,
            call_from,
        )
        if result:
            return result

        # Number 2
        number2_cts = [ct.lower() for ct in (self.config.number2_chargeable_call_types or [])]
        result = self._handle_number_charge(
            self.config.number2,
            number2_cts,
            self.config.number2_rate or 0,
            self.config.number2_rate_type or "per_minute",
            call_type,
            call_to,
            call_from,
        )
        if result:
            return result

        # Fallback to general config
        allowed_types = [ct.lower() for ct in getattr(self.config, "chargeable_call_types", [])]
        if not allowed_types or call_type in allowed_types:
            rate_type = getattr(self.config, "rate_type", "per_minute")
            rate = getattr(self.config, "rate", 0)
            if rate_type == "per_minute":
                return self.calculate_per_minute_charge(rate)
            elif rate_type == "per_second":
                return self.calculate_per_second_charge(rate)

        # Excluded call types
        if call_type not in chargeable_types:
            return self.calculate_per_minute_charge(0)

        return self.calculate_per_minute_charge(720)

    def to_dict(self) -> dict:
        return {
            "Sequence ID": self.sequence_id,
            "User name": format_username(self.user_name),
            "Call from": self.call_from,
            "Call to": self.call_to,
            "Call type": self.call_type,
            "Number type": self.number_type,
            "Dial starts at": format_datetime_as_human_readable(self.dial_start_at),
            "Dial answered at": format_datetime_as_human_readable(self.dial_answered_at),
            "Dial ends at": format_datetime_as_human_readable(self.dial_end_at),
            "Ringing time": format_timedelta(self.ringing_time),
            "Call duration": format_timedelta(self.call_duration),
            "Call memo": self.call_memo,
            "Call charge": self.call_charge,
        }

    def hash_key(self) -> str:
        return call_hash(self.call_from, self.call_to, self.dial_start_at)
