"""Config flow for Smarter Shutter."""

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
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
    DEFAULT_TRAVEL_TIME,
    DEFAULT_MOTOR_INERTIA,
)


class SmarterShutterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Smarter Shutter."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict = {}

    async def async_step_user(self, user_input=None):
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

    async def async_step_switches(self, user_input=None):
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

    async def async_step_cover(self, user_input=None):
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

    async def async_step_timing(self, user_input=None):
        """Step 3: timing configuration."""
        errors = {}

        if user_input is not None:
            if user_input[CONF_TRAVEL_TIME_UP] <= 0:
                errors[CONF_TRAVEL_TIME_UP] = "invalid_time"
            if user_input[CONF_TRAVEL_TIME_DOWN] <= 0:
                errors[CONF_TRAVEL_TIME_DOWN] = "invalid_time"

            if not errors:
                self._data.update(user_input)
                await self.async_set_unique_id(self._data[CONF_NAME])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=self._data[CONF_NAME],
                    data=self._data,
                )

        return self.async_show_form(
            step_id="timing",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_TRAVEL_TIME_UP, default=DEFAULT_TRAVEL_TIME
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1, max=300, step=0.5, unit_of_measurement="s",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Required(
                        CONF_TRAVEL_TIME_DOWN, default=DEFAULT_TRAVEL_TIME
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1, max=300, step=0.5, unit_of_measurement="s",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Optional(
                        CONF_MOTOR_INERTIA, default=DEFAULT_MOTOR_INERTIA
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0, max=5, step=0.1, unit_of_measurement="s",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow handler."""
        return SmarterShutterOptionsFlow()


class SmarterShutterOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for reconfiguring timing."""

    async def async_step_init(self, user_input=None):
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
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_TRAVEL_TIME_UP,
                        default=current.get(CONF_TRAVEL_TIME_UP, DEFAULT_TRAVEL_TIME),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1, max=300, step=0.5, unit_of_measurement="s",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Required(
                        CONF_TRAVEL_TIME_DOWN,
                        default=current.get(CONF_TRAVEL_TIME_DOWN, DEFAULT_TRAVEL_TIME),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1, max=300, step=0.5, unit_of_measurement="s",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Optional(
                        CONF_MOTOR_INERTIA,
                        default=current.get(CONF_MOTOR_INERTIA, DEFAULT_MOTOR_INERTIA),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0, max=5, step=0.1, unit_of_measurement="s",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                }
            ),
            errors=errors,
        )
