"""
Test suite for Stage 2 visualization functions.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
import matplotlib.pyplot as plt
from market_sim.config import SimConfig
from market_sim.entities import Shift, Nurse, BookingEvent, SimulationState, SimulationResult
from market_sim.discrete import run_simulation_with_tracking
from market_sim.plots import (
    plot_availability_heatmap,
    plot_booking_timeline, 
    plot_running_booking_rates,
    create_summary_dashboard,
    calculate_shift_utilization,
    identify_interference_patterns,
    setup_plot_style
)


def test_setup_plot_style():
    """Test that plot style setup runs without errors."""
    setup_plot_style()
    print("✓ Plot style setup successful")


def test_simulation_state_class():
    """Test SimulationState class creation and validation."""
    state = SimulationState(
        timestep=10,
        shift_statuses=["open", "filled", "open"],
        available_count=2,
        filled_count=1
    )
    
    assert state.timestep == 10
    assert len(state.shift_statuses) == 3
    assert state.available_count == 2
    assert state.filled_count == 1
    print("✓ SimulationState class works correctly")


def test_run_simulation_with_tracking():
    """Test enhanced simulation function with tracking."""
    config = SimConfig(horizon=50, random_seed=42)
    result, states, shifts = run_simulation_with_tracking(config)
    
    # Check return types
    assert isinstance(result, SimulationResult)
    assert isinstance(states, list)
    assert isinstance(shifts, list)
    
    # Check state tracking
    assert len(states) == config.horizon
    assert all(isinstance(state, SimulationState) for state in states)
    
    # Check shifts
    assert len(shifts) == config.n_shifts
    assert all(isinstance(shift, Shift) for shift in shifts)
    
    print(f"✓ Enhanced simulation tracking works: {len(states)} states, {len(shifts)} shifts")


def test_plot_availability_heatmap():
    """Test availability heatmap generation."""
    config = SimConfig(horizon=20, n_shifts=5, random_seed=42)
    result, states, shifts = run_simulation_with_tracking(config)
    
    # Test basic functionality
    fig = plot_availability_heatmap(states, shifts, config, figsize=(8, 6))
    assert fig is not None
    
    # Test with empty states (edge case)
    empty_states = []
    try:
        fig_empty = plot_availability_heatmap(empty_states, shifts, config)
        # Should handle gracefully
    except Exception as e:
        print(f"Note: Empty states handling: {e}")
    
    plt.close('all')  # Clean up figures
    print("✓ Availability heatmap generation works")


def test_plot_booking_timeline():
    """Test booking timeline generation."""
    config = SimConfig(horizon=30, random_seed=42)
    result, states, shifts = run_simulation_with_tracking(config)
    
    # Test with booking events
    if result.booking_events:
        fig = plot_booking_timeline(result.booking_events, shifts, figsize=(8, 4))
        assert fig is not None
    
    # Test with no booking events (edge case)
    empty_events = []
    fig_empty = plot_booking_timeline(empty_events, shifts)
    assert fig_empty is not None
    
    plt.close('all')
    print("✓ Booking timeline generation works")


def test_plot_running_booking_rates():
    """Test running booking rates plot."""
    config = SimConfig(horizon=100, random_seed=42)
    result, states, shifts = run_simulation_with_tracking(config)
    
    # Create simple arrivals data
    total_arrivals = list(range(1, config.horizon + 1))
    
    if result.booking_events:
        fig = plot_running_booking_rates(
            result.booking_events, 
            total_arrivals, 
            window_size=10
        )
        assert fig is not None
    
    # Test with no events
    fig_empty = plot_running_booking_rates([], total_arrivals, window_size=10)
    assert fig_empty is not None
    
    plt.close('all')
    print("✓ Running booking rates plot works")


def test_create_summary_dashboard():
    """Test summary dashboard creation."""
    config = SimConfig(horizon=50, n_shifts=8, random_seed=42)
    result, states, shifts = run_simulation_with_tracking(config)
    
    fig = create_summary_dashboard(result, states, shifts, config)
    assert fig is not None
    
    # Check that it has the expected subplots (2x2 grid)
    axes = fig.get_axes()
    assert len(axes) >= 3  # At least 3 axes (one might be turned off for text)
    
    plt.close('all')
    print("✓ Summary dashboard creation works")


def test_calculate_shift_utilization():
    """Test shift utilization calculation."""
    # Create test data
    shifts = [
        Shift(id=0, base_utility=1.0, is_treated=True),
        Shift(id=1, base_utility=0.5, is_treated=False),
        Shift(id=2, base_utility=1.5, is_treated=True)
    ]
    
    booking_events = [
        BookingEvent(timestamp=1.0, nurse_id=1, shift_id=0, nurse_treated=False, 
                    shift_treated=True, consideration_set_size=3, shift_utility=1.0, choice_position=0),
        BookingEvent(timestamp=2.0, nurse_id=2, shift_id=0, nurse_treated=False, 
                    shift_treated=True, consideration_set_size=3, shift_utility=1.0, choice_position=0),
        BookingEvent(timestamp=3.0, nurse_id=3, shift_id=1, nurse_treated=False, 
                    shift_treated=False, consideration_set_size=3, shift_utility=0.5, choice_position=1)
    ]
    
    utilization = calculate_shift_utilization(booking_events, shifts, horizon=100)
    
    # Check results
    assert len(utilization) == 3
    assert utilization[0] == 0.02  # 2 bookings / 100 steps
    assert utilization[1] == 0.01  # 1 booking / 100 steps
    assert utilization[2] == 0.0   # 0 bookings / 100 steps
    
    # Test edge case: zero horizon
    util_zero = calculate_shift_utilization(booking_events, shifts, horizon=0)
    assert all(u == 0.0 for u in util_zero.values())
    
    print("✓ Shift utilization calculation works")


def test_identify_interference_patterns():
    """Test interference pattern identification."""
    # Create test data with clear interference
    shifts = [
        Shift(id=0, base_utility=1.0, is_treated=True),
        Shift(id=1, base_utility=1.0, is_treated=False),
        Shift(id=2, base_utility=1.0, is_treated=True),
        Shift(id=3, base_utility=1.0, is_treated=False)
    ]
    
    # Treated shifts get more bookings (interference effect)
    booking_events = [
        # Treated shift bookings (4 total)
        BookingEvent(timestamp=1.0, nurse_id=1, shift_id=0, nurse_treated=False, 
                    shift_treated=True, consideration_set_size=3, shift_utility=1.0, choice_position=0),
        BookingEvent(timestamp=2.0, nurse_id=2, shift_id=0, nurse_treated=False, 
                    shift_treated=True, consideration_set_size=3, shift_utility=1.0, choice_position=0),
        BookingEvent(timestamp=3.0, nurse_id=3, shift_id=2, nurse_treated=False, 
                    shift_treated=True, consideration_set_size=3, shift_utility=1.0, choice_position=0),
        BookingEvent(timestamp=4.0, nurse_id=4, shift_id=2, nurse_treated=False, 
                    shift_treated=True, consideration_set_size=3, shift_utility=1.0, choice_position=0),
        
        # Control shift bookings (1 total)
        BookingEvent(timestamp=5.0, nurse_id=5, shift_id=1, nurse_treated=False, 
                    shift_treated=False, consideration_set_size=3, shift_utility=1.0, choice_position=1)
    ]
    
    patterns = identify_interference_patterns(booking_events, shifts)
    
    # Check basic statistics
    assert patterns['total_bookings'] == 5
    assert patterns['treated_bookings'] == 4
    assert patterns['control_bookings'] == 1
    assert patterns['treated_shifts'] == 2
    assert patterns['control_shifts'] == 2
    
    # Check rates (4 bookings / 2 treated shifts = 2.0, 1 booking / 2 control shifts = 0.5)
    assert patterns['treated_booking_rate'] == 2.0
    assert patterns['control_booking_rate'] == 0.5
    assert patterns['rate_difference'] == 1.5
    
    # Should detect interference
    assert patterns['interference_detected'] == True
    
    # Test with no events
    empty_patterns = identify_interference_patterns([], shifts)
    assert empty_patterns['total_bookings'] == 0
    assert empty_patterns['interference_detected'] == False
    
    print("✓ Interference pattern identification works")


def test_visualization_data_consistency():
    """Test that visualization data is consistent with simulation results."""
    config = SimConfig(horizon=30, n_shifts=6, random_seed=42)
    result, states, shifts = run_simulation_with_tracking(config)
    
    # Check that state count matches horizon
    assert len(states) == config.horizon
    
    # Check that all booking events are within time bounds
    for event in result.booking_events:
        assert 0 <= event.timestamp < config.horizon
        assert 0 <= event.shift_id < config.n_shifts
    
    # Check that shift states are valid
    for state in states:
        assert len(state.shift_statuses) == config.n_shifts
        assert all(status in ["open", "filled"] for status in state.shift_statuses)
        assert state.available_count + state.filled_count == config.n_shifts
    
    # Check that final shifts match config
    assert len(shifts) == config.n_shifts
    
    print("✓ Visualization data consistency verified")


def test_plot_performance():
    """Test that plots generate within reasonable time."""
    import time
    
    config = SimConfig(horizon=100, n_shifts=10, random_seed=42)
    result, states, shifts = run_simulation_with_tracking(config)
    
    # Time each plot function
    start_time = time.time()
    fig1 = plot_availability_heatmap(states, shifts, config, figsize=(6, 4))
    heatmap_time = time.time() - start_time
    
    start_time = time.time()
    fig2 = plot_booking_timeline(result.booking_events, shifts, figsize=(6, 3))
    timeline_time = time.time() - start_time
    
    total_arrivals = list(range(1, config.horizon + 1))
    start_time = time.time()
    fig3 = plot_running_booking_rates(result.booking_events, total_arrivals)
    rates_time = time.time() - start_time
    
    start_time = time.time()
    fig4 = create_summary_dashboard(result, states, shifts, config)
    dashboard_time = time.time() - start_time
    
    plt.close('all')
    
    # Check performance (should be under 5 seconds total)
    total_time = heatmap_time + timeline_time + rates_time + dashboard_time
    
    print(f"Plot Performance:")
    print(f"  Heatmap: {heatmap_time:.3f}s")
    print(f"  Timeline: {timeline_time:.3f}s") 
    print(f"  Rates: {rates_time:.3f}s")
    print(f"  Dashboard: {dashboard_time:.3f}s")
    print(f"  Total: {total_time:.3f}s")
    
    assert total_time < 5.0, f"Plot generation too slow: {total_time:.3f}s"
    print("✓ Plot performance acceptable")


def run_all_stage2_tests():
    """Run all Stage 2 visualization tests."""
    print("Running Stage 2 Visualization Tests")
    print("=" * 50)
    
    test_functions = [
        test_setup_plot_style,
        test_simulation_state_class,
        test_run_simulation_with_tracking,
        test_plot_availability_heatmap,
        test_plot_booking_timeline,
        test_plot_running_booking_rates,
        test_create_summary_dashboard,
        test_calculate_shift_utilization,
        test_identify_interference_patterns,
        test_visualization_data_consistency,
        test_plot_performance
    ]
    
    passed = 0
    failed = 0
    
    for test_func in test_functions:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"✗ {test_func.__name__} FAILED: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"Stage 2 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✓ ALL STAGE 2 TESTS PASSED!")
        return True
    else:
        print(f"⚠ {failed} tests failed")
        return False


if __name__ == "__main__":
    success = run_all_stage2_tests()
    
    # Also run a comprehensive integration test
    print("\nRunning Integration Test...")
    try:
        config = SimConfig(horizon=50, n_shifts=8, lambda_c=0.6, random_seed=42)
        result, states, shifts = run_simulation_with_tracking(config)
        
        # Generate all visualizations
        fig1 = plot_availability_heatmap(states, shifts, config)
        fig2 = plot_booking_timeline(result.booking_events, shifts)
        fig3 = create_summary_dashboard(result, states, shifts, config)
        
        # Run analysis
        utilization = calculate_shift_utilization(result.booking_events, shifts, config.horizon)
        patterns = identify_interference_patterns(result.booking_events, shifts)
        
        plt.close('all')
        
        print("✓ Integration test passed - all components work together")
        
    except Exception as e:
        print(f"✗ Integration test failed: {e}")
        success = False
    
    if success:
        print("\n🎉 Stage 2 implementation fully validated!")
    else:
        print("\n⚠ Some issues found - check implementation")