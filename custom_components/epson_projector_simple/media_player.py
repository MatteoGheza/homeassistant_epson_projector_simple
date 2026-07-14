from epson_projector.const import TURN_OFF, TURN_ON
from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([EpsonMediaPlayer(coordinator, entry.data["name"])])

class EpsonMediaPlayer(CoordinatorEntity, MediaPlayerEntity):
    _attr_supported_features = MediaPlayerEntityFeature.TURN_ON | MediaPlayerEntityFeature.TURN_OFF  # noqa: E501
    _attr_device_class = "tv"

    def __init__(self, coordinator, name):
        super().__init__(coordinator)
        self._attr_name = name
        self._attr_unique_id = f"{coordinator.host}_media_player"

    @property
    def state(self):
        if not self.coordinator.data["available"]:
            return None # HA translates this to unavailable

        power = self.coordinator.data.get("power")
        if power == "on":
            return MediaPlayerState.ON
        if power in ["off", "warmup", "cooldown"]:
            return MediaPlayerState.OFF
        return None

    @property
    def available(self):
        return self.coordinator.data.get("available", False)

    async def async_turn_on(self):
        try:
            projector = self.coordinator.get_projector()
            await projector.send_command(TURN_ON, timeout=5)
            await self.coordinator.async_request_refresh()
        except Exception:  # noqa: BLE001, S110
            pass

    async def async_turn_off(self):
        try:
            projector = self.coordinator.get_projector()
            await projector.send_command(TURN_OFF, timeout=5)
            await self.coordinator.async_request_refresh()
        except Exception:  # noqa: BLE001, S110
            pass
