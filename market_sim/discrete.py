"""
Main discrete-time simulation loop for marketplace simulation.
"""

import numpy as np
from typing import List, Optional
from .config import SimConfig
from .entities import Shift, Nurse, BookingEvent, SimulationResult, SimulationState
from .mechanics import process_nurse_choice, update_shift_statuses


def initialize_shifts(config: SimConfig) -> List[Shift]:
    """Create initial set of shifts with random utilities and treatment assignment."""
    shifts = []
    
    for shift_id in range(config.n_shifts):
        # Generate random base utility (could be made configurable)
        base_utility = np.random.normal(0, 1)  # Standard normal for now
        
        # Assign treatment randomly
        is_treated = np.random.random() < config.treatment_prob
        
        shift = Shift(
            id=shift_id,
            base_utility=base_utility,
            is_treated=is_treated,
            status="open",
            filled_until=0.0
        )
        shifts.append(shift)
    
    return shifts


def generate_arrivals(config: SimConfig, current_time: float) -> List[Nurse]:
    """Generate nurse arrivals for current timestep using Bernoulli process."""
    arrivals = []
    
    # Bernoulli arrivals with rate lambda_c per timestep
    n_arrivals = np.random.poisson(config.lambda_c)
    
    nurse_id_counter = int(current_time * 1000)  # Simple ID generation
    
    for i in range(n_arrivals):
        # Treatment assignment (for future use in customer randomization)
        is_treated = np.random.random() < config.treatment_prob
        
        nurse = Nurse(
            id=nurse_id_counter + i,
            arrived_at=current_time,
            is_treated=is_treated
        )
        arrivals.append(nurse)
    
    return arrivals


def simulate_timestep(
    shifts: List[Shift], 
    config: SimConfig, 
    current_time: float
) -> List[BookingEvent]:
    """Process one timestep of the simulation."""
    booking_events = []
    
    # Update shift statuses (reopen shifts that should be available)
    update_shift_statuses(shifts, current_time)
    
    # Generate arriving nurses
    arriving_nurses = generate_arrivals(config, current_time)
    
    # Process each nurse's choice
    for nurse in arriving_nurses:
        booking_event = process_nurse_choice(nurse, shifts, config, current_time)
        if booking_event:
            booking_events.append(booking_event)
    
    return booking_events


def run_simulation(config: Optional[SimConfig] = None) -> SimulationResult:
    """
    Run complete discrete-time simulation.
    
    Args:
        config: Simulation configuration. If None, uses default config.
        
    Returns:
        SimulationResult with all booking events and summary statistics.
    """
    if config is None:
        config = SimConfig()
    
    # Set random seed for reproducibility
    if config.random_seed is not None:
        np.random.seed(config.random_seed)
    
    # Initialize shifts
    shifts = initialize_shifts(config)
    
    # Track all booking events
    all_booking_events = []
    total_arrivals = 0
    
    # Main simulation loop
    for t in range(config.horizon):
        current_time = float(t)
        
        # Generate arrivals once per timestep
        arriving_nurses = generate_arrivals(config, current_time)
        total_arrivals += len(arriving_nurses)
        
        # Update shift statuses (reopen shifts that should be available)
        from .mechanics import update_shift_statuses, process_nurse_choice
        update_shift_statuses(shifts, current_time)
        
        # Process each nurse's choice
        for nurse in arriving_nurses:
            booking_event = process_nurse_choice(nurse, shifts, config, current_time)
            if booking_event:
                all_booking_events.append(booking_event)
    
    # Calculate summary statistics
    total_bookings = len(all_booking_events)
    treated_bookings = sum(1 for event in all_booking_events if event.shift_treated)
    control_bookings = total_bookings - treated_bookings
    
    # Create result object
    result = SimulationResult(
        booking_events=all_booking_events,
        total_arrivals=total_arrivals,
        total_bookings=total_bookings,
        booking_rate=0.0,  # Will be calculated in __post_init__
        treated_bookings=treated_bookings,
        control_bookings=control_bookings
    )
    
    return result


def run_simulation_with_tracking(
    config: Optional[SimConfig] = None
) -> tuple[SimulationResult, List[SimulationState], List[Shift]]:
    """
    Enhanced simulation that tracks states for visualization.
    
    Args:
        config: Simulation configuration. If None, uses default config.
        
    Returns:
        - SimulationResult: Standard results
        - List[SimulationState]: State at each timestep  
        - List[Shift]: Final shift states
    """
    if config is None:
        config = SimConfig()
    
    # Set random seed for reproducibility
    if config.random_seed is not None:
        np.random.seed(config.random_seed)
    
    # Initialize shifts
    shifts = initialize_shifts(config)
    
    # Track all booking events and states
    all_booking_events = []
    simulation_states = []
    total_arrivals = 0
    
    # Main simulation loop
    for t in range(config.horizon):
        current_time = float(t)
        
        # Generate arrivals once per timestep
        arriving_nurses = generate_arrivals(config, current_time)
        total_arrivals += len(arriving_nurses)
        
        # Update shift statuses (reopen shifts that should be available)
        from .mechanics import update_shift_statuses, process_nurse_choice
        update_shift_statuses(shifts, current_time)
        
        # Process each nurse's choice
        for nurse in arriving_nurses:
            booking_event = process_nurse_choice(nurse, shifts, config, current_time)
            if booking_event:
                all_booking_events.append(booking_event)
        
        # Capture simulation state after processing timestep
        shift_statuses = [shift.status for shift in shifts]
        available_count = sum(1 for shift in shifts if shift.is_available(current_time))
        filled_count = len(shifts) - available_count
        
        state = SimulationState(
            timestep=t,
            shift_statuses=shift_statuses,
            available_count=available_count,
            filled_count=filled_count
        )
        simulation_states.append(state)
    
    # Calculate summary statistics
    total_bookings = len(all_booking_events)
    treated_bookings = sum(1 for event in all_booking_events if event.shift_treated)
    control_bookings = total_bookings - treated_bookings
    
    # Create result object
    result = SimulationResult(
        booking_events=all_booking_events,
        total_arrivals=total_arrivals,
        total_bookings=total_bookings,
        booking_rate=0.0,  # Will be calculated in __post_init__
        treated_bookings=treated_bookings,
        control_bookings=control_bookings
    )
    
    return result, simulation_states, shifts


def print_simulation_summary(result: SimulationResult) -> None:
    """Print a summary of simulation results."""
    print(f"Simulation Summary:")
    print(f"  Total arrivals: {result.total_arrivals}")
    print(f"  Total bookings: {result.total_bookings}")
    print(f"  Booking rate: {result.booking_rate:.3f}")
    print(f"  Treated bookings: {result.treated_bookings}")
    print(f"  Control bookings: {result.control_bookings}")
    
    if result.total_bookings > 0:
        treated_rate = result.treated_bookings / result.total_bookings
        print(f"  Treatment rate in bookings: {treated_rate:.3f}")


# Simple CLI interface for testing
if __name__ == "__main__":
    print("Running marketplace simulation...")
    
    # Run with default configuration
    config = SimConfig(horizon=100, random_seed=42)
    result = run_simulation(config)
    
    print_simulation_summary(result)
    
    # Show first few booking events
    print(f"\nFirst 5 booking events:")
    for i, event in enumerate(result.booking_events[:5]):
        print(f"  {i+1}. t={event.timestamp:.1f}, nurse={event.nurse_id}, "
              f"shift={event.shift_id}, treated={event.shift_treated}")