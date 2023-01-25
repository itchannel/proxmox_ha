"""Support for Proxmox VE."""
from __future__ import annotations

from datetime import timedelta
import logging
import async_timeout
from proxmoxer import ProxmoxAPI
from proxmoxer.backends.https import AuthenticationError
from proxmoxer.core import ResourceException
from .proxmox import ProxmoxClient
import requests.exceptions
from requests.exceptions import ConnectTimeout, SSLError
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
import voluptuous as vol

from .const import (
    DOMAIN,
    SERVERIP,
    SERVERPORT,
    REALM,
    SSL_CERT
)
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed
)

PLATFORMS = ["sensor"]
PROXMOX_CLIENTS = "proxmox_clients"
CONF_REALM = "realm"
CONF_NODE = "node"
CONF_NODES = "nodes"
CONF_VMS = "vms"
CONF_CONTAINERS = "containers"

COORDINATORS = "coordinators"
API_DATA = "api_data"

DEFAULT_PORT = 8006
DEFAULT_REALM = "pam"
DEFAULT_VERIFY_SSL = True
TYPE_VM = 0
TYPE_CONTAINER = 1
UPDATE_INTERVAL = 60

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the platform."""
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    serverip = entry.data[SERVERIP]
    serverport= entry.data[SERVERPORT]
    realm = entry.data[REALM]
    ssl_cert = entry.data[SSL_CERT]

    coordinator = ProxmoxDataUpdateCoordinator(hass, serverip, serverport, username, password, realm, ssl_cert)

    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    
    hass.data[DOMAIN][entry.entry_id] = coordinator

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class ProxmoxDataUpdateCoordinator(DataUpdateCoordinator):
    """DataUpdateCoordinator to handle fetching new data about the Proxmox Server."""

    def __init__(self, hass, serverip, serverport, username, password, realm, verify_ssl):
        self._hass = hass
        self.serverip = serverip
        self.serverport = serverport
        self.username = username
        self.password = password
        if verify_ssl is True:
            self._verify_ssl = False
        else:
            self._verify_ssl = True
        self.realm = realm
        self.proxmox_client = ProxmoxClient(self.serverip, self.serverport, self.username, self.realm, self.password, self._verify_ssl)
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=60),
        )

    async def _async_update_data(self):
        """Fetch data from Proxmox Server"""
        try:
            async with async_timeout.timeout(30):
                data = {}
                await self._hass.async_add_executor_job(self.proxmox_client.build_client)
                client = self.proxmox_client.get_api_client()
                _LOGGER.debug(client)
                data["nodes"] = await self._hass.async_add_executor_job(
                    client.nodes.get  # Fetch new status
                )
                for node in data["nodes"]:
                    node["vms"] = await self._hass.async_add_executor_job(
                        client.nodes(node["node"]).qemu().get
                    )

                    node["storage"] = await self._hass.async_add_executor_job(
                        client.nodes(node["node"]).storage().get
                    )
                
                _LOGGER.debug(data)
                return data
        except Exception as ex:
            self._available = False  # Mark as unavailable
            _LOGGER.warning(str(ex))
            _LOGGER.warning("Error communicating with Tdarr for %s", self.serverip)
            raise UpdateFailed(
                f"Error communicating with Tdarr for {self.serverip}"
            ) from ex



class ProxmoxEntity(CoordinatorEntity):
    """Represents any entity created for the Proxmox VE platform."""

    def __init__(
        self, *, device_id: str, name: str, coordinator: ProxmoxDataUpdateCoordinator
    ):
        """Initialize the Proxmox entity."""
        super().__init__(coordinator)

        self._device_id = device_id
        self._name = name

    @property
    def unique_id(self) -> str:
        """Return the unique ID for this sensor."""
        return f"{self.coordinator.serverip}-{self._device_id}"

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def device_info(self):
        """Return device information about this device."""
        if self._device_id is None:
            return None

        return {
            "identifiers": {(DOMAIN, self.coordinator.serverip)},
            "name": f"Promox Server ({self.coordinator.serverip})",
            #"hw_version": self.coordinator.data["system"]["hardware"],
            "sw_version": "",
            "manufacturer": "Proxmox VE"
        }

