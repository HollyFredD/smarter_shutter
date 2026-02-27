"""Shared motor control helpers for Smarter Shutter."""

from __future__ import annotations

from homeassistant.const import (
    SERVICE_OPEN_COVER,
    SERVICE_CLOSE_COVER,
    SERVICE_STOP_COVER,
)
from homeassistant.core import HomeAssistant

from .const import (
    MODE_SWITCHES,
    MODE_COVER,
    STOP_METHOD_RESEND,
    DIR_UP,
)


async def async_activate_motor(
    hass: HomeAssistant,
    control_mode: str,
    direction: str,
    open_switch: str | None,
    close_switch: str | None,
    cover_entity: str | None,
) -> None:
    """Start the motor in the given direction."""
    if control_mode == MODE_SWITCHES:
        if direction == DIR_UP:
            await _async_turn_off_switch(hass, close_switch)
            await _async_turn_on_switch(hass, open_switch)
        else:
            await _async_turn_off_switch(hass, open_switch)
            await _async_turn_on_switch(hass, close_switch)
    elif control_mode == MODE_COVER:
        service = SERVICE_OPEN_COVER if direction == DIR_UP else SERVICE_CLOSE_COVER
        await hass.services.async_call(
            "cover", service, {"entity_id": cover_entity},
        )


async def async_stop_motor(
    hass: HomeAssistant,
    control_mode: str,
    stop_method: str,
    direction: str | None,
    open_switch: str | None,
    close_switch: str | None,
    cover_entity: str | None,
) -> None:
    """Stop the motor.

    If stop_method is resend_direction, resend the current direction
    command to toggle the motor off. Otherwise use the stop command.
    """
    if control_mode == MODE_SWITCHES:
        await _async_turn_off_switch(hass, open_switch)
        await _async_turn_off_switch(hass, close_switch)
    elif control_mode == MODE_COVER:
        if stop_method == STOP_METHOD_RESEND and direction is not None:
            service = SERVICE_OPEN_COVER if direction == DIR_UP else SERVICE_CLOSE_COVER
            await hass.services.async_call(
                "cover", service, {"entity_id": cover_entity},
            )
        else:
            await hass.services.async_call(
                "cover", SERVICE_STOP_COVER, {"entity_id": cover_entity},
            )


async def _async_turn_on_switch(hass: HomeAssistant, entity_id: str | None) -> None:
    """Turn on a switch."""
    if entity_id is None:
        return
    await hass.services.async_call("switch", "turn_on", {"entity_id": entity_id})


async def _async_turn_off_switch(hass: HomeAssistant, entity_id: str | None) -> None:
    """Turn off a switch."""
    if entity_id is None:
        return
    await hass.services.async_call("switch", "turn_off", {"entity_id": entity_id})
