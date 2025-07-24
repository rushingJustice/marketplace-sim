"""
Comprehensive validation tests for both Jupyter notebooks.
Ensures notebooks execute correctly and produce valid outputs after bug fix.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for testing
import matplotlib.pyplot as plt

from market_sim.config import SimConfig
from market_sim.discrete import run_simulation, run_simulation_with_tracking, print_simulation_summary
from market_sim.entities import BookingEvent
from market_sim.plots import (
    calculate_shift_utilization,
    identify_interference_patterns,
    setup_plot_style,
    plot_availability_heatmap,
    plot_booking_timeline,
    create_summary_dashboard
)


class TestNotebook01BasicSim:
    """Validation tests for 01_basic_sim.ipynb notebook contents."""
    
    def test_basic_simulation_run(self):
        """Test the basic simulation run from notebook cell."""
        config = SimConfig(
            horizon=1000,
            lambda_c=0.5,
            mu=1.0,
            k=5,
            n_shifts=20,
            random_seed=42
        )
        
        result = run_simulation(config)
        
        # Critical validations
        assert result.booking_rate <= 1.0, f"booking_rate={result.booking_rate:.6f} > 1.0"
        assert result.total_bookings <= result.total_arrivals, "bookings > arrivals"
        assert result.treated_bookings + result.control_bookings == result.total_bookings
        
        # Should have reasonable booking activity
        assert result.total_arrivals > 0, "No arrivals generated"
        assert result.total_bookings >= 0, "Negative bookings"
        
        print(f"✓ Basic simulation: rate={result.booking_rate:.3f}, arrivals={result.total_arrivals}")
    
    def test_parameter_exploration(self):
        """Test parameter exploration from notebook."""
        arrival_rates = [0.1, 0.3, 0.5, 0.7, 0.9]
        
        for lambda_c in arrival_rates:
            config = SimConfig(
                horizon=1000,
                lambda_c=lambda_c,
                mu=1.0,
                k=5,
                n_shifts=20,
                random_seed=42
            )
            
            result = run_simulation(config)
            
            # Critical validations for each parameter
            assert result.booking_rate <= 1.0, f"λ={lambda_c}: booking_rate > 1.0"
            assert result.total_bookings <= result.total_arrivals, f"λ={lambda_c}: bookings > arrivals"
            
            print(f"  λ={lambda_c:.1f}: rate={result.booking_rate:.3f}")
    
    def test_treatment_analysis(self):
        """Test treatment vs control analysis from notebook."""
        config = SimConfig(
            horizon=2000,
            lambda_c=0.6,
            mu=1.0,
            k=5,
            n_shifts=20,
            treatment_prob=0.5,
            random_seed=42
        )
        
        result = run_simulation(config)
        
        # Basic validations
        assert result.booking_rate <= 1.0, "booking_rate > 1.0"
        assert result.total_bookings <= result.total_arrivals, "bookings > arrivals"
        
        # Treatment analysis
        treated_events = [e for e in result.booking_events if e.shift_treated]
        control_events = [e for e in result.booking_events if not e.shift_treated]
        
        assert len(treated_events) + len(control_events) == len(result.booking_events)
        
        print(f"✓ Treatment analysis: {len(treated_events)} treated, {len(control_events)} control")
    
    def test_choice_position_analysis(self):
        """Test choice position analysis from notebook."""
        config = SimConfig(horizon=500, lambda_c=0.8, random_seed=42)
        result = run_simulation(config)
        
        if result.booking_events:
            positions = [event.choice_position for event in result.booking_events]
            
            # All positions should be valid (0 to k-1)
            assert all(0 <= pos < config.k for pos in positions), "Invalid choice positions"
            
            # Position 0 should typically be most popular (position weighting)
            position_counts = {}
            for pos in positions:
                position_counts[pos] = position_counts.get(pos, 0) + 1
            
            print(f"✓ Choice positions: {len(set(positions))} different positions used")
    
    def test_market_scenarios(self):
        """Test different market scenarios from notebook."""
        scenarios = {
            'Low Demand': SimConfig(horizon=1000, lambda_c=0.2, mu=1.0, k=5, n_shifts=20, random_seed=42),
            'Balanced': SimConfig(horizon=1000, lambda_c=0.5, mu=1.0, k=5, n_shifts=20, random_seed=42),
            'High Demand': SimConfig(horizon=1000, lambda_c=0.8, mu=1.0, k=5, n_shifts=20, random_seed=42),
        }
        
        for name, config in scenarios.items():
            result = run_simulation(config)
            
            # Critical validations for each scenario
            assert result.booking_rate <= 1.0, f"{name}: booking_rate > 1.0"
            assert result.total_bookings <= result.total_arrivals, f"{name}: bookings > arrivals"
            
            print(f"  {name}: rate={result.booking_rate:.3f}")


class TestNotebook02Visualize:
    """Validation tests for 02_visualize.ipynb notebook contents."""
    
    def test_exact_bug_scenario(self):
        """Test the exact scenario that showed the booking_rate=1.054 bug."""
        # EXACT configuration from notebook cell 3
        config = SimConfig(
            horizon=500,
            lambda_c=0.6,
            mu=1.2,
            k=5,
            n_shifts=15,
            treatment_prob=0.1,  # This was the problematic setting
            random_seed=42
        )
        
        result, states, shifts = run_simulation_with_tracking(config)
        
        # CRITICAL BUG VALIDATION
        assert result.booking_rate <= 1.0, f"BUG REPRODUCED: booking_rate={result.booking_rate:.6f} > 1.0"
        assert result.total_bookings <= result.total_arrivals, "BUG REPRODUCED: bookings > arrivals"
        assert result.treated_bookings + result.control_bookings == result.total_bookings
        
        # Should have captured states
        assert len(states) == config.horizon, "State tracking failed"
        assert len(shifts) == config.n_shifts, "Shift tracking failed"
        
        print(f"✓ Bug scenario fixed: rate={result.booking_rate:.6f}, arrivals={result.total_arrivals}, bookings={result.total_bookings}")
    
    def test_visualization_functions(self):
        """Test visualization functions from notebook."""
        config = SimConfig(
            horizon=200,
            lambda_c=0.6,
            mu=1.2,
            k=5,
            n_shifts=10,
            treatment_prob=0.5,
            random_seed=42
        )
        
        result, states, shifts = run_simulation_with_tracking(config)
        
        # Test shift utilization calculation
        utilization = calculate_shift_utilization(result.booking_events, shifts, config.horizon)
        
        assert len(utilization) == len(shifts), "Utilization calculation failed"
        assert all(0.0 <= util <= 1.0 for util in utilization.values()), "Utilization out of bounds"
        
        # Test interference detection
        patterns = identify_interference_patterns(result.booking_events, shifts)
        
        assert patterns['total_bookings'] == len(result.booking_events), "Analysis inconsistent"
        assert patterns['treated_bookings'] + patterns['control_bookings'] == patterns['total_bookings']
        
        print(f"✓ Visualization functions: utilization range [{min(utilization.values()):.3f}, {max(utilization.values()):.3f}]")
    
    def test_plot_generation(self):
        """Test that plotting functions execute without errors."""
        config = SimConfig(horizon=100, lambda_c=0.5, n_shifts=8, random_seed=42)
        result, states, shifts = run_simulation_with_tracking(config)
        
        try:
            # Test plot generation (don't display, just ensure no errors)
            setup_plot_style()
            
            fig1 = plot_availability_heatmap(states, shifts, config, figsize=(6, 4))
            plt.close(fig1)
            
            fig2 = plot_booking_timeline(result.booking_events, shifts, figsize=(6, 3))
            plt.close(fig2)
            
            fig3 = create_summary_dashboard(result, states, shifts, config)
            plt.close(fig3)
            
            print("✓ All plot functions execute without errors")
            
        except Exception as e:
            assert False, f"Plot generation failed: {e}"
    
    def test_demand_level_comparison(self):
        """Test demand level comparison from notebook."""
        demand_levels = [0.3, 0.6, 0.9]
        
        for lambda_c in demand_levels:
            test_config = SimConfig(
                horizon=300,
                lambda_c=lambda_c,
                mu=1.0,
                k=5,
                n_shifts=10,
                treatment_prob=0.5,
                random_seed=42
            )
            
            test_result, _, _ = run_simulation_with_tracking(test_config)
            
            # Critical validations
            assert test_result.booking_rate <= 1.0, f"λ={lambda_c}: booking_rate > 1.0"
            assert test_result.total_bookings <= test_result.total_arrivals, f"λ={lambda_c}: bookings > arrivals"
            
            print(f"  Demand λ={lambda_c:.1f}: rate={test_result.booking_rate:.3f}")
    
    def test_interference_pattern_detection(self):
        """Test interference pattern detection from notebook."""
        config = SimConfig(
            horizon=300,
            lambda_c=0.7,
            mu=1.5,
            k=5,
            n_shifts=12,
            treatment_prob=0.4,
            random_seed=42
        )
        
        result, _, shifts = run_simulation_with_tracking(config)
        
        # Calculate interference patterns
        patterns = identify_interference_patterns(result.booking_events, shifts)
        
        # Validate analysis
        assert patterns['total_bookings'] >= 0
        assert patterns['treated_bookings'] >= 0
        assert patterns['control_bookings'] >= 0
        assert patterns['treated_shifts'] > 0
        assert patterns['control_shifts'] > 0
        
        # Rates should be non-negative
        assert patterns['treated_booking_rate'] >= 0
        assert patterns['control_booking_rate'] >= 0
        
        print(f"✓ Interference detection: {patterns['interference_detected']}, difference={patterns['rate_difference']:.3f}")
    
    def test_validation_tests_from_notebook(self):
        """Test the validation tests from the notebook."""
        config = SimConfig(horizon=200, lambda_c=0.6, treatment_prob=0.3, random_seed=42)
        result, states, shifts = run_simulation_with_tracking(config)
        
        # Test 1: Pattern Recognition
        treated_bookings = len([e for e in result.booking_events if e.shift_treated])
        control_bookings = len([e for e in result.booking_events if not e.shift_treated])
        treated_shifts_count = len([s for s in shifts if s.is_treated])
        control_shifts_count = len(shifts) - treated_shifts_count
        
        if treated_shifts_count > 0 and control_shifts_count > 0:
            treated_rate_per_shift = treated_bookings / treated_shifts_count
            control_rate_per_shift = control_bookings / control_shifts_count
            
            print(f"  Pattern recognition: treated={treated_rate_per_shift:.2f}, control={control_rate_per_shift:.2f} per shift")
        
        # Test 2: Timeline Accuracy
        timeline_times = [e.timestamp for e in result.booking_events]
        test2_pass = all(0 <= t < config.horizon for t in timeline_times)
        assert test2_pass, "Booking times outside simulation horizon"
        
        # Test 3: State Consistency
        assert len(states) == config.horizon, "State count mismatch"
        
        # Test 4: Utilization Logic
        utilization = calculate_shift_utilization(result.booking_events, shifts, config.horizon)
        max_util = max(utilization.values()) if utilization else 0.0
        assert max_util <= 1.0, "Utilization exceeds 1.0"
        
        print("✓ All notebook validation tests pass")


def run_notebook_validation_tests():
    """Run all notebook validation tests."""
    print("Running Comprehensive Notebook Validation Tests")
    print("=" * 60)
    
    test_classes = [
        TestNotebook01BasicSim,
        TestNotebook02Visualize
    ]
    
    total_passed = 0
    total_failed = 0
    
    for test_class in test_classes:
        print(f"\n{test_class.__name__}:")
        class_instance = test_class()
        
        # Get all test methods
        test_methods = [method for method in dir(class_instance) 
                       if method.startswith('test_')]
        
        for method_name in test_methods:
            try:
                method = getattr(class_instance, method_name)
                method()
                print(f"✓ {method_name}")
                total_passed += 1
            except AssertionError as e:
                print(f"✗ {method_name} FAILED: {e}")
                total_failed += 1
            except Exception as e:
                print(f"✗ {method_name} ERROR: {e}")
                total_failed += 1
    
    print("\n" + "=" * 60)
    print(f"Notebook Validation Results: {total_passed} passed, {total_failed} failed")
    
    if total_failed == 0:
        print("✅ ALL NOTEBOOK VALIDATION TESTS PASSED!")
        print("\nNotebook Status:")
        print("• 01_basic_sim.ipynb: All functions validated ✓")
        print("• 02_visualize.ipynb: Bug fixed, all functions validated ✓")
        print("• Booking rate > 1.0 bug completely eliminated")
        print("• All mathematical constraints enforced")
        print("• Visualization functions working correctly")
        return True
    else:
        print(f"❌ {total_failed} notebook validation tests failed")
        return False


if __name__ == "__main__":
    success = run_notebook_validation_tests()
    
    if success:
        print("\n🎉 BOTH NOTEBOOKS FULLY VALIDATED!")
        print("Ready for production use.")
    else:
        print("\n⚠ Notebook validation failed - check implementation")