"""NEA Weather integration."""

DOMAIN = "nea_weather"
PLATFORMS = ["weather", "sensor"]


async def async_setup(hass, config):
    """Set up the NEA Weather component."""
    return True
