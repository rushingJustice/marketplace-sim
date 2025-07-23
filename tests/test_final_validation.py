"""
Final validation tests to ensure booking rate > 1.0 bug is completely eliminated.
These tests are designed to be extremely thorough and catch any edge cases.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
from market_sim.config import SimConfig
from market_sim.discrete import run_simulation, run_simulation_with_tracking


def test_extreme_stress_scenarios():
    """Test extreme scenarios that would maximize chances of triggering the bug."""
    stress_configs = [
        # Very high demand scenarios
        SimConfig(lambda_c=20.0, horizon=100, mu=0.01, n_shifts=5, random_seed=42),
        SimConfig(lambda_c=50.0, horizon=50, mu=0.05, n_shifts=3, random_seed=123),
        SimConfig(lambda_c=100.0, horizon=20, mu=0.001, n_shifts=2, random_seed=456),
        
        # Edge case parameters
        SimConfig(lambda_c=10.0, horizon=1000, mu=0.1, k=1, n_shifts=10, random_seed=789),
        SimConfig(lambda_c=15.0, horizon=500, mu=2.0, k=20, n_shifts=5, random_seed=999),
        
        # Original notebook scenario variants
        SimConfig(horizon=500, lambda_c=0.6, mu=1.2, k=5, n_shifts=15, treatment_prob=0.1, random_seed=42),
        SimConfig(horizon=500, lambda_c=0.6, mu=1.2, k=5, n_shifts=15, treatment_prob=0.9, random_seed=42),
        SimConfig(horizon=1000, lambda_c=1.2, mu=0.6, k=10, n_shifts=30, treatment_prob=0.5, random_seed=42),
    ]
    
    print("Testing extreme stress scenarios:")
    max_rate_seen = 0.0
    
    for i, config in enumerate(stress_configs):
        # Test both simulation functions
        for func_name, func in [("run_simulation", run_simulation), ("run_simulation_with_tracking", run_simulation_with_tracking)]:
            if func_name == "run_simulation":
                result = func(config)
            else:
                result, _, _ = func(config)
            
            print(f"  Config {i} ({func_name}): arrivals={result.total_arrivals}, bookings={result.total_bookings}, rate={result.booking_rate:.6f}")
            
            # Critical assertions
            assert result.booking_rate <= 1.0, (
                f"CRITICAL BUG in {func_name} config {i}: booking_rate={result.booking_rate:.6f} > 1.0"
            )
            
            assert result.total_bookings <= result.total_arrivals, (
                f"CRITICAL BUG in {func_name} config {i}: bookings > arrivals"
            )
            
            # Track maximum rate seen
            max_rate_seen = max(max_rate_seen, result.booking_rate)
    
    print(f"Maximum booking rate observed: {max_rate_seen:.6f}")
    assert max_rate_seen <= 1.0, "Maximum rate exceeds theoretical limit"


def test_mathematical_consistency():
    """Test that mathematical relationships are always preserved."""
    config = SimConfig(lambda_c=5.0, horizon=200, mu=0.5, random_seed=42)
    
    # Test multiple times to check consistency
    for i in range(10):
        config.random_seed = 42 + i
        result = run_simulation(config)
        
        # Mathematical consistency checks
        assert result.total_bookings <= result.total_arrivals, (
            f"Run {i}: bookings ({result.total_bookings}) > arrivals ({result.total_arrivals})"
        )
        
        assert 0.0 <= result.booking_rate <= 1.0, (
            f"Run {i}: booking_rate ({result.booking_rate}) outside [0,1]"
        )
        
        # Booking rate calculation consistency
        expected_rate = result.total_bookings / result.total_arrivals if result.total_arrivals > 0 else 0.0
        assert abs(result.booking_rate - expected_rate) < 1e-10, (
            f"Run {i}: booking_rate calculation inconsistent"
        )
        
        # Treatment consistency
        assert result.treated_bookings + result.control_bookings == result.total_bookings, (
            f"Run {i}: treatment counts don't sum correctly"
        )
        
        print(f"  Run {i}: rate={result.booking_rate:.3f}, arrivals={result.total_arrivals}, bookings={result.total_bookings}")


def test_no_impossible_rates():
    """Test that we never see rates that were previously possible with the bug."""
    # The bug could produce rates like 1.054, so test we never see anything > 1.001
    config = SimConfig(lambda_c=3.0, horizon=500, mu=0.8, random_seed=42)
    
    suspicious_rates = []
    
    for seed in range(50):  # Test many random seeds
        config.random_seed = seed
        result = run_simulation(config)
        
        if result.booking_rate > 1.001:  # Any rate > 1.001 is suspicious
            suspicious_rates.append((seed, result.booking_rate, result.total_arrivals, result.total_bookings))
        
        # Still enforce the hard constraint
        assert result.booking_rate <= 1.0, (
            f"Seed {seed}: booking_rate={result.booking_rate:.6f} > 1.0"
        )
    
    if suspicious_rates:
        print("Suspicious rates found (this should never happen):")
        for seed, rate, arrivals, bookings in suspicious_rates:
            print(f"  Seed {seed}: rate={rate:.6f}, arrivals={arrivals}, bookings={bookings}")
        assert False, f"Found {len(suspicious_rates)} suspicious rates that shouldn't be possible"
    
    print("✓ No suspicious rates found across 50 random seeds")


def test_notebook_exact_reproduction():
    """Final attempt to reproduce the exact notebook bug."""
    # Multiple attempts with slight variations
    variations = [
        # Original
        SimConfig(horizon=500, lambda_c=0.6, mu=1.2, k=5, n_shifts=15, treatment_prob=0.1, random_seed=42),
        
        # Without random seed (maybe notebook didn't set it)
        SimConfig(horizon=500, lambda_c=0.6, mu=1.2, k=5, n_shifts=15, treatment_prob=0.1, random_seed=None),
        
        # Different seeds that might trigger it
        SimConfig(horizon=500, lambda_c=0.6, mu=1.2, k=5, n_shifts=15, treatment_prob=0.1, random_seed=1),
        SimConfig(horizon=500, lambda_c=0.6, mu=1.2, k=5, n_shifts=15, treatment_prob=0.1, random_seed=0),
        
        # Small parameter variations
        SimConfig(horizon=500, lambda_c=0.61, mu=1.2, k=5, n_shifts=15, treatment_prob=0.1, random_seed=42),
        SimConfig(horizon=500, lambda_c=0.6, mu=1.21, k=5, n_shifts=15, treatment_prob=0.1, random_seed=42),
    ]
    
    print("Final reproduction attempts:")
    
    for i, config in enumerate(variations):
        result, _, _ = run_simulation_with_tracking(config)
        
        print(f"  Variation {i}: arrivals={result.total_arrivals}, bookings={result.total_bookings}, rate={result.booking_rate:.6f}")
        
        # The reported bug showed rate=1.054, arrivals=296, bookings=312
        if abs(result.booking_rate - 1.054) < 0.001:
            print(f"    WARNING: Found rate very close to reported bug: {result.booking_rate:.6f}")
        
        if result.total_arrivals == 296 and result.total_bookings == 312:
            print(f"    WARNING: Found exact arrival/booking counts from bug report!")
        
        # But still enforce constraints
        assert result.booking_rate <= 1.0, f"Variation {i}: rate > 1.0"
        assert result.total_bookings <= result.total_arrivals, f"Variation {i}: bookings > arrivals"


def run_final_validation_tests():
    """Run all final validation tests."""
    print("Running Final Validation Tests")
    print("=" * 60)
    
    test_functions = [
        test_extreme_stress_scenarios,
        test_mathematical_consistency,
        test_no_impossible_rates,
        test_notebook_exact_reproduction
    ]
    
    passed = 0
    failed = 0
    
    for test_func in test_functions:
        print(f"\n{test_func.__name__}:")
        try:
            test_func()
            print(f"✓ {test_func.__name__} PASSED")
            passed += 1
        except AssertionError as e:
            print(f"✗ {test_func.__name__} FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test_func.__name__} ERROR: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Final Validation Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✅ ALL FINAL VALIDATION TESTS PASSED!")
        print("\nBooking rate > 1.0 bug has been completely eliminated:")
        print("• No rates > 1.0 found in any scenario")
        print("• Mathematical constraints enforced everywhere")
        print("• Extreme stress tests all pass")
        print("• Cannot reproduce original bug report")
        return True
    else:
        print(f"❌ {failed} validation tests failed")
        return False


if __name__ == "__main__":
    success = run_final_validation_tests()
    
    if success:
        print("\n🎉 BOOKING RATE BUG COMPLETELY ELIMINATED!")
        print("The simulation is now mathematically sound.")
    else:
        print("\n⚠ Validation failed - bug may still exist")