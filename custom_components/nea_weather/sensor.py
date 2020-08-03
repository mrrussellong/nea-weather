"""Support for Meteorological Service Singapore weather service."""
import datetime
import json
import logging
import pytz
import requests
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
import homeassistant.util.dt as dt_util

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_NAME,
)
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle
from datetime import datetime as dt

_LOGGER = logging.getLogger(__name__)

MIN_TIME_BETWEEN_UPDATES = datetime.timedelta(seconds=60)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME): cv.string,
})

def setup_platform(hass, config, add_entities, discovery_info=None):
    nea_data = NEACurrentData()

    try:
        nea_data.update()
    except ValueError as err:
        _LOGGER.error("Received error from NEA Current: %s", err)
        return

    add_entities([NEACurrentData()])


class NEACurrentData:
    """Get data from NEA."""

    def __init__(self):
        """Initialize the data object."""
        self._data = None
        self._forecast_data = None
        self._today_data = None
        self.last_updated = None

    @property
    def latest_data(self):
        """Return the latest data object."""
        if self._data:
            return self._data[0]
        return None

    def get_last_updated_at(self):
        """Return the last updated at."""
        return self.last_updated

    def get_today_reading(self, condition):
        """Return today's reading"""
        condition_readings = self._today_data[condition]
        return condition_readings

    def get_forecast_reading(self):
        """Return forecast reading"""
        return self._forecast_data

    def get_reading(self, area):
        """Return reading"""
        for entry in self._data:
            try:
                if entry["area"] != area:
                    continue
                return entry["forecast"]
            except ValueError as err:
                _LOGGER.error("Check NEA %s", err.args)
                raise

    def should_update(self):
        """Return if update is due"""
        if self.last_updated is None:
            return True

        now = dt_util.utcnow()
        update_due_at = self.last_updated.replace(tzinfo=pytz.UTC) + datetime.timedelta(minutes=35)
        return now > update_due_at

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Get the latest data from NEA."""
        if not self.should_update():
            _LOGGER.debug(
                "NEA data was updated %s minutes ago, skipping update as"
                " < 35 minutes, Now: %s, LastUpdate: %s",
                (dt_util.utcnow() - self.last_updated.replace(tzinfo=pytz.UTC)),
                dt_util.utcnow(),
                self.last_updated.replace(tzinfo=pytz.UTC),
            )
            return

        try:
            two_hour_forecast = "https://api.data.gov.sg/v1/environment/2-hour-weather-forecast"
            two_hour_result = requests.get(two_hour_forecast, timeout=10).json()
            self._data = two_hour_result["items"][0]["forecasts"]

            four_day_forecast = "https://api.data.gov.sg/v1/environment/4-day-weather-forecast"
            four_day_result = requests.get(four_day_forecast, timeout=10).json()
            self._forecast_data = four_day_result["items"][0]["forecasts"]

            today_forecast = "https://api.data.gov.sg/v1/environment/24-hour-weather-forecast"
            today_result = requests.get(today_forecast, timeout=10).json()
            self._today_data = today_result["items"][0]["general"]

            self.last_updated = dt.strptime(
                today_result["items"][0]["update_timestamp"][:-3],
                '%Y-%m-%dT%H:%M:%S%Z')
            return

        except ValueError as err:
            _LOGGER.error("Check NEA %s", err.args)
            self._data = None
            self._forecast_data = None
            self._today_data = None
            raise
