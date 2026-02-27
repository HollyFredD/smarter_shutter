"""Config flow for Smarter Shutter."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
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
    STOP_METHOD_STOP,
    STOP_METHOD_RESEND,
    DEFAULT_TRAVEL_TIME,
    DEFAULT_MOTOR_INERTIA,
    DEFAULT_STOP_METHOD,
    DIR_DOWN,
)
from .motor_helpers import async_activate_motor, async_stop_motor

_LOGGER = logging.getLogger(__name__)


def _timing_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Build the timing + stop method schema with optional defaults."""
    d = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_TRAVEL_TIME_UP,
                default=d.get(CONF_TRAVEL_TIME_UP, DEFAULT_TRAVEL_TIME),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1, max=300, step=0.5, unit_of_measurement="s",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_TRAVEL_TIME_DOWN,
                default=d.get(CONF_TRAVEL_TIME_DOWN, DEFAULT_TRAVEL_TIME),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1, max=300, step=0.5, unit_of_measurement="s",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(
                CONF_MOTOR_INERTIA,
                default=d.get(CONF_MOTOR_INERTIA, DEFAULT_MOTOR_INERTIA),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0, max=5, step=0.1, unit_of_measurement="s",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_STOP_METHOD,
                default=d.get(CONF_STOP_METHOD, DEFAULT_STOP_METHOD),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(
                            value=STOP_METHOD_STOP, label="stop_command"
                        ),
                        selector.SelectOptionDict(
                            value=STOP_METHOD_RESEND, label="resend_direction"
                        ),
                    ],
                    translation_key="stop_method",
                )
            ),
        }
    )


class SmarterShutterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Smarter Shutter."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}
        self._calibration_task: asyncio.Task | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 1: name and control mode."""
        if user_input is not None:
            self._data.update(user_input)
            if user_input[CONF_CONTROL_MODE] == MODE_SWITCHES:
                return await self.async_step_switches()
            return await self.async_step_cover()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME): str,
                    vol.Required(
                        CONF_CONTROL_MODE, default=MODE_SWITCHES
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(
                                    value=MODE_SWITCHES, label="switches_mode"
                                ),
                                selector.SelectOptionDict(
                                    value=MODE_COVER, label="cover_mode"
                                ),
                            ],
                            translation_key="control_mode",
                        )
                    ),
                }
            ),
        )

    async def async_step_switches(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 2a: select switch entities."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_timing()

        return self.async_show_form(
            step_id="switches",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_OPEN_SWITCH): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="switch")
                    ),
                    vol.Required(CONF_CLOSE_SWITCH): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="switch")
                    ),
                }
            ),
        )

    async def async_step_cover(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 2b: select cover entity."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_timing()

        return self.async_show_form(
            step_id="cover",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_COVER_ENTITY): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="cover")
                    ),
                }
            ),
        )

    async def async_step_timing(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 3: timing configuration."""
        errors = {}

        if user_input is not None:
            if user_input[CONF_TRAVEL_TIME_UP] <= 0:
                errors[CONF_TRAVEL_TIME_UP] = "invalid_time"
            if user_input[CONF_TRAVEL_TIME_DOWN] <= 0:
                errors[CONF_TRAVEL_TIME_DOWN] = "invalid_time"

            if not errors:
                self._data.update(user_input)
                if self._data[CONF_CONTROL_MODE] == MODE_SWITCHES:
                    unique_id = f"{self._data[CONF_OPEN_SWITCH]}_{self._data[CONF_CLOSE_SWITCH]}"
                else:
                    unique_id = self._data[CONF_COVER_ENTITY]
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                return await self.async_step_calibration()

        return self.async_show_form(
            step_id="timing",
            data_schema=_timing_schema(),
            errors=errors,
        )

    async def async_step_calibration(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 4: ask user to calibrate or skip."""
        if user_input is not None:
            if user_input.get("skip_calibration", False):
                return self._create_entry()
            return await self.async_step_calibration_progress()

        return self.async_show_form(
            step_id="calibration",
            data_schema=vol.Schema(
                {
                    vol.Optional("skip_calibration", default=False): bool,
                }
            ),
        )

    async def async_step_calibration_progress(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 5: close shutter with progress spinner."""
        travel_down = self._data.get(CONF_TRAVEL_TIME_DOWN, DEFAULT_TRAVEL_TIME)

        if self._calibration_task is None:
            self._calibration_task = self.hass.async_create_task(
                self._async_calibrate_close()
            )

        if not self._calibration_task.done():
            return self.async_show_progress(
                step_id="calibration_progress",
                progress_action="closing_shutter",
                description_placeholders={
                    "travel_time": str(int(travel_down)),
                },
                progress_task=self._calibration_task,
            )

        try:
            self._calibration_task.result()
        except Exception:
            _LOGGER.exception("Calibration failed")
            self._calibration_task = None
            return self.async_show_progress_done(
                next_step_id="calibration_failed",
            )

        self._calibration_task = None
        return self.async_show_progress_done(
            next_step_id="calibration_confirm",
        )

    async def _async_calibrate_close(self) -> None:
        """Background task: close the shutter and stop it."""
        travel_down = self._data.get(CONF_TRAVEL_TIME_DOWN, DEFAULT_TRAVEL_TIME)
        inertia = self._data.get(CONF_MOTOR_INERTIA, DEFAULT_MOTOR_INERTIA)
        stop_method = self._data.get(CONF_STOP_METHOD, DEFAULT_STOP_METHOD)
        control_mode = self._data[CONF_CONTROL_MODE]

        open_switch = self._data.get(CONF_OPEN_SWITCH)
        close_switch = self._data.get(CONF_CLOSE_SWITCH)
        cover_entity = self._data.get(CONF_COVER_ENTITY)

        await async_activate_motor(
            self.hass, control_mode, DIR_DOWN,
            open_switch, close_switch, cover_entity,
        )

        await asyncio.sleep(travel_down + inertia)

        await async_stop_motor(
            self.hass, control_mode, stop_method, DIR_DOWN,
            open_switch, close_switch, cover_entity,
        )

    async def async_step_calibration_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 6: user confirms the shutter is fully closed."""
        if user_input is not None:
            return self._create_entry()

        return self.async_show_form(
            step_id="calibration_confirm",
            data_schema=vol.Schema({}),
        )

    async def async_step_calibration_failed(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 7: calibration failed, retry or skip."""
        if user_input is not None:
            if user_input.get("skip_calibration", False):
                return self._create_entry()
            return await self.async_step_calibration_progress()

        return self.async_show_form(
            step_id="calibration_failed",
            data_schema=vol.Schema(
                {
                    vol.Optional("skip_calibration", default=False): bool,
                }
            ),
        )

    @callback
    def _create_entry(self) -> FlowResult:
        """Create the config entry."""
        return self.async_create_entry(
            title=self._data[CONF_NAME],
            data=self._data,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow handler."""
        return SmarterShutterOptionsFlow()


class SmarterShutterOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for reconfiguring timing."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage timing options."""
        errors = {}

        if user_input is not None:
            if user_input[CONF_TRAVEL_TIME_UP] <= 0:
                errors[CONF_TRAVEL_TIME_UP] = "invalid_time"
            if user_input[CONF_TRAVEL_TIME_DOWN] <= 0:
                errors[CONF_TRAVEL_TIME_DOWN] = "invalid_time"

            if not errors:
                return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options or self.config_entry.data

        return self.async_show_form(
            step_id="init",
            data_schema=_timing_schema(current),
            errors=errors,
        )
