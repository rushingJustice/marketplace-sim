"""
Choice model mechanics for marketplace simulation.
"""

import numpy as np
from typing import List, Optional, Tuple
from .entities import Shift, Nurse, BookingEvent
from .config import SimConfig


def get_available_shifts(shifts: List[Shift], current_time: float) -> List[Shift]:
    """Filter shifts to only those available for booking."""
    return [shift for shift in shifts if shift.is_available(current_time)]


def select_consideration_set(
    shifts: List[Shift], 
    config: SimConfig,
    nurse: Optional[Nurse] = None
) -> List[Shift]:
    """
    Select top-k shifts for consideration set.
    
    Treatment ranking: treated shifts sort first, then by base_utility (descending).
    For Stage 1, we use listing randomization (shift treatment only).
    """
    if not shifts:
        return []
    
    # Sort: treated shifts first, then by utility (descending)
    def sort_key(shift: Shift) -> Tuple[int, float]:
        # Return (1, utility) for treated, (0, utility) for control
        # This puts treated shifts first (1 > 0), then sorts by utility within each group
        return (1 if shift.is_treated else 0, shift.base_utility)
    
    sorted_shifts = sorted(shifts, key=sort_key, reverse=True)
    
    # Take top k shifts
    k = min(config.k, len(sorted_shifts))
    return sorted_shifts[:k]


def calculate_choice_probabilities(
    consideration_set: List[Shift], 
    config: SimConfig
) -> np.ndarray:
    """
    Calculate choice probabilities using position-weighted multinomial logit.
    
    prob[i] = position_weights[i] * exp(utility[i]) / sum_all
    """
    if not consideration_set:
        return np.array([])
    
    n_shifts = len(consideration_set)
    
    # Get position weights (pad or truncate as needed)
    weights = config.position_weights[:n_shifts]
    if len(weights) < n_shifts:
        # Extend with last weight if we need more positions
        last_weight = config.position_weights[-1] if config.position_weights else 0.1
        weights.extend([last_weight] * (n_shifts - len(weights)))
    
    weights = np.array(weights)
    
    # Calculate utilities and probabilities
    utilities = np.array([shift.base_utility for shift in consideration_set])
    
    # Position-weighted logit: weight[i] * exp(utility[i])
    weighted_utilities = weights * np.exp(utilities)
    
    # Normalize to probabilities
    total = np.sum(weighted_utilities)
    if total == 0:
        # If all weights are zero, uniform choice
        return np.ones(n_shifts) / n_shifts
    
    probabilities = weighted_utilities / total
    return probabilities


def make_choice(
    consideration_set: List[Shift], 
    config: SimConfig
) -> Optional[int]:
    """
    Make choice from consideration set using multinomial selection.
    
    Returns index of chosen shift in consideration_set, or None if no choice.
    """
    if not consideration_set:
        return None
    
    probabilities = calculate_choice_probabilities(consideration_set, config)
    
    if len(probabilities) == 0:
        return None
    
    # Use multinomial to select one shift
    try:
        choice_array = np.random.multinomial(1, probabilities)
        chosen_index = np.argmax(choice_array)
        return chosen_index
    except ValueError:
        # Handle edge case where probabilities don't sum to 1 due to numerical errors
        return np.random.choice(len(consideration_set))


def process_nurse_choice(
    nurse: Nurse,
    shifts: List[Shift], 
    config: SimConfig,
    current_time: float
) -> Optional[BookingEvent]:
    """
    Process a single nurse's choice through the complete pipeline.
    
    Returns BookingEvent if a booking was made, None otherwise.
    """
    # Get available shifts
    available_shifts = get_available_shifts(shifts, current_time)
    
    if not available_shifts:
        return None  # No shifts available
    
    # Select consideration set
    consideration_set = select_consideration_set(available_shifts, config, nurse)
    
    if not consideration_set:
        return None  # No shifts in consideration set
    
    # Make choice
    choice_index = make_choice(consideration_set, config)
    
    if choice_index is None:
        return None  # No choice made
    
    # Book the chosen shift
    chosen_shift = consideration_set[choice_index]
    chosen_shift.book_shift(current_time, config.mu)
    
    # Create booking event record
    booking_event = BookingEvent(
        timestamp=current_time,
        nurse_id=nurse.id,
        shift_id=chosen_shift.id,
        nurse_treated=nurse.is_treated,
        shift_treated=chosen_shift.is_treated,
        consideration_set_size=len(consideration_set),
        shift_utility=chosen_shift.base_utility,
        choice_position=choice_index
    )
    
    return booking_event


def update_shift_statuses(shifts: List[Shift], current_time: float) -> int:
    """
    Update all shift statuses, reopening shifts that should be available.
    
    Returns number of shifts that reopened.
    """
    reopened_count = 0
    for shift in shifts:
        if shift.check_reopening(current_time):
            reopened_count += 1
    
    return reopened_count