"""Cover platform for Smarter Shutter."""

from __future__ import annotations

import time
from datetime import timedelta

from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_NAME,
    STATE_ON,
    STATE_OFF,
    STATE_OPEN,
    STATE_CLOSED,
    STATE_OPENING,
    STATE_CLOSING,
)
from homeassistant.core import HomeAssistant, callback, Event
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import (
    async_call_later,
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    MODE_SWITCHES,
    MODE_COVER,
    CONF_CONTROL_MODE,
    CONF_OPEN_SWITCH,
    CONF_CLOSE_SWITCH,
    CONF_COVER_ENTITY,
    CONF_TRAVEL_TIME_UP,
    CONF_TRAVEL_TIME_DOWN,
    CONF_MOTOR_INERTIA,
    CONF_STOP_METHOD,
    DEFAULT_TRAVEL_TIME,
    DEFAULT_MOTOR_INERTIA,
    DEFAULT_STOP_METHOD,
    DIR_UP,
    DIR_DOWN,
)
from .motor_helpers import async_activate_motor, async_stop_motor
from .travel_calculator import TravelCalculator

POSITION_UPDATE_INTERVAL = timedelta(seconds=1)
COMMAND_COOLDOWN_SECONDS = 2.0


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up cover entities from a config entry."""
    async_add_entities([SmarterShutterCover(hass, config_entry)])


class SmarterShutterCover(CoverEntity, RestoreEntity):
    """A cover with time-based position tracking."""

    _attr_device_class = CoverDeviceClass.SHUTTER
    _attr_has_entity_name = False
    _attr_should_poll = False
    _attr_assumed_state = True
    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
        | CoverEntityFeature.SET_POSITION
    )

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the cover."""
        self._config_entry = config_entry
        data = config_entry.data
        options = config_entry.options

        self._attr_name = data[CONF_NAME]
        self._attr_unique_id = config_entry.entry_id

        self._control_mode = data[CONF_CONTROL_MODE]
        self._open_switch = data.get(CONF_OPEN_SWITCH)
        self._close_switch = data.get(CONF_CLOSE_SWITCH)
        self._cover_entity = data.get(CONF_COVER_ENTITY)

        travel_up = options.get(
            CONF_TRAVEL_TIME_UP,
            data.get(CONF_TRAVEL_TIME_UP, DEFAULT_TRAVEL_TIME),
        )
        travel_down = options.get(
            CONF_TRAVEL_TIME_DOWN,
            data.get(CONF_TRAVEL_TIME_DOWN, DEFAULT_TRAVEL_TIME),
        )
        inertia = options.get(
            CONF_MOTOR_INERTIA,
            data.get(CONF_MOTOR_INERTIA, DEFAULT_MOTOR_INERTIA),
        )

        self._tc = TravelCalculator(travel_up, travel_down, inertia)

        self._stop_method = options.get(
            CONF_STOP_METHOD,
            data.get(CONF_STOP_METHOD, DEFAULT_STOP_METHOD),
        )

        self._last_command_time: float = 0.0
        self._unsub_position_updater = None
        self._unsub_stop_timer = None
        self._unsub_state_listeners: list = []

    @property
    def current_cover_position(self) -> int:
        """Return current position (0=closed, 100=open)."""
        return self._tc.current_position

    @property
    def is_closed(self) -> bool:
        """Return True if closed."""
        return self._tc.current_position == 0

    @property
    def is_opening(self) -> bool:
        """Return True if opening."""
        return self._tc.is_traveling and self._tc.direction == DIR_UP

    @property
    def is_closing(self) -> bool:
        """Return True if closing."""
        return self._tc.is_traveling and self._tc.direction == DIR_DOWN

    # --- State restoration ---

    async def async_added_to_hass(self) -> None:
        """Restore state and subscribe to source entity changes."""
        await super().async_added_to_hass()

        state = await self.async_get_last_state()
        if state is not None:
            pos = state.attributes.get("current_position")
            if pos is not None:
                self._tc.set_position(int(pos))

        self._setup_state_listeners()
        self._config_entry.async_on_unload(
            self._config_entry.add_update_listener(self._async_options_updated)
        )

    async def async_will_remove_from_hass(self) -> None:
        """Clean up on removal."""
        self._cancel_all_timers()
        self._remove_state_listeners()

    # --- Commands ---

    async def async_open_cover(self, **kwargs) -> None:
        """Open the cover fully."""
        await self.async_set_cover_position(position=100)

    async def async_close_cover(self, **kwargs) -> None:
        """Close the cover fully."""
        await self.async_set_cover_position(position=0)

    async def async_set_cover_position(self, **kwargs) -> None:
        """Move to a target position."""
        target = kwargs.get(ATTR_POSITION, 0)
        current = self._tc.current_position

        if target == current:
            return

        if self._tc.is_traveling:
            await self._async_stop_movement()

        if target > current:
            direction = DIR_UP
        else:
            direction = DIR_DOWN

        travel_time = self._tc.time_to_position(target)
        self._tc.start_travel(direction, target)

        self._last_command_time = time.monotonic()
        try:
            await self._async_activate_motor(direction)
        except Exception:
            self._tc.stop()
            raise

        self._start_position_updater()

        self._unsub_stop_timer = async_call_later(
            self.hass, travel_time, self._async_timed_stop
        )

        self.async_write_ha_state()

    async def async_stop_cover(self, **kwargs) -> None:
        """Stop the cover."""
        await self._async_stop_movement()

    # --- Motor control ---

    async def _async_activate_motor(self, direction: str) -> None:
        """Turn on the appropriate switch or send cover command."""
        await async_activate_motor(
            self.hass, self._control_mode, direction,
            self._open_switch, self._close_switch, self._cover_entity,
        )

    async def _async_stop_motor(self, direction: str | None = None) -> None:
        """Stop the motor."""
        await async_stop_motor(
            self.hass, self._control_mode, self._stop_method, direction,
            self._open_switch, self._close_switch, self._cover_entity,
        )

    # --- Movement tracking ---

    async def _async_stop_movement(self) -> None:
        """Stop current movement, update position, stop motor."""
        direction = self._tc.direction
        self._cancel_all_timers()
        self._tc.stop()

        self._last_command_time = time.monotonic()
        await self._async_stop_motor(direction)

        self.async_write_ha_state()

    @callback
    def _async_timed_stop(self, _now=None) -> None:
        """Called when the travel timer expires."""
        self._unsub_stop_timer = None
        self._stop_position_updater()

        target = self._tc.target_position
        direction = self._tc.direction
        self._tc.stop()

        if target == 100:
            self._tc.recalibrate(100)
        elif target == 0:
            self._tc.recalibrate(0)

        self.hass.async_create_task(self._async_guarded_stop_motor(direction))
        self.async_write_ha_state()

    async def _async_guarded_stop_motor(self, direction: str | None = None) -> None:
        """Stop motor while holding the command cooldown guard."""
        self._last_command_time = time.monotonic()
        await self._async_stop_motor(direction)

    @callback
    def _async_update_position(self, _now=None) -> None:
        """Periodic position update during movement."""
        self._tc.update_position()
        self.async_write_ha_state()

    @callback
    def _start_position_updater(self) -> None:
        """Start periodic position updates."""
        self._stop_position_updater()
        self._unsub_position_updater = async_track_time_interval(
            self.hass, self._async_update_position, POSITION_UPDATE_INTERVAL
        )

    @callback
    def _stop_position_updater(self) -> None:
        """Stop periodic position updates."""
        if self._unsub_position_updater is not None:
            self._unsub_position_updater()
            self._unsub_position_updater = None

    @callback
    def _cancel_all_timers(self) -> None:
        """Cancel all active timers."""
        self._stop_position_updater()
        if self._unsub_stop_timer is not None:
            self._unsub_stop_timer()
            self._unsub_stop_timer = None

    # --- External action detection ---

    def _setup_state_listeners(self) -> None:
        """Listen to source entity state changes for external actions."""
        entities = []
        if self._control_mode == MODE_SWITCHES:
            if self._open_switch:
                entities.append(self._open_switch)
            if self._close_switch:
                entities.append(self._close_switch)
        elif self._control_mode == MODE_COVER and self._cover_entity:
            entities.append(self._cover_entity)

        if entities:
            self._unsub_state_listeners.append(
                async_track_state_change_event(
                    self.hass, entities, self._async_source_state_changed
                )
            )

    def _remove_state_listeners(self) -> None:
        """Remove state change listeners."""
        for unsub in self._unsub_state_listeners:
            unsub()
        self._unsub_state_listeners.clear()

    @callback
    def _async_source_state_changed(self, event: Event) -> None:
        """Handle state change of source switch/cover."""
        if time.monotonic() - self._last_command_time < COMMAND_COOLDOWN_SECONDS:
            return

        entity_id = event.data.get("entity_id")
        new_state = event.data.get("new_state")
        old_state = event.data.get("old_state")

        if new_state is None or old_state is None:
            return

        if self._control_mode == MODE_SWITCHES:
            self._handle_switch_external_change(entity_id, old_state, new_state)
        elif self._control_mode == MODE_COVER:
            self._handle_cover_external_change(new_state)

    @callback
    def _start_external_travel(self, direction: str, target: float) -> None:
        """Begin tracking an externally triggered movement."""
        if self._tc.is_traveling:
            self._cancel_all_timers()
            self._tc.stop()
        self._tc.start_travel(direction, target)
        self._start_position_updater()
        self._unsub_stop_timer = async_call_later(
            self.hass,
            self._tc.time_to_position(target),
            self._async_timed_stop,
        )
        self.async_write_ha_state()

    @callback
    def _stop_external_travel(self) -> None:
        """Stop tracking when an external movement ends."""
        if self._tc.is_traveling:
            self._cancel_all_timers()
            self._tc.stop()
            self.async_write_ha_state()

    @callback
    def _handle_switch_external_change(self, entity_id, old_state, new_state) -> None:
        """Handle external switch toggle (wall switch / ZBMINIR2)."""
        new = new_state.state
        old = old_state.state

        if new == STATE_ON and old == STATE_OFF:
            if entity_id == self._open_switch:
                self._start_external_travel(DIR_UP, 100.0)
            elif entity_id == self._close_switch:
                self._start_external_travel(DIR_DOWN, 0.0)

        elif new == STATE_OFF and old == STATE_ON:
            self._stop_external_travel()

    @callback
    def _handle_cover_external_change(self, new_state) -> None:
        """Handle external cover entity state change."""
        state = new_state.state

        if state == STATE_OPENING:
            if not self._tc.is_traveling:
                self._start_external_travel(DIR_UP, 100.0)
        elif state == STATE_CLOSING:
            if not self._tc.is_traveling:
                self._start_external_travel(DIR_DOWN, 0.0)
        elif state in (STATE_OPEN, STATE_CLOSED):
            self._stop_external_travel()

    # --- Options update ---

    @staticmethod
    async def _async_options_updated(
        hass: HomeAssistant, entry: ConfigEntry
    ) -> None:
        """Handle options update - reload the entry."""
        await hass.config_entries.async_reload(entry.entry_id)
