"""NEA Weather integration."""

DOMAIN = "nea_weather"
PLATFORMS = ["weather"]


async def async_setup(hass, config):
    """Set up the NEA Weather component."""
    return True
