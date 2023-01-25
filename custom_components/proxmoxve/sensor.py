"""Sensor to read Proxmox VE Data"""
import logging
import re
from . import ProxmoxEntity
from homeassistant.helpers.entity import Entity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    entry = hass.data[DOMAIN][config_entry.entry_id]
    sensors = []
    for node in entry.data["nodes"]:
        sensors.append(ProxmoxSensor(entry, node, config_entry.options, "node"))
        for vm in node["vms"]:
            vm["node"] = node["node"]
            sensors.append(ProxmoxSensor(entry, vm, config_entry.options, "vm"))
            sensors.append(ProxmoxSensor(entry, vm, config_entry.options, "vm_mem"))
            sensors.append(ProxmoxSensor(entry, vm, config_entry.options, "vm_cpu"))
        for storage in node["storage"]:
            storage["node"] = node["node"]
            sensors.append(ProxmoxSensor(entry, storage, config_entry.options, "storage"))

    async_add_entities(sensors, True)

class ProxmoxSensor(
    ProxmoxEntity,
    Entity
):
    def __init__(self, coordinator, sensor, options, type):
        self.sensor = sensor
        self.options = options
        self.type = type
        self._attr = {}
        self.coordinator = coordinator
        if self.type == "node":
            self._device_id = "_node_" + self.sensor["node"]
        if self.type == "vm":
            self._device_id = "_vm_" + self.sensor["name"]
        if self.type == "vm_mem":
            self._device_id = "_vm_" + self.sensor["name"] + "_mem"
        if self.type == "vm_cpu":
            self._device_id = "_vm_" + self.sensor["name"] + "_cpu"
        if self.type == "storage":
            self._device_id = "_storage_" + self.sensor["storage"]

        self.coordinator_context = object()
    def get_value(self, ftype):
        if ftype == "state":
            if self.type == "node":
                for value in self.coordinator.data["nodes"]:
                    if value["node"] == self.sensor["node"]:
                        return value["status"]
            elif self.type == "vm":
                for value in self.coordinator.data["nodes"]:
                    if value["node"] == self.sensor["node"]:
                        for value2 in value["vms"]:
                            if value2["name"] == self.sensor["name"]:
                                return value2["status"]
            elif self.type == "vm_cpu":
                for value in self.coordinator.data["nodes"]:
                    if value["node"] == self.sensor["node"]:
                        for value2 in value["vms"]:
                            _LOGGER.debug(value2)
                            _LOGGER.debug(self.sensor["name"])
                            if value2["name"] == self.sensor["name"]:
                                return round(value2["cpu"] * 100,0)
            elif self.type == "vm_mem":
                for value in self.coordinator.data["nodes"]:
                    if value["node"] == self.sensor["node"]:
                        for value2 in value["vms"]:
                            _LOGGER.debug(value2)
                            _LOGGER.debug(self.sensor["name"])
                            if value2["name"] == self.sensor["name"]:
                                return round((value2["mem"] / value2["maxmem"]) * 100,0)     
            elif self.type == "storage":
                for value in self.coordinator.data["nodes"]:
                    if value["node"] == self.sensor["node"]:
                        for value2 in value["storage"]:
                            if value2["storage"] == self.sensor["storage"]:
                                used = value2["used"]
                                total = value2["total"]
                                percentage = (used / total) * 100
                                return round(percentage, 0)  

        if ftype == "attributes":
            if self.type == "node":
                for value in self.coordinator.data["nodes"]:
                    if value["node"] == self.sensor["node"]:
                        return value
            elif self.type == "vm":
                for value in self.coordinator.data["nodes"]:
                    if value["node"] == self.sensor["node"]:
                        for value2 in value["vms"]:
                            if value2["name"] == self.sensor["name"]:
                                return value2
            elif self.type == "storage":
                for value in self.coordinator.data["nodes"]:
                    if value["node"] == self.sensor["node"]:
                        for value2 in value["storage"]:
                            if value2["storage"] == self.sensor["storage"]:
                                return value2
            else:
                return None

        if ftype == "unit_of_measurement":
            if self.type == "vm_mem":
                return "%"
            elif self.type == "vm_cpu":
                return "%"
            elif self.type == "storage":
                return "%"
            else:
                return None
    @property
    def name(self):
        if self.type == "node":
            return "proxmox_node_" + self.sensor["node"]
        if self.type == "vm":
            return "proxmox_vm_" + self.sensor["name"]
        if self.type == "vm_cpu":
            return "proxmox_vm_" + self.sensor["name"] + "_cpu"
        if self.type == "vm_mem":
            return "proxmox_vm_" + self.sensor["name"] + "_mem"
        if self.type == "storage":
            return "proxmox_storage_" + self.sensor["storage"]

    @property
    def state(self):
        return self.get_value("state")

    @property
    def device_id(self):
        return self.device_id

    @property
    def extra_state_attributes(self):
        return self.get_value("attributes")

    @property
    def unit_of_measurement(self):
        return self.get_value("unit_of_measurement")

    @property
    def icon(self):
        return None