"""
Core entity classes for marketplace simulation.
"""

from dataclasses import dataclass
import numpy as np
from typing import Optional


@dataclass
class Shift:
    """Represents a shift in the marketplace that nurses can book."""
    
    id: int
    base_utility: float
    is_treated: bool
    status: str = "open"  # "open" or "filled"
    filled_until: float = 0.0  # time when shift becomes available again
    
    def __post_init__(self):
        """Validate shift parameters."""
        if self.status not in ["open", "filled"]:
            raise ValueError("status must be 'open' or 'filled'")
    
    def is_available(self, current_time: float) -> bool:
        """Check if shift is available for booking at current time."""
        return self.status == "open" and current_time >= self.filled_until
    
    def book_shift(self, current_time: float, mu: float) -> None:
        """Book the shift and set reopening time."""
        self.status = "filled"
        # Exponential distribution for reopening time
        reopening_delay = np.random.exponential(1.0 / mu)
        self.filled_until = current_time + reopening_delay
    
    def check_reopening(self, current_time: float) -> bool:
        """Check if shift should reopen and update status if needed."""
        if self.status == "filled" and current_time >= self.filled_until:
            self.status = "open"
            return True
        return False


@dataclass
class Nurse:
    """Represents a nurse arriving at the marketplace."""
    
    id: int
    arrived_at: float
    is_treated: bool
    
    def __post_init__(self):
        """Validate nurse parameters."""
        if self.arrived_at < 0:
            raise ValueError("arrived_at must be non-negative")


@dataclass
class BookingEvent:
    """Records a booking event for analysis."""
    
    timestamp: float
    nurse_id: int
    shift_id: int
    nurse_treated: bool
    shift_treated: bool
    consideration_set_size: int
    shift_utility: float
    choice_position: int  # position in consideration set (0-indexed)


@dataclass
class SimulationState:
    """Captures the state of the simulation at a specific timestep."""
    
    timestep: int
    shift_statuses: list[str]  # Status of each shift at this timestep
    available_count: int
    filled_count: int
    

@dataclass
class SimulationResult:
    """Contains results from a complete simulation run."""
    
    booking_events: list[BookingEvent]
    total_arrivals: int
    total_bookings: int
    booking_rate: float
    treated_bookings: int
    control_bookings: int
    
    def __post_init__(self):
        """Calculate derived metrics."""
        if self.total_arrivals > 0:
            self.booking_rate = self.total_bookings / self.total_arrivals
        else:
            self.booking_rate = 0.0