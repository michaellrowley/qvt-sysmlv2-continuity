HEAT_BELOW_C = 24.0
OFF_ABOVE_C = 26.0
SAFE_OFF = "SAFE_OFF"


def generate_heater_command(
    temperature_c: float,
    sensor_valid: bool = True,
    current_state: str = "HOLD",
) -> str:
    if not sensor_valid:
        return SAFE_OFF
    if temperature_c < HEAT_BELOW_C:
        return "HEAT"
    if temperature_c > OFF_ABOVE_C:
        return "OFF"
    return current_state
