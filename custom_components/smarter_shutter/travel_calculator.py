"""Travel calculator for time-based cover position tracking."""

from __future__ import annotations

import time
from typing import Callable

from .const import DIR_UP, DIR_DOWN


class TravelCalculator:
    """Calculate cover position based on elapsed travel time."""

    def __init__(
        self,
        travel_time_up: float,
        travel_time_down: float,
        motor_inertia: float = 0.3,
        time_fn: Callable[[], float] | None = None,
    ) -> None:
        """Initialize the calculator."""
        if travel_time_up <= 0:
            raise ValueError(f"travel_time_up must be positive, got {travel_time_up}")
        if travel_time_down <= 0:
            raise ValueError(f"travel_time_down must be positive, got {travel_time_down}")
        if motor_inertia < 0:
            raise ValueError(f"motor_inertia must be non-negative, got {motor_inertia}")

        self._travel_time_up = travel_time_up
        self._travel_time_down = travel_time_down
        self._motor_inertia = motor_inertia
        self._time_fn = time_fn or time.monotonic

        self._position: float = 0.0
        self._target_position: float | None = None
        self._direction: str | None = None
        self._travel_start: float | None = None
        self._start_position: float = 0.0

    @property
    def current_position(self) -> int:
        """Return current position as integer (0=closed, 100=open)."""
        return max(0, min(100, round(self._position)))

    @property
    def is_traveling(self) -> bool:
        """Return True if currently moving."""
        return self._direction is not None

    @property
    def direction(self) -> str | None:
        """Return current direction."""
        return self._direction

    @property
    def target_position(self) -> float | None:
        """Return the target position."""
        return self._target_position

    def set_position(self, position: int) -> None:
        """Set position directly (for state restoration)."""
        self._position = float(max(0, min(100, position)))

    def recalibrate(self, position: int) -> None:
        """Force position to a known value (end stop recalibration)."""
        self._position = float(position)
        self._direction = None
        self._travel_start = None
        self._target_position = None

    def start_travel(self, direction: str, target_position: float) -> None:
        """Start tracking a movement."""
        self._start_position = self._position
        self._direction = direction
        self._target_position = target_position
        self._travel_start = self._time_fn()

    def stop(self) -> None:
        """Stop movement and freeze position at current calculated value."""
        self.update_position()
        self._direction = None
        self._travel_start = None
        self._target_position = None

    def update_position(self) -> int:
        """Recalculate position based on elapsed time since travel start.

        This is a pure calculation - no side effects like recalibration.
        """
        if not self.is_traveling or self._travel_start is None:
            return self.current_position

        elapsed = self._time_fn() - self._travel_start
        effective_elapsed = max(0.0, elapsed - self._motor_inertia)

        if self._direction == DIR_UP:
            moved = (effective_elapsed / self._travel_time_up) * 100.0
            self._position = min(self._start_position + moved, 100.0)
        elif self._direction == DIR_DOWN:
            moved = (effective_elapsed / self._travel_time_down) * 100.0
            self._position = max(self._start_position - moved, 0.0)

        return self.current_position

    def time_to_position(self, target: float) -> float:
        """Calculate time needed to reach target from current position."""
        distance = abs(target - self._position)
        if distance == 0:
            return 0.0

        if target > self._position:
            travel_time = self._travel_time_up
        else:
            travel_time = self._travel_time_down

        return (distance / 100.0) * travel_time + self._motor_inertia

