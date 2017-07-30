"""
Asterisk Voicemail interface.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/mailbox.asteriskvm/
"""
import asyncio
import logging

from homeassistant.core import callback
from homeassistant.components.asterisk_mbox import DOMAIN
from homeassistant.components.mailbox import (Mailbox, CONTENT_TYPE_MPEG,
                                              StreamError)
from homeassistant.helpers.dispatcher import async_dispatcher_connect

DEPENDENCIES = ['asterisk_mbox']
_LOGGER = logging.getLogger(__name__)

SIGNAL_MESSAGE_UPDATE = 'asterisk_mbox.message_updated'
SIGNAL_MESSAGE_REQUEST = 'asterisk_mbox.message_request'


@asyncio.coroutine
def async_get_handler(hass, config, async_add_devices, discovery_info=None):
    """Set up the Asterix VM platform."""
    return AsteriskMailbox(hass, DOMAIN)


class AsteriskMailbox(Mailbox):
    """Asterisk VM Sensor."""

    def __init__(self, hass, name):
        """Initialie Asterisk mailbox."""
        super().__init__(hass, name)
        async_dispatcher_connect(
            self.hass, SIGNAL_MESSAGE_UPDATE, self._update_callback)

    @callback
    def _update_callback(self, msg):
        """Update the message count in HA, if needed."""
        if self.entity:
            self.hass.async_add_job(self.entity.async_update_ha_state(True))

    def get_media_type(self):
        """Return the supported media type."""
        return CONTENT_TYPE_MPEG

    def get_media(self, msgid):
        """Return the media blob for the msgid."""
        from asterisk_mbox import ServerError
        client = self.hass.data[DOMAIN].client
        try:
            return client.mp3(msgid, sync=True)
        except ServerError as err:
            raise StreamError(err)

    def get_messages(self):
        """Return a list of the current messages."""
        return self.hass.data[DOMAIN].messages

    def delete(self, msgids):
        """Delete the specified messages."""
        client = self.hass.data[DOMAIN].client
        for sha in msgids:
            _LOGGER.info("Deleting: %s", sha)
            client.delete(sha)
        return True