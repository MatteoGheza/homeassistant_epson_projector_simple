import logging
import asyncio
from datetime import timedelta

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.core import HomeAssistant

from epson_projector.projector_tcp import ProjectorTcp
from epson_projector.const import POWER, MUTE

from .const import DOMAIN

logging.getLogger("epson_projector").setLevel(logging.CRITICAL)

_LOGGER = logging.getLogger(__name__)

STATE_OFF = "off"
STATE_ON = "on"

POWER_CODE_MAP = {
    "00": STATE_OFF, 
    "01": STATE_ON, 
    "02": "warmup", 
    "03": "cooldown",
    "04": STATE_OFF, 
    "05": STATE_OFF, 
    "09": STATE_OFF,
}

class EpsonCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, host: str, password: str, name: str):
        super().__init__(
            hass,
            _LOGGER,
            name=name,
            update_interval=timedelta(seconds=60), # Default to offline polling
        )
        self.host = host
        self.password = password
        self._device_name = name
        self.projector = None # Start with None to force creation on first loop
        self.data = {
            "power": STATE_OFF,
            "av_mute": False,
            "freeze": False,
            "available": False
        }

    def get_projector(self):
        """Get the active projector client, or spin up a new one if missing."""
        if self.projector is None:
            self.projector = ProjectorTcp(host=self.host, password=self.password, on_imevent=self._on_imevent)
        return self.projector

    def _on_imevent(self, event):
        """Fire event if alarm or warning is present."""
        if event.alarm_type or event.warning_type:
            warning_val = event.warning_type.name if event.warning_type else None
            self.hass.bus.async_fire("epson_projector_imevent", {
                "host": self.host,
                "name": self._device_name,
                "alarm_type": event.alarm_type,
                "warning_type": warning_val
            })

    async def _async_cleanup_projector(self):
        """Tear down and clean up the stale connection."""
        if self.projector is not None:
            try:
                if hasattr(self.projector, "close"):
                    if asyncio.iscoroutinefunction(self.projector.close):
                        await self.projector.close()
                    else:
                        self.projector.close()
            except Exception as e:
                _LOGGER.debug("Error during projector socket cleanup: %s", e)
            finally:
                self.projector = None # Discard the instance

    async def _async_update_data(self):
        # Fetch or initialize a fresh client
        projector = self.get_projector()
        
        try:
            # Check power
            power_raw = await projector.get_property(POWER, timeout=5)
            power_state = POWER_CODE_MAP.get(power_raw, "unknown")
            
            self.data["available"] = True
            self.data["power"] = power_state

            if power_state == STATE_ON:
                # Device online and ON -> poll every 10 seconds
                self.update_interval = timedelta(seconds=10)
                
                mute_raw = await projector.get_property(MUTE, timeout=5)
                self.data["av_mute"] = (mute_raw == "ON")
                
                freeze_raw = await projector.get_property("FREEZE", timeout=5)
                self.data["freeze"] = (freeze_raw == "ON")
            else:
                # Device online but OFF -> poll every 20 seconds
                self.update_interval = timedelta(seconds=20)
                self.data["av_mute"] = False
                self.data["freeze"] = False

            return self.data

        except Exception:
            # Catch ALL connection, transport, or timeout exceptions safely
            _LOGGER.warning("Device offline")
            await self._async_cleanup_projector() # Cleanly dump the old socket
            self.update_interval = timedelta(seconds=60) # Recheck in 60s
            self.data["available"] = False
            return self.data
