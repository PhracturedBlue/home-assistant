"""
Sensor for Asterisk Voicemail box

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.asteriskvm/
"""
import asyncio
import logging

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (CONF_NAME, CONF_HOST,
                                 CONF_PORT, CONF_PASSWORD)
from homeassistant.helpers.entity import Entity
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.dispatcher import async_dispatcher_connect


REQUIREMENTS = ['asteriskvm']

_LOGGER = logging.getLogger(__name__)

SIGNAL_MESSAGE_UPDATE = 'asteriskvm.message_updated'
DOMAIN = 'Voicemail'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME): cv.string,
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_PORT): int,
    vol.Required(CONF_PASSWORD): cv.string,
})


@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Set up the Asterix VM platform."""
    from asteriskvm import Client as asteriskClient
    import asteriskvm.commands as cmd

    name = config.get(CONF_NAME)
    host = config.get(CONF_HOST)
    port = config.get(CONF_PORT)
    password = config.get(CONF_PASSWORD)

    @callback
    def handle_data(command, msg):
        """Handle changes to the mailbox."""
        if command == cmd.CMD_MESSAGE_LIST:
            _LOGGER.info("Signalling Callback")
            _LOGGER.info("AsteriskVM sent updated message list")
            async_dispatcher_send(hass, SIGNAL_MESSAGE_UPDATE, msg)

    _LOGGER.info("Start AsteriskVM listener")
    asteriskClient(host, port, password, handle_data)
    async_add_devices([AsteriskVMSensor(name)])


class AsteriskVMSensor(Entity):
    """Asterisk VM Sensor."""

    def __init__(self, name):
        """Initialize the sensor."""
        self._name = name
        self._attributes = None
        self._state = 0

    @asyncio.coroutine
    def async_added_to_hass(self):
        """Register callbacks."""
        async_dispatcher_connect(
            self.hass, SIGNAL_MESSAGE_UPDATE, self._update_callback)

    @callback
    def _update_callback(self, msg):
        """Update the message count in HA, if needed."""
        self._state = len(msg.keys())
        _LOGGER.info("Update Callback")
        self.hass.async_add_job(self.async_update_ha_state(True))

    @property
    def name(self):
        """Return the name of the sensor."""
        return '{}'.format(self._name or DOMAIN)

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state
