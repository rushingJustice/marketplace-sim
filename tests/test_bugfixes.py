"""
Unit tests for specific bug fixes and critical issues.
CODER requirement: Every bug fix must have comprehensive unit tests.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
from market_sim.config import SimConfig
from market_sim.discrete import run_simulation, run_simulation_with_tracking, generate_arrivals
from market_sim.entities import SimulationResult


class TestBookingRateBugFix:
    """
    Tests for the critical booking rate > 1.0 bug fix.
    
    Bug: Double counting arrivals but processing different nurse sets led to 
    booking_rate > 1.0, which is mathematically impossible.
    
    Fix: Generate arrivals once per timestep and process the same set consistently.
    """
    
    def test_booking_rate_never_exceeds_one(self):
        """Test that booking rate never exceeds 1.0 under any conditions."""
        test_scenarios = [
            # High demand scenarios that previously caused booking_rate > 1.0
            SimConfig(lambda_c=5.0, horizon=50, mu=0.5, random_seed=42),
            SimConfig(lambda_c=10.0, horizon=100, mu=0.1, random_seed=123),
            SimConfig(lambda_c=20.0, horizon=30, mu=0.05, random_seed=456),
            
            # Extreme scenarios
            SimConfig(lambda_c=50.0, horizon=20, mu=0.01, n_shifts=5, random_seed=789),
            
            # Edge cases
            SimConfig(lambda_c=1.0, horizon=1000, mu=0.001, random_seed=999),
        ]
        
        for i, config in enumerate(test_scenarios):
            result = run_simulation(config)
            
            # Critical assertion: booking rate must never exceed 1.0
            assert result.booking_rate <= 1.0, (
                f"Scenario {i}: booking_rate={result.booking_rate:.6f} > 1.0 "
                f"(arrivals={result.total_arrivals}, bookings={result.total_bookings})"
            )
            
            # Additional consistency checks
            assert result.total_bookings <= result.total_arrivals, (
                f"Scenario {i}: More bookings ({result.total_bookings}) than arrivals ({result.total_arrivals})"
            )
            
            # Verify mathematical consistency
            if result.total_arrivals > 0:
                expected_rate = result.total_bookings / result.total_arrivals
                assert abs(result.booking_rate - expected_rate) < 1e-10, (
                    f"Scenario {i}: Booking rate calculation inconsistent"
                )
    
    def test_arrivals_bookings_consistency(self):
        """Test that arrivals and bookings are consistently counted."""
        config = SimConfig(lambda_c=3.0, horizon=100, random_seed=42)
        result = run_simulation(config)
        
        # Each booking event should correspond to exactly one arrival
        # (since each nurse books at most one shift)
        assert result.total_bookings <= result.total_arrivals
        
        # Verify that treated + control bookings = total bookings
        assert result.treated_bookings + result.control_bookings == result.total_bookings
        
        # All booking events should have valid timestamps within horizon
        for event in result.booking_events:
            assert 0 <= event.timestamp < config.horizon
    
    def test_tracking_version_consistency(self):
        """Test that run_simulation_with_tracking has same fix applied."""
        config = SimConfig(lambda_c=8.0, horizon=50, mu=0.2, random_seed=42)
        
        # Run both versions
        result1 = run_simulation(config)
        result2, states, shifts = run_simulation_with_tracking(config)
        
        # Both should have booking_rate <= 1.0
        assert result1.booking_rate <= 1.0
        assert result2.booking_rate <= 1.0
        
        # Results should be identical (same arrivals processed)
        assert result1.total_arrivals == result2.total_arrivals
        assert result1.total_bookings == result2.total_bookings
        assert abs(result1.booking_rate - result2.booking_rate) < 1e-10
        
        # Tracking version should have captured states
        assert len(states) == config.horizon
    
    def test_arrival_generation_determinism(self):
        """Test that arrival generation is deterministic with same seed."""
        config = SimConfig(lambda_c=2.0, horizon=50, random_seed=123)
        
        # Run simulation twice with same seed
        result1 = run_simulation(config)
        result2 = run_simulation(config)
        
        # Should get identical results
        assert result1.total_arrivals == result2.total_arrivals
        assert result1.total_bookings == result2.total_bookings
        assert result1.booking_rate == result2.booking_rate
        
        # Booking events should be identical
        assert len(result1.booking_events) == len(result2.booking_events)
        
        for e1, e2 in zip(result1.booking_events, result2.booking_events):
            assert e1.timestamp == e2.timestamp
            assert e1.nurse_id == e2.nurse_id
            assert e1.shift_id == e2.shift_id
    
    def test_generate_arrivals_function(self):
        """Test the generate_arrivals function directly."""
        config = SimConfig(lambda_c=1.5, random_seed=42)
        
        # Generate arrivals for multiple timesteps
        np.random.seed(42)  # Reset seed
        arrivals_t0 = generate_arrivals(config, 0.0)
        arrivals_t1 = generate_arrivals(config, 1.0)
        
        # Should generate reasonable number of arrivals
        total_arrivals = len(arrivals_t0) + len(arrivals_t1)
        
        # With lambda_c=1.5, expect around 3 arrivals over 2 timesteps
        # Allow for Poisson variation (very loose bounds)
        assert 0 <= total_arrivals <= 20  # Very conservative upper bound
        
        # All nurses should have correct timestamps
        for nurse in arrivals_t0:
            assert nurse.arrived_at == 0.0
        for nurse in arrivals_t1:
            assert nurse.arrived_at == 1.0
    
    def test_mathematical_impossibility_prevented(self):
        """Test that mathematically impossible scenarios are prevented."""
        # Previously, this scenario could produce booking_rate > 1.0
        config = SimConfig(
            lambda_c=15.0,  # Very high arrival rate
            horizon=20,     # Short simulation
            mu=0.05,        # Very slow reopening
            n_shifts=3,     # Few shifts
            random_seed=42
        )
        
        result = run_simulation(config)
        
        # The fundamental constraint: each nurse books at most one shift
        assert result.total_bookings <= result.total_arrivals
        
        # Therefore booking rate cannot exceed 1.0
        assert result.booking_rate <= 1.0
        
        # In this high-demand scenario, expect high booking rate but not > 1.0
        # Most arrivals should successfully book (but not more than arrived)
        assert 0.0 <= result.booking_rate <= 1.0


class TestBugFixRegressionTests:
    """Regression tests to ensure bugs don't reappear."""
    
    def test_no_double_arrival_counting(self):
        """Regression test: ensure arrivals aren't double-counted."""
        config = SimConfig(lambda_c=2.0, horizon=10, random_seed=42)
        
        # Run simulation and verify internal consistency
        result = run_simulation(config)
        
        # The key test: booking rate must be valid
        assert 0.0 <= result.booking_rate <= 1.0
        
        # Fundamental constraint: bookings <= arrivals
        assert result.total_bookings <= result.total_arrivals
        
        # Mathematical consistency
        if result.total_arrivals > 0:
            expected_rate = result.total_bookings / result.total_arrivals
            assert abs(result.booking_rate - expected_rate) < 1e-10
        
        # Run with different parameters to ensure consistency
        config2 = SimConfig(lambda_c=1.0, horizon=20, random_seed=42)
        result2 = run_simulation(config2)
        assert 0.0 <= result2.booking_rate <= 1.0
        assert result2.total_bookings <= result2.total_arrivals
    
    def test_extreme_parameter_robustness(self):
        """Test robustness with parameter values that previously caused issues."""
        problematic_configs = [
            # Cases that previously caused booking_rate > 1.0
            SimConfig(lambda_c=25.0, horizon=10, mu=0.01, random_seed=1),
            SimConfig(lambda_c=100.0, horizon=5, mu=0.001, random_seed=2),
            
            # Edge cases
            SimConfig(lambda_c=0.001, horizon=10000, mu=1000.0, random_seed=3),
            SimConfig(lambda_c=1000.0, horizon=1, mu=1.0, random_seed=4),
        ]
        
        for i, config in enumerate(problematic_configs):
            try:
                result = run_simulation(config)
                
                # Must satisfy fundamental constraints
                assert 0.0 <= result.booking_rate <= 1.0, f"Config {i}: Invalid booking rate"
                assert result.total_bookings <= result.total_arrivals, f"Config {i}: Too many bookings"
                
            except Exception as e:
                # If simulation fails, it should fail gracefully, not with mathematical impossibilities
                assert False, f"Config {i} failed: {e}"


def run_all_bugfix_tests():
    """Run all bug fix validation tests."""
    print("Running Bug Fix Validation Tests")
    print("=" * 50)
    
    test_classes = [
        TestBookingRateBugFix,
        TestBugFixRegressionTests
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
    
    print("\n" + "=" * 50)
    print(f"Bug Fix Test Results: {total_passed} passed, {total_failed} failed")
    
    if total_failed == 0:
        print("✓ ALL BUG FIX TESTS PASSED!")
        print("\nCritical Bug Fix Validated:")
        print("• Booking rate never exceeds 1.0")
        print("• Arrivals and bookings are consistently counted")
        print("• Double-counting bug eliminated")
        print("• Mathematical constraints enforced")
        return True
    else:
        print(f"⚠ {total_failed} bug fix tests failed")
        return False


if __name__ == "__main__":
    success = run_all_bugfix_tests()
    
    if success:
        print("\n🎉 Critical bug fix fully validated!")
        print("The booking rate > 1.0 bug has been eliminated.")
    else:
        print("\n⚠ Bug fix validation failed - check implementation")