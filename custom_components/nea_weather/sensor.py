"""Support for Meteorological Service Singapore weather service."""
import datetime
import json
import logging
import time
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
        return self._today_data[condition]

    def get_forecast_reading(self):
        """Return forecast reading"""
        return self._forecast_data

    def get_reading(self, area):
        """Return reading"""
        if self._data is None:
            return None

        for entry in self._data:
            try:
                if entry["Name"].lower() != area.lower():
                    continue
                return entry["Forecast"]
            except ValueError as err:
                _LOGGER.error("Check NEA %s", err.args)
                raise

    def should_update(self):
        """Return if update is due"""
        if self.last_updated is None:
            return True

        now = dt_util.utcnow()
        update_due_at = self.last_updated.replace(tzinfo=pytz.UTC) + datetime.timedelta(minutes=2)
        return now > update_due_at

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Get the latest data from NEA."""
        if not self.should_update():
            return
        try:
            two_hour_forecast = "https://www.nea.gov.sg/api/WeatherForecast/forecast24hrnowcast2hrs/" + \
                str(int(time.time()))
            two_hour_result = requests.get(two_hour_forecast, timeout=10).json()
            if (two_hour_result is not None and two_hour_result["Channel2HrForecast"] is not None and
                two_hour_result["Channel2HrForecast"]["Item"] is not None and
                two_hour_result["Channel2HrForecast"]["Item"]["WeatherForecast"] is not None and
                two_hour_result["Channel2HrForecast"]["Item"]["WeatherForecast"]["Area"] is not None):
                self._data = two_hour_result["Channel2HrForecast"]["Item"]["WeatherForecast"]["Area"]

            if (two_hour_result is not None and two_hour_result["Channel24HrForecast"] is not None and
                    two_hour_result["Channel24HrForecast"]["Main"] is not None):
                self._today_data = two_hour_result["Channel24HrForecast"]["Main"]

            four_day_forecast = "https://www.nea.gov.sg/api/Weather4DayOutlook/GetData/" + \
                str(int(time.time()))
            self._forecast_data = requests.get(four_day_forecast, timeout=10).json()

            self.last_updated = dt_util.utcnow()
            return

        except ValueError as err:
            _LOGGER.error("Check NEA %s", err.args)
            self._data = None
            self._forecast_data = None
            self._today_data = None
            raise
