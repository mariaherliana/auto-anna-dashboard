from src.utils import parse_phone_number, parse_iso_datetime, parse_time_duration, parse_call_memo, classify_number
from src.idn_area_codes import EMERGENCY_NUMBERS, INTERNATIONAL_PHONE_PREFIXES
import math
from src.utils import call_hash, classify_number, format_datetime_as_human_readable, format_timedelta, format_username, parse_call_memo, parse_iso_datetime, parse_phone_number
from src.international_rates import INTERNATIONAL_RATES
from config import CONFIG

class CallDetail:
    def __init__(
        self,
        client:str,
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
    ):
        self.client = client
        self.sequence_id = sequence_id
        self.user_name = user_name
        self.call_from = parse_phone_number(call_from)  # Normalizing here
        self.call_to = parse_phone_number(call_to)      # Normalizing here
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
        self.number_type = classify_number(self.call_to, self.call_type, self.call_from, self.call_to)
        self.call_charge = self.calculate_call_charge()

    def calculate_per_minute_charge(self, rate: float) -> str:
        minutes = math.ceil(self.call_duration.total_seconds() / 60)
        return str(minutes * rate)

    def calculate_per_second_charge(self, rate: float) -> str:
        return str(self.call_duration.total_seconds() * rate)

    @property
    def matched_client(self):
        if not hasattr(self, "_matched_client"):
            self._matched_client = next(
                (config_entry for config_entry in CONFIG if config_entry.client == self.client),
                None
            )
        return self._matched_client

    @property
    def is_enduser(self):
        return self.matched_client is not None and "enduser" in self.matched_client.client.lower()

    def _handle_number_charge(self, number, allowed_types, rate, rate_type, call_type, call_to, call_from):
        if call_type in allowed_types and (call_to == number or call_from == number):
            if rate == 0:
                rate = 720
            if rate_type == "per_minute":
                return self.calculate_per_minute_charge(rate)
            elif rate_type == "per_second":
                return self.calculate_per_second_charge(rate)
        return None

    def calculate_call_charge(self) -> str:
        SPECIAL_ZERO_CHARGE_CALLERS = {"2150913403", "85161662298", "85157455618", "82248400487", "2150913400", "2131141271"}
        config = self.matched_client

        call_to = str(self.call_to or "").strip()
        call_from = str(self.call_from or "").strip()
        call_type = (self.call_type or "").strip().lower()
        number_type = self.number_type.lower() if self.number_type else ""
        chargeable_types = [ct.lower() for ct in config.chargeable_call_types] if config.chargeable_call_types else ["outbound call", "predictive dialer"]

        if not config:
            return self.calculate_per_minute_charge(720)

        if call_from in SPECIAL_ZERO_CHARGE_CALLERS and self.matched_client and self.matched_client.client == "siemens-id":
            return "0"

        #Excluded number type
        if number_type == "internal call":
            return self.calculate_per_minute_charge(0)

        # Premium call handling
        if number_type in ["premium call", "toll-free", "split charge"] or number_type in EMERGENCY_NUMBERS.values():
            rate = 1700 + (200 if self.is_enduser else 0)
            return self.calculate_per_minute_charge(rate)

        # International call handling
        carrier_key = config.carrier.title()  # Normalize the carrier name
        rate_map = INTERNATIONAL_RATES.get(carrier_key, INTERNATIONAL_RATES["Atlasat"])

        matched_key = next(
            (k for k in rate_map if k.lower() in number_type.lower() or number_type.lower() in k.lower()),
            None
        )

        if matched_key:
            base_rate = rate_map[matched_key]
            if self.is_enduser:
                base_rate += 200
            return self.calculate_per_minute_charge(base_rate)

        # Specific number logic for S2C
        s2c_target = call_to or call_from  # fallback if call_to is empty
        #print(f"DEBUG: call_type={call_type}, number_type={number_type}, call_to={call_to}, call_from={call_from}, s2c_target={s2c_target}, config.s2c={config.s2c}")
        s2c_list = config.s2c if isinstance(config.s2c, list) else [config.s2c]
        if (s2c_target in s2c_list or number_type == "scancall"):
            #print(f"DEBUG: Matched S2C by number or type")

            if call_type in ["incoming call", "answering machine"]:
                if config.s2c_rate_type == "per_minute":
                    return self.calculate_per_minute_charge(config.s2c_rate)
                elif config.s2c_rate_type == "per_second":
                    return self.calculate_per_second_charge(config.s2c_rate)

            elif call_type in chargeable_types:
                if config.s2c_rate_type == "per_minute":
                    return self.calculate_per_minute_charge(config.s2c_rate)
                elif config.s2c_rate_type == "per_second":
                    return self.calculate_per_second_charge(config.s2c_rate)

        number1_cts = [ct.lower() for ct in (config.number1_chargeable_call_types or [])]
        result = self._handle_number_charge(
            config.number1,
            number1_cts,
            config.number1_rate or 0,
            config.number1_rate_type or "per_minute",
            call_type,
            call_to,
            call_from
        )
        if result:
            return result

        number2_cts = [ct.lower() for ct in (config.number2_chargeable_call_types or [])]
        result = self._handle_number_charge(
            config.number2,
            number2_cts,
            config.number2_rate or 0,
            config.number2_rate_type or "per_minute",
            call_type,
            call_to,
            call_from
        )
        if result:
            return result

        # Otherwise, fallback to general chargeable_call_types (for all other calls)
        allowed_types = [ct.lower() for ct in getattr(config, "chargeable_call_types", [])]
        if not allowed_types or call_type in allowed_types:
            rate_type = getattr(config, "rate_type", "per_minute")
            rate = getattr(config, "rate", 0)
            if rate_type == "per_minute":
                return self.calculate_per_minute_charge(rate)
            elif rate_type == "per_second":
                return self.calculate_per_second_charge(rate)

        # General chargeable logic
        if call_type in chargeable_types:
            if config.rate_type == "per_second":
                return self.calculate_per_second_charge(config.rate if config.rate is not None else 720)
            else:
                return self.calculate_per_minute_charge(config.rate if config.rate is not None else 720)

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
            "Number type": classify_number(self.call_to, self.call_type, self.call_from, self.call_to),
            "Dial starts at": format_datetime_as_human_readable(self.dial_start_at),
            "Dial answered at": format_datetime_as_human_readable(
                self.dial_answered_at
            ),
            "Dial ends at": format_datetime_as_human_readable(self.dial_end_at),
            "Ringing time": format_timedelta(self.ringing_time),
            "Call duration": format_timedelta(self.call_duration),
            "Call memo": self.call_memo,
            "Call charge": self.call_charge,
        }

    def hash_key(self) -> str:
        return call_hash(self.call_from, self.call_to, self.dial_start_at)