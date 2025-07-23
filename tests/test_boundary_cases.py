"""
Comprehensive boundary and edge case tests for marketplace simulation.
Tests numeric boundaries, extreme parameter values, and edge conditions.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
# import pytest  # Not available, using manual error checking
from market_sim.config import SimConfig
from market_sim.discrete import run_simulation, run_simulation_with_tracking
from market_sim.entities import Shift, Nurse, BookingEvent, SimulationResult
from market_sim.plots import calculate_shift_utilization, identify_interference_patterns


class TestBookingRateBoundaries:
    """Test booking rate stays within valid bounds [0.0, 1.0]."""
    
    def test_booking_rate_lower_bound(self):
        """Test booking rate >= 0.0 in all scenarios."""
        # Zero arrival rate
        config = SimConfig(horizon=100, lambda_c=0.0, random_seed=42)
        result = run_simulation(config)
        assert result.booking_rate >= 0.0
        assert result.booking_rate == 0.0  # No arrivals = no bookings
        
        # Very low arrival rate
        config = SimConfig(horizon=100, lambda_c=0.01, random_seed=42)
        result = run_simulation(config)
        assert result.booking_rate >= 0.0
    
    def test_booking_rate_upper_bound(self):
        """Test booking rate <= 1.0 in all scenarios."""
        # Very high arrival rate
        config = SimConfig(horizon=100, lambda_c=5.0, mu=0.1, random_seed=42)
        result = run_simulation(config)
        assert result.booking_rate <= 1.0
        
        # Extreme arrival rate
        config = SimConfig(horizon=50, lambda_c=10.0, mu=0.1, random_seed=42)
        result = run_simulation(config)
        assert result.booking_rate <= 1.0
        
        # Perfect matching scenario
        config = SimConfig(horizon=100, lambda_c=1.0, mu=100.0, n_shifts=50, random_seed=42)
        result = run_simulation(config)
        assert result.booking_rate <= 1.0
    
    def test_booking_rate_mathematical_consistency(self):
        """Test that booking_rate = total_bookings / total_arrivals always holds."""
        test_configs = [
            SimConfig(horizon=50, lambda_c=0.1, random_seed=42),
            SimConfig(horizon=100, lambda_c=0.5, random_seed=42),
            SimConfig(horizon=200, lambda_c=1.0, random_seed=42),
            SimConfig(horizon=50, lambda_c=2.0, random_seed=42)
        ]
        
        for config in test_configs:
            result = run_simulation(config)
            if result.total_arrivals > 0:
                expected_rate = result.total_bookings / result.total_arrivals
                assert abs(result.booking_rate - expected_rate) < 1e-10
            else:
                assert result.booking_rate == 0.0


class TestTreatmentProbabilityBoundaries:
    """Test treatment_prob edge cases and boundaries."""
    
    def test_treatment_prob_zero(self):
        """Test treatment_prob = 0.0 (no treated shifts)."""
        config = SimConfig(horizon=100, treatment_prob=0.0, random_seed=42)
        result, states, shifts = run_simulation_with_tracking(config)
        
        # No shifts should be treated
        treated_shifts = [s for s in shifts if s.is_treated]
        assert len(treated_shifts) == 0
        
        # All bookings should be control
        treated_bookings = [e for e in result.booking_events if e.shift_treated]
        assert len(treated_bookings) == 0
        assert result.treated_bookings == 0
        assert result.control_bookings == result.total_bookings
    
    def test_treatment_prob_one(self):
        """Test treatment_prob = 1.0 (all shifts treated)."""
        config = SimConfig(horizon=100, treatment_prob=1.0, random_seed=42)
        result, states, shifts = run_simulation_with_tracking(config)
        
        # All shifts should be treated
        treated_shifts = [s for s in shifts if s.is_treated]
        assert len(treated_shifts) == config.n_shifts
        
        # All bookings should be treated
        control_bookings = [e for e in result.booking_events if not e.shift_treated]
        assert len(control_bookings) == 0
        assert result.control_bookings == 0
        assert result.treated_bookings == result.total_bookings
    
    def test_treatment_prob_boundary_values(self):
        """Test treatment_prob at various boundary values."""
        boundary_values = [0.001, 0.1, 0.5, 0.9, 0.999]
        
        for prob in boundary_values:
            config = SimConfig(horizon=50, treatment_prob=prob, n_shifts=10, random_seed=42)
            result, states, shifts = run_simulation_with_tracking(config)
            
            # Check that treatment assignment is within reasonable bounds
            treated_count = sum(1 for s in shifts if s.is_treated)
            expected_treated = prob * config.n_shifts
            
            # Allow for some random variation (binomial distribution)
            # Should be within 3 standard deviations for 99.7% confidence
            std_dev = np.sqrt(config.n_shifts * prob * (1 - prob))
            tolerance = 3 * std_dev + 1  # +1 for small sample sizes
            
            assert abs(treated_count - expected_treated) <= tolerance
    
    def test_treatment_prob_invalid_values(self):
        """Test that invalid treatment_prob values raise errors."""
        # Test negative value
        try:
            SimConfig(treatment_prob=-0.1)
            assert False, "Should have raised ValueError for negative treatment_prob"
        except ValueError:
            pass
        
        # Test value > 1
        try:
            SimConfig(treatment_prob=1.1)
            assert False, "Should have raised ValueError for treatment_prob > 1"
        except ValueError:
            pass
        
        # Test infinity
        try:
            SimConfig(treatment_prob=float('inf'))
            assert False, "Should have raised ValueError for infinite treatment_prob"
        except ValueError:
            pass
        
        # Test NaN
        try:
            SimConfig(treatment_prob=float('nan'))
            assert False, "Should have raised ValueError for NaN treatment_prob"
        except ValueError:
            pass


class TestParameterBoundaries:
    """Test other parameter boundary conditions."""
    
    def test_lambda_c_boundaries(self):
        """Test lambda_c (arrival rate) boundary conditions."""
        # Zero arrival rate
        config = SimConfig(lambda_c=0.0, horizon=50, random_seed=42)
        result = run_simulation(config)
        assert result.total_arrivals == 0
        assert result.total_bookings == 0
        assert result.booking_rate == 0.0
        
        # Very small arrival rate
        config = SimConfig(lambda_c=0.001, horizon=1000, random_seed=42)
        result = run_simulation(config)
        assert result.booking_rate >= 0.0
        assert result.booking_rate <= 1.0
        
        # Large arrival rate
        config = SimConfig(lambda_c=10.0, horizon=50, random_seed=42)
        result = run_simulation(config)
        assert result.booking_rate >= 0.0
        assert result.booking_rate <= 1.0
    
    def test_mu_boundaries(self):
        """Test mu (reopening rate) boundary conditions."""
        # Very slow reopening (mu close to 0)
        config = SimConfig(mu=0.001, horizon=100, lambda_c=0.5, random_seed=42)
        result = run_simulation(config)
        assert result.booking_rate >= 0.0
        assert result.booking_rate <= 1.0
        
        # Very fast reopening (high mu)
        config = SimConfig(mu=100.0, horizon=50, lambda_c=0.5, random_seed=42)
        result = run_simulation(config)
        assert result.booking_rate >= 0.0
        assert result.booking_rate <= 1.0
    
    def test_k_boundaries(self):
        """Test k (consideration set size) boundary conditions."""
        # k = 1 (nurses see only 1 shift)
        config = SimConfig(k=1, horizon=50, n_shifts=10, random_seed=42)
        result = run_simulation(config)
        
        # All choice positions should be 0
        positions = [e.choice_position for e in result.booking_events]
        assert all(pos == 0 for pos in positions)
        
        # k larger than number of shifts
        config = SimConfig(k=50, horizon=50, n_shifts=10, random_seed=42)
        result = run_simulation(config)
        
        # Choice positions should be <= 9 (max shift index)
        positions = [e.choice_position for e in result.booking_events]
        assert all(pos < 10 for pos in positions)
    
    def test_n_shifts_boundaries(self):
        """Test n_shifts boundary conditions."""
        # Single shift
        config = SimConfig(n_shifts=1, horizon=50, k=1, random_seed=42)
        result, states, shifts = run_simulation_with_tracking(config)
        
        assert len(shifts) == 1
        # All bookings should be for shift 0
        shift_ids = [e.shift_id for e in result.booking_events]
        assert all(sid == 0 for sid in shift_ids)
        
        # Large number of shifts
        config = SimConfig(n_shifts=100, horizon=50, random_seed=42)
        result, states, shifts = run_simulation_with_tracking(config)
        assert len(shifts) == 100


class TestVisualizationBoundaries:
    """Test boundary conditions in visualization functions."""
    
    def test_utilization_boundaries(self):
        """Test shift utilization stays within [0.0, 1.0]."""
        # Create test scenario with various booking patterns
        shifts = [Shift(id=i, base_utility=1.0, is_treated=i%2==0) for i in range(5)]
        
        # No bookings
        utilization = calculate_shift_utilization([], shifts, horizon=100)
        assert all(0.0 <= util <= 1.0 for util in utilization.values())
        assert all(util == 0.0 for util in utilization.values())
        
        # Many bookings (but still <= horizon)
        many_events = []
        for t in range(50):  # 50 bookings over 100 timesteps
            event = BookingEvent(
                timestamp=float(t), nurse_id=t, shift_id=0,
                nurse_treated=False, shift_treated=True,
                consideration_set_size=5, shift_utility=1.0, choice_position=0
            )
            many_events.append(event)
        
        utilization = calculate_shift_utilization(many_events, shifts, horizon=100)
        assert all(0.0 <= util <= 1.0 for util in utilization.values())
        assert utilization[0] == 0.5  # 50 bookings / 100 timesteps
        
        # Zero horizon edge case
        utilization = calculate_shift_utilization(many_events, shifts, horizon=0)
        assert all(util == 0.0 for util in utilization.values())
    
    def test_interference_detection_boundaries(self):
        """Test interference detection with boundary conditions."""
        shifts = [
            Shift(id=0, base_utility=1.0, is_treated=True),
            Shift(id=1, base_utility=1.0, is_treated=False)
        ]
        
        # No bookings
        patterns = identify_interference_patterns([], shifts)
        assert patterns['treated_booking_rate'] == 0.0
        assert patterns['control_booking_rate'] == 0.0
        assert patterns['rate_difference'] == 0.0
        assert not patterns['interference_detected']
        
        # Only treated bookings
        treated_only = [
            BookingEvent(timestamp=1.0, nurse_id=1, shift_id=0, 
                        nurse_treated=False, shift_treated=True,
                        consideration_set_size=2, shift_utility=1.0, choice_position=0)
        ]
        patterns = identify_interference_patterns(treated_only, shifts)
        assert patterns['treated_booking_rate'] == 1.0  # 1 booking / 1 treated shift
        assert patterns['control_booking_rate'] == 0.0  # 0 bookings / 1 control shift
        assert patterns['rate_difference'] == 1.0
        assert patterns['interference_detected']  # Large difference should trigger detection


class TestExtremePileupScenarios:
    """Test extreme scenarios that could cause numeric issues."""
    
    def test_extreme_high_demand(self):
        """Test scenario with extremely high demand."""
        config = SimConfig(
            horizon=20,
            lambda_c=50.0,  # Very high arrival rate
            mu=0.1,         # Very slow reopening
            n_shifts=5,     # Few shifts
            random_seed=42
        )
        
        result = run_simulation(config)
        
        # Should handle gracefully
        assert 0.0 <= result.booking_rate <= 1.0
        assert result.total_bookings <= result.total_arrivals
        assert result.treated_bookings + result.control_bookings == result.total_bookings
    
    def test_extreme_low_demand(self):
        """Test scenario with extremely low demand."""
        config = SimConfig(
            horizon=1000,
            lambda_c=0.001,  # Very low arrival rate
            mu=10.0,         # Fast reopening
            n_shifts=50,     # Many shifts
            random_seed=42
        )
        
        result = run_simulation(config)
        
        # Should handle gracefully
        assert 0.0 <= result.booking_rate <= 1.0
        assert result.total_bookings <= result.total_arrivals
    
    def test_instantaneous_reopening(self):
        """Test with very fast reopening (mu >> 1)."""
        config = SimConfig(
            horizon=100,
            lambda_c=1.0,
            mu=1000.0,  # Nearly instantaneous reopening
            random_seed=42
        )
        
        result = run_simulation(config)
        
        # With instant reopening, booking rate should be very high
        assert 0.0 <= result.booking_rate <= 1.0
        # Should approach 1.0 since shifts are always available
        assert result.booking_rate > 0.8  # Should be high with instant reopening


def run_all_boundary_tests():
    """Run all boundary and edge case tests."""
    print("Running Comprehensive Boundary and Edge Case Tests")
    print("=" * 60)
    
    test_classes = [
        TestBookingRateBoundaries,
        TestTreatmentProbabilityBoundaries,
        TestParameterBoundaries,
        TestVisualizationBoundaries,
        TestExtremePileupScenarios
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
                print(f"  ✓ {method_name}")
                total_passed += 1
            except Exception as e:
                print(f"  ✗ {method_name} FAILED: {e}")
                total_failed += 1
    
    print("\n" + "=" * 60)
    print(f"Boundary Test Results: {total_passed} passed, {total_failed} failed")
    
    if total_failed == 0:
        print("✓ ALL BOUNDARY TESTS PASSED!")
        return True
    else:
        print(f"⚠ {total_failed} boundary tests failed")
        return False


if __name__ == "__main__":
    success = run_all_boundary_tests()
    
    if success:
        print("\n🎉 All boundary and edge case tests validated!")
        print("Numeric boundaries are properly enforced:")
        print("• Booking rates stay within [0.0, 1.0]")
        print("• Treatment probabilities work at all boundary values")
        print("• Extreme parameter values handled gracefully")
        print("• Visualization functions respect numeric bounds")
    else:
        print("\n⚠ Some boundary tests failed - check implementation")