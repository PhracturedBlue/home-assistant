"""Support for Asterisk Voicemail interface."""

import asyncio
import logging

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.const import (CONF_HOST,
                                 CONF_PORT, CONF_PASSWORD)

from homeassistant.const import (HTTP_BAD_REQUEST)

from homeassistant.core import callback
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.dispatcher import async_dispatcher_send

from homeassistant.components.frontend import register_built_in_panel
from homeassistant.components.http import HomeAssistantView

REQUIREMENTS = ['asterisk_mbox']

_LOGGER = logging.getLogger(__name__)

SIGNAL_MESSAGE_UPDATE = 'asterisk_mbox.message_updated'
DOMAIN = 'asterisk_mbox'
DATA_AC = 'asterisk_client'
DATA_MSGS = 'asterisk_msgs'

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_PORT): int,
        vol.Required(CONF_PASSWORD): cv.string,
    }),
}, extra=vol.ALLOW_EXTRA)


@asyncio.coroutine
def async_setup(hass, config):
    """Set up for the Asterisk Voicemail box."""
    from asterisk_mbox import Client as asteriskClient
    import asterisk_mbox.commands as cmd

    conf = config.get(DOMAIN)

    host = conf.get(CONF_HOST)
    port = conf.get(CONF_PORT)
    password = conf.get(CONF_PASSWORD)

    @callback
    def handle_data(command, msg):
        """Handle changes to the mailbox."""
        if command == cmd.CMD_MESSAGE_LIST:
            _LOGGER.info("Signalling Callback")
            _LOGGER.info("AsteriskVM sent updated message list")
            msgs = sorted(msg,
                          key=lambda item: item['info']['origtime'],
                          reverse=True)
            hass.data[DATA_MSGS] = msgs
            async_dispatcher_send(hass, SIGNAL_MESSAGE_UPDATE,
                                  hass.data[DATA_MSGS])

    # @callback
    # def stop_asterisk_client(_service_or_event):
    #     """Stop Asterisk listener."""
    #     _LOGGER.info("Stopping Asterisk listener...")
    #     client = hass.data[DATA_AC]
    #     client.stop()

    hass.data[DATA_MSGS] = []

    hass.async_add_job(async_load_platform(hass, "sensor", DOMAIN, {}, config))

    hass.data[DATA_AC] = asteriskClient(host, port, password, handle_data)
    # hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, stop_asterisk_client)

    if 'frontend' in hass.config.components:
        register_built_in_panel(hass, 'mailbox', 'Mailbox',
                                'mdi:account-location')
        hass.http.register_view(AsteriskMboxMsgView)
        hass.http.register_view(AsteriskMboxMP3View)
        hass.http.register_view(AsteriskMboxDeleteView)

    return True


class AsteriskMboxMsgView(HomeAssistantView):
    """View to return the list of messages."""

    url = "/api/asteriskmbox/messages"
    name = "api:asteriskmbox:messages"

    @asyncio.coroutine
    def get(self, request):
        """Retrieve Asterisk messages."""
        hass = request.app['hass']
        msgs = hass.data.get(DATA_MSGS)
        _LOGGER.info("Sending: %s", msgs)
        return self.json(msgs)


class AsteriskMboxMP3View(HomeAssistantView):
    """View to return an MP3."""

    url = r"/api/asteriskmbox/mp3/{index:\d+}"
    name = "api:asteriskmbox:mp3"

    # pylint: disable=no-self-use
    @asyncio.coroutine
    def get(self, request, index):
        """Retrieve Asterisk mp3."""
        hass = request.app['hass']
        msgs = hass.data.get(DATA_MSGS)
        index = int(index)
        client = hass.data[DATA_AC]
        _LOGGER.info("Sending mp3 for %d", index)
        return client.mp3(msgs[index]['sha'], sync=True)


class AsteriskMboxDeleteView(HomeAssistantView):
    """View to delete selected messages."""

    url = "/api/asteriskmbox/delete"
    name = "api:asteriskmbox:delete"

    @asyncio.coroutine
    def post(self, request):
        """Delete items."""
        try:
            data = yield from request.json()
            hass = request.app['hass']
            client = hass.data[DATA_AC]
            for sha in data:
                _LOGGER.info("Deleting: %s", sha)
                client.delete(sha)
        except ValueError:
            return self.json_message('Bad item id', HTTP_BAD_REQUEST)
