import logging

import voluptuous as vol
from homeassistant import config_entries, core, exceptions
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from proxmoxer import ProxmoxAPI
from .proxmox import ProxmoxClient
from requests.exceptions import ConnectTimeout, SSLError, ConnectionError, HTTPError
from proxmoxer.backends.https import AuthenticationError

_LOGGER = logging.getLogger(__name__)
from .const import (
    DOMAIN,
    SERVERIP,
    SERVERPORT,
    REALM,
    SSL_CERT,
    UPDATE_INTERVAL,
    UPDATE_INTERVAL_DEFAULT
)
DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(REALM, default="pam"): str,
        vol.Required(SERVERIP): str,
        vol.Required(SERVERPORT, default="8006"): str,
        vol.Required(SSL_CERT, default=True): bool
    }
)

async def validate_input(hass: core.HomeAssistant, data):
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    proxmox = ProxmoxClient(data[SERVERIP], data[SERVERPORT], data[CONF_USERNAME], data[REALM], data[CONF_PASSWORD], data[SSL_CERT])
    try:
       result = await hass.async_add_executor_job(proxmox.build_client)
    except AuthenticationError:
        _LOGGER.warning("Error incorrect credentials")
        raise InvalidAuth
    except SSLError:
        _LOGGER.warning("SSL ERROR OCCURRED")
        raise SSLError
    except HTTPError:
        _LOGGER.debug("HTTP Error")
    except ConnectionError:
        _LOGGER.debug("ConnectionError")
        raise CannotConnect
    return {"title": f"Proxmox Server ({data[SERVERIP]})"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL
    
    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                return self.async_create_entry(title=info["title"], data=user_input)
            except CannotConnect:
                print("EXCEPT")
                errors["base"] = "cannot_connect"
            except SSLError:
                errors["base"] = "ssl_error"
                raise SSLError
            except InvalidAuth:
                print("INVALID AUTH")
                errors["base"] = "invalid_auth"
            except ConnectionError:
                errors["base"] = "Connection Refused to Server"
                raise CannotConnect
            except HTTPError:
                _LOGGER.exception("HTTP ERROR")
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )
        
    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlow(config_entry)
        
class OptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        options = {
            vol.Optional(
                UPDATE_INTERVAL,
                default=self.config_entry.options.get(
                    UPDATE_INTERVAL, UPDATE_INTERVAL_DEFAULT
                ),
            ): int,
        }

        return self.async_show_form(step_id="init", data_schema=vol.Schema(options))

class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""

class InvalidHost(exceptions.HomeAssistantError):
    """Error for invalid Host"""

class SSLError(exceptions.HomeAssistantError):
    """Error for untrusted SSL validation"""

