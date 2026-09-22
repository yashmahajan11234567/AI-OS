import sys
sys.path.insert(0, 'C:\Development\AI-OS')

from aios.core.provider_registry import ProviderRegistry, _DEFAULT_COOLDOWN_DURATIONS
from aios.core.provider_failures import FailureCategory

# Test what's in the default durations
registry = ProviderRegistry()
print("Base duration:", registry._base_duration)
print("Max duration:", registry._max_duration)
print("Multiplier:", registry._multiplier)
print("NETWORK in _DEFAULT_COOLDOWN_DURATIONS:", FailureCategory.NETWORK in _DEFAULT_COOLDOWN_DURATIONS)
print("_DEFAULT_COOLDOWN_DURATIONS[NETWORK]:", _DEFAULT_COOLDOWN_DURATIONS.get(FailureCategory.NETWORK, "NOT FOUND"))
print("All _DEFAULT_COOLDOWN_DURATIONS:", dict(_DEFAULT_COOLDOWN_DURATIONS))