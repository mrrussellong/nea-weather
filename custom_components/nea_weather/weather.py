"""Support for Meteorological Service Singapore weather service."""
import logging
import datetime
import voluptuous as vol
from homeassistant.components.weather import (
    ATTR_FORECAST_CONDITION,
    ATTR_FORECAST_TEMP,
    ATTR_FORECAST_TEMP_LOW,
    ATTR_FORECAST_WIND_SPEED,
    ATTR_FORECAST_WIND_BEARING,
    ATTR_CONDITION_CLASS,
    ATTR_WEATHER_ATTRIBUTION,
    ATTR_WEATHER_HUMIDITY,
    ATTR_FORECAST_TIME,
    PLATFORM_SCHEMA,
    WeatherEntity,
)
from homeassistant.const import CONF_NAME, TEMP_CELSIUS
from homeassistant.helpers import config_validation as cv
from .sensor import NEACurrentData

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {vol.Optional(CONF_NAME): cv.string}
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the NEA weather platform."""
    _LOGGER.debug("initialising NEA Weather2 %s", config.get(CONF_NAME))

    nea_data = NEACurrentData()
    try:
        nea_data.update()
    except ValueError as err:
        _LOGGER.error("Received error from NEA Current: %s", err)
        return False

    add_entities([NEAWeather(nea_data, config.get(CONF_NAME))], True)


class NEAWeather(WeatherEntity):
    """Representation of a weather condition."""

    def __init__(self, nea_data, location_name):
        """Initialise the platform with a data instance and station name."""
        self.nea_data = nea_data
        self.location_name = location_name

    def update(self):
        """Update current conditions."""
        self.nea_data.update()

    def convert_to_forecast(self, input_str):
        _input_str = str(input_str).lower()
        if _input_str.find("Heavy Thundery Showers with Gusty Winds") != -1:
            return "pouring"
        elif _input_str.find("windy") != -1 or _input_str.find("shower") != -1:
            return "windy-variant"
        elif _input_str.find("heavy") != -1 and _input_str.find("rain") != -1:
            return "pouring"
        elif _input_str.find("rain") != -1 or _input_str.find("shower") != -1:
            return "rainy"
        elif _input_str.find("thunder") != -1:
            return "lightning-rainy"
        elif _input_str.find("wind") != -1:
            return "windy"
        elif _input_str.find("cloud") != -1:
            return "cloudy"
        elif _input_str.find("fair") != -1:
            return "sunny"
        else:
            return _input_str

    """
        clear-night	Clear night
        cloudy	Many clouds
        exceptional	Exceptional
        fog	Fog
        hail	Hail
        lightning	Lightning/ thunderstorms
        lightning-rainy	Lightning/ thunderstorms and rain
        partlycloudy	A few clouds
        pouring	Pouring rain
        rainy	Rain
        snowy	Snow
        snowy-rainy	Snow and Rain
        sunny	Sunshine
        windy	Wind
        windy-variant	Wind and clouds
    """
    # ps passing showers
    # ls light showers
    # lr light rain
    def convert_shortform(self, input_str):
        input_str = str(input_str).lower()
        _LOGGER.warn("_data input_str - NEA_v2 %s ", input_str)
        if input_str == "cl" or input_str == "pc" or input_str == "pn":
            return "cloudy"
        elif input_str == "tl": # thundery showers
            return "lightning-rainy"
        elif input_str == "hg":
            return "pouring"
        elif input_str == "fa":
            return "sunny"
        elif (input_str == "ps" or input_str == "ls" or
            input_str == "lr" or input_str == "ra" or
            input_str == "sh"):
            return "rainy"
        elif input_str == "wd":
            return "windy"
        else:
            return input_str

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"NEA: {self.location_name or '(unknown station)'}"

    @property
    def condition(self):
        """Return the current condition."""
        return self.convert_shortform(
            self.nea_data.get_reading(self.location_name))

    @property
    def state(self):
        return self.condition

    @property
    def forecast(self):
        """Return the current forecast."""
        return [
            {
                ATTR_FORECAST_TIME: datetime.datetime.now() + datetime.timedelta(days=index + 1),
                ATTR_FORECAST_TEMP: int(item["temperature"][:-2].split(" - ")[1]),
                ATTR_FORECAST_TEMP_LOW: int(item["temperature"][:-2].split(" - ")[0]),
                # ATTR_FORECAST_WIND_BEARING: item["wind"]["direction"],
                # ATTR_FORECAST_WIND_SPEED:
                    # ((item["wind"]["speed"]["high"] + item["wind"]["speed"]["low"]) / 2),
                # ATTR_WEATHER_HUMIDITY:
                    # ((item["relative_humidity"]["high"] + item["relative_humidity"]["low"]) / 2),
                ATTR_FORECAST_CONDITION: self.convert_to_forecast(item["forecast"]),
                ATTR_CONDITION_CLASS: item["forecast"],
                ATTR_WEATHER_ATTRIBUTION: self.attribution,
            }
            for index, item in enumerate(self.nea_data.get_forecast_reading())
        ]

    @property
    def temperature(self):
        """Return the temperature."""
        reading = self.nea_data.get_today_reading("Temperature")
        high = int(reading["High"])
        low = int(reading["Low"])
        return (high + low) / 2

    @property
    def temperature_unit(self):
        """Return the temperature unit."""
        return TEMP_CELSIUS

    @property
    def humidity(self):
        """Return the humidity."""
        reading = self.nea_data.get_today_reading("RelativeHumidity")
        high = int(reading["High"])
        low = int(reading["Low"])
        return (high + low) / 2

    @property
    def wind_speed(self):
        """Return the wind speed."""
        reading = self.nea_data.get_today_reading("Wind")["Speed"].split(" - ")
        high = int(reading[1])
        low = int(reading[0])
        return (high + low) / 2

    @property
    def wind_bearing(self):
        """Return the wind bearing."""
        return self.nea_data.get_today_reading("Wind")["Direction"]

    @property
    def attribution(self):
        """Return the attribution."""
        return "Data provided by the Meteorological Service Singapore"
