"""
Visualization functions for marketplace simulation.
"""

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from typing import List, Dict, Any, Tuple
from .config import SimConfig
from .entities import Shift, BookingEvent, SimulationState, SimulationResult


def setup_plot_style() -> None:
    """Set consistent matplotlib style for all plots."""
    plt.style.use('default')
    sns.set_palette("husl")
    plt.rcParams.update({
        'figure.figsize': (10, 6),
        'font.size': 11,
        'axes.grid': True,
        'grid.alpha': 0.3
    })


def plot_availability_heatmap(
    simulation_states: List[SimulationState],
    shifts: List[Shift],
    config: SimConfig,
    figsize: Tuple[int, int] = (12, 8)
) -> plt.Figure:
    """
    Create shift availability heatmap.
    
    Shows shift availability over time - treated shifts should show darker bands
    (filled more often) if interference is working properly.
    """
    setup_plot_style()
    
    fig, ax = plt.subplots(figsize=figsize)
    
    # Create matrix: rows = shifts, cols = time
    n_shifts = len(shifts)
    n_timesteps = len(simulation_states)
    
    # Initialize heatmap data (0 = open, 1 = filled)
    heatmap_data = np.zeros((n_shifts, n_timesteps))
    
    # Fill in the data
    for t, state in enumerate(simulation_states):
        for shift_id in range(n_shifts):
            # 1 if filled, 0 if open
            heatmap_data[shift_id, t] = 1 if state.shift_statuses[shift_id] == "filled" else 0
    
    # Create the heatmap
    im = ax.imshow(heatmap_data, cmap='RdYlBu_r', aspect='auto', interpolation='nearest')
    
    # Set labels and title
    ax.set_xlabel('Time (simulation steps)')
    ax.set_ylabel('Shift ID')
    ax.set_title('Shift Availability Over Time\n(Dark = Filled, Light = Open)')
    
    # Add colorbar
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Status (0=Open, 1=Filled)')
    
    # Mark treated vs control shifts on y-axis
    treated_shifts = [i for i, shift in enumerate(shifts) if shift.is_treated]
    control_shifts = [i for i, shift in enumerate(shifts) if not shift.is_treated]
    
    # Color y-tick labels
    yticks = list(range(0, n_shifts, max(1, n_shifts // 10)))  # Show max 10 ticks
    ax.set_yticks(yticks)
    ax.set_yticklabels([f"S{i}" for i in yticks])
    
    # Add legend showing treatment status
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='red', alpha=0.3, label=f'Treated ({len(treated_shifts)} shifts)'),
        Patch(facecolor='blue', alpha=0.3, label=f'Control ({len(control_shifts)} shifts)')
    ]
    ax.legend(handles=legend_elements, loc='upper right')
    
    plt.tight_layout()
    return fig


def plot_booking_timeline(
    booking_events: List[BookingEvent],
    shifts: List[Shift], 
    figsize: Tuple[int, int] = (12, 6)
) -> plt.Figure:
    """
    Create booking timeline scatter plot.
    
    Shows when and which shifts get booked, colored by treatment status.
    """
    setup_plot_style()
    
    fig, ax = plt.subplots(figsize=figsize)
    
    if not booking_events:
        ax.text(0.5, 0.5, 'No booking events to display', 
                transform=ax.transAxes, ha='center', va='center')
        ax.set_title('Booking Timeline (No Events)')
        return fig
    
    # Separate treated and control bookings
    treated_times = []
    treated_shifts = []
    control_times = []
    control_shifts = []
    
    for event in booking_events:
        if event.shift_treated:
            treated_times.append(event.timestamp)
            treated_shifts.append(event.shift_id)
        else:
            control_times.append(event.timestamp)
            control_shifts.append(event.shift_id)
    
    # Create scatter plots
    if treated_times:
        ax.scatter(treated_times, treated_shifts, c='red', alpha=0.6, 
                  s=30, label=f'Treated ({len(treated_times)} bookings)')
    
    if control_times:
        ax.scatter(control_times, control_shifts, c='blue', alpha=0.6, 
                  s=30, label=f'Control ({len(control_times)} bookings)')
    
    # Set labels and title
    ax.set_xlabel('Time (simulation steps)')
    ax.set_ylabel('Shift ID')
    ax.set_title('Booking Timeline')
    ax.legend()
    
    # Set y-axis to show all shifts
    if shifts:
        ax.set_ylim(-0.5, len(shifts) - 0.5)
    
    plt.tight_layout()
    return fig


def plot_running_booking_rates(
    booking_events: List[BookingEvent],
    total_arrivals_over_time: List[int],
    window_size: int = 50,
    figsize: Tuple[int, int] = (10, 6)
) -> plt.Figure:
    """
    Plot running booking rates for treated vs control.
    
    Uses a rolling window to smooth the visualization.
    """
    setup_plot_style()
    
    fig, ax = plt.subplots(figsize=figsize)
    
    if not booking_events:
        ax.text(0.5, 0.5, 'No booking events to display', 
                transform=ax.transAxes, ha='center', va='center')
        ax.set_title('Running Booking Rates (No Events)')
        return fig
    
    # Sort events by time
    events_by_time = sorted(booking_events, key=lambda x: x.timestamp)
    
    # Create time series data
    max_time = int(max(event.timestamp for event in events_by_time)) + 1
    treated_bookings_by_time = [0] * max_time
    control_bookings_by_time = [0] * max_time
    
    for event in events_by_time:
        time_idx = int(event.timestamp)
        if time_idx < max_time:
            if event.shift_treated:
                treated_bookings_by_time[time_idx] += 1
            else:
                control_bookings_by_time[time_idx] += 1
    
    # Calculate rolling averages
    def rolling_mean(data: List[float], window: int) -> Tuple[List[float], List[float]]:
        """Calculate rolling mean and corresponding time points."""
        if len(data) < window:
            return [], []
        
        means = []
        times = []
        
        for i in range(window, len(data) + 1):
            window_data = data[i-window:i]
            means.append(np.mean(window_data))
            times.append(i - window//2)  # Center the window
            
        return times, means
    
    # Calculate rolling booking rates
    treated_times, treated_rates = rolling_mean(treated_bookings_by_time, window_size)
    control_times, control_rates = rolling_mean(control_bookings_by_time, window_size)
    
    # Plot the lines
    if treated_times:
        ax.plot(treated_times, treated_rates, 'r-', linewidth=2, 
               label=f'Treated (window={window_size})', alpha=0.8)
    
    if control_times:
        ax.plot(control_times, control_rates, 'b-', linewidth=2, 
               label=f'Control (window={window_size})', alpha=0.8)
    
    # Set labels and title
    ax.set_xlabel('Time (simulation steps)')
    ax.set_ylabel('Booking Rate (bookings per timestep)')
    ax.set_title(f'Running Booking Rates (Window Size: {window_size})')
    ax.legend()
    
    plt.tight_layout()
    return fig


def create_summary_dashboard(
    result: SimulationResult,
    simulation_states: List[SimulationState],
    shifts: List[Shift],
    config: SimConfig
) -> plt.Figure:
    """
    Create 2x2 dashboard with all key visualizations.
    """
    setup_plot_style()
    
    fig = plt.figure(figsize=(16, 12))
    
    # Create subplots
    gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)
    
    # 1. Availability heatmap (top left)
    ax1 = fig.add_subplot(gs[0, 0])
    
    # Simplified heatmap code for subplot
    n_shifts = len(shifts)
    n_timesteps = len(simulation_states)
    heatmap_data = np.zeros((n_shifts, n_timesteps))
    
    for t, state in enumerate(simulation_states):
        for shift_id in range(n_shifts):
            heatmap_data[shift_id, t] = 1 if state.shift_statuses[shift_id] == "filled" else 0
    
    im1 = ax1.imshow(heatmap_data, cmap='RdYlBu_r', aspect='auto', interpolation='nearest')
    ax1.set_xlabel('Time')
    ax1.set_ylabel('Shift ID')
    ax1.set_title('Shift Availability Heatmap')
    
    # 2. Booking timeline (top right)
    ax2 = fig.add_subplot(gs[0, 1])
    
    if result.booking_events:
        treated_times = [e.timestamp for e in result.booking_events if e.shift_treated]
        treated_shifts = [e.shift_id for e in result.booking_events if e.shift_treated]
        control_times = [e.timestamp for e in result.booking_events if not e.shift_treated]
        control_shifts = [e.shift_id for e in result.booking_events if not e.shift_treated]
        
        if treated_times:
            ax2.scatter(treated_times, treated_shifts, c='red', alpha=0.6, s=20, label='Treated')
        if control_times:
            ax2.scatter(control_times, control_shifts, c='blue', alpha=0.6, s=20, label='Control')
        
        ax2.set_xlabel('Time')
        ax2.set_ylabel('Shift ID')
        ax2.set_title('Booking Timeline')
        ax2.legend()
        
        if shifts:
            ax2.set_ylim(-0.5, len(shifts) - 0.5)
    else:
        ax2.text(0.5, 0.5, 'No bookings', transform=ax2.transAxes, ha='center')
        ax2.set_title('Booking Timeline (No Events)')
    
    # 3. Availability over time (bottom left)
    ax3 = fig.add_subplot(gs[1, 0])
    
    times = [state.timestep for state in simulation_states]
    available_counts = [state.available_count for state in simulation_states]
    filled_counts = [state.filled_count for state in simulation_states]
    
    ax3.plot(times, available_counts, 'g-', label='Available', linewidth=2)
    ax3.plot(times, filled_counts, 'r-', label='Filled', linewidth=2)
    ax3.set_xlabel('Time')
    ax3.set_ylabel('Number of Shifts')
    ax3.set_title('Shift Availability Over Time')
    ax3.legend()
    
    # 4. Summary statistics (bottom right)
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.axis('off')  # Turn off axes for text display
    
    # Create summary text
    summary_text = f"""
Simulation Summary

Total Arrivals: {result.total_arrivals:,}
Total Bookings: {result.total_bookings:,}
Booking Rate: {result.booking_rate:.3f}

Treated Bookings: {result.treated_bookings:,}
Control Bookings: {result.control_bookings:,}

Configuration:
• Horizon: {config.horizon:,} steps
• λ (arrival rate): {config.lambda_c:.2f}
• μ (reopening rate): {config.mu:.2f}
• k (consideration set): {config.k}
• Shifts: {config.n_shifts}
    """
    
    ax4.text(0.1, 0.9, summary_text, transform=ax4.transAxes, 
            fontsize=11, verticalalignment='top', fontfamily='monospace')
    
    # Add overall title
    fig.suptitle('Marketplace Simulation Dashboard', fontsize=16, fontweight='bold')
    
    return fig


def calculate_shift_utilization(
    booking_events: List[BookingEvent],
    shifts: List[Shift],
    horizon: int
) -> Dict[int, float]:
    """
    Calculate utilization rate for each shift.
    
    Returns dictionary mapping shift_id to utilization rate (0-1).
    """
    utilization = {}
    
    for shift in shifts:
        shift_bookings = [e for e in booking_events if e.shift_id == shift.id]
        utilization_rate = len(shift_bookings) / horizon if horizon > 0 else 0.0
        utilization[shift.id] = min(utilization_rate, 1.0)  # Cap at 1.0
    
    return utilization


def identify_interference_patterns(
    booking_events: List[BookingEvent],
    shifts: List[Shift]
) -> Dict[str, Any]:
    """
    Analyze patterns that indicate interference.
    
    Returns dictionary with interference indicators.
    """
    if not booking_events:
        return {
            'total_bookings': 0,
            'treated_booking_rate': 0.0,
            'control_booking_rate': 0.0,
            'rate_difference': 0.0,
            'interference_detected': False
        }
    
    # Calculate basic rates
    treated_bookings = [e for e in booking_events if e.shift_treated]
    control_bookings = [e for e in booking_events if not e.shift_treated]
    
    total_treated_shifts = sum(1 for shift in shifts if shift.is_treated)
    total_control_shifts = len(shifts) - total_treated_shifts
    
    # Rates per shift (to normalize for different numbers of treated/control shifts)
    treated_rate = len(treated_bookings) / max(total_treated_shifts, 1)
    control_rate = len(control_bookings) / max(total_control_shifts, 1)
    
    rate_difference = treated_rate - control_rate
    
    # Simple interference detection: treated shifts should have higher booking rates
    interference_detected = rate_difference > 0.1  # Threshold can be adjusted
    
    return {
        'total_bookings': len(booking_events),
        'treated_bookings': len(treated_bookings),
        'control_bookings': len(control_bookings),
        'treated_booking_rate': treated_rate,
        'control_booking_rate': control_rate,
        'rate_difference': rate_difference,
        'interference_detected': interference_detected,
        'treated_shifts': total_treated_shifts,
        'control_shifts': total_control_shifts
    }