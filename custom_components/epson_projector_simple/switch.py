from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        EpsonSwitch(coordinator, entry.data["name"], "av_mute", "AV Mute", "MUTE ON", "MUTE OFF"),
        EpsonSwitch(coordinator, entry.data["name"], "freeze", "Freeze", "FREEZE ON", "FREEZE OFF")
    ])

class EpsonSwitch(CoordinatorEntity, SwitchEntity):
    def __init__(self, coordinator, device_name, switch_type, name_suffix, cmd_on, cmd_off):
        super().__init__(coordinator)
        self.switch_type = switch_type
        self.cmd_on = cmd_on
        self.cmd_off = cmd_off
        
        self._attr_name = f"{device_name} {name_suffix}"
        self._attr_unique_id = f"{coordinator.host}_{switch_type}"

    @property
    def is_on(self):
        return self.coordinator.data.get(self.switch_type, False)

    @property
    def available(self):
        # Switches only available when device is on and online
        return self.coordinator.data.get("available", False) and self.coordinator.data.get("power") == "on"

    async def async_turn_on(self, **kwargs):
        try:
            projector = self.coordinator.get_projector()
            await projector.send_command(self.cmd_on, timeout=5)
            await self.coordinator.async_request_refresh()
        except Exception:
            pass

    async def async_turn_off(self, **kwargs):
        try:
            projector = self.coordinator.get_projector()
            await projector.send_command(self.cmd_off, timeout=5)
            await self.coordinator.async_request_refresh()
        except Exception:
            pass
