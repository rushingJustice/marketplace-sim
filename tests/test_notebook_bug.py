"""
Test case to reproduce the booking rate 1.054 bug reported from notebook.
This should initially FAIL, then pass after the bug is fixed.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from market_sim.config import SimConfig
from market_sim.discrete import run_simulation_with_tracking


def test_notebook_booking_rate_bug():
    """
    Reproduce the exact scenario from notebook that shows booking_rate = 1.054.
    
    Reported bug:
    - treatment_prob = 0.1
    - Total arrivals: 296
    - Total bookings: 312
    - Booking rate: 1.054
    - Treated bookings: 159
    - Control bookings: 153
    
    This is mathematically impossible - bookings cannot exceed arrivals.
    """
    # Exact configuration from notebook
    config = SimConfig(
        horizon=500,
        lambda_c=0.6,
        mu=1.2,
        k=5,
        n_shifts=15,
        treatment_prob=0.1,
        random_seed=42
    )
    
    result, states, shifts = run_simulation_with_tracking(config)
    
    print(f"Test Results:")
    print(f"  Total arrivals: {result.total_arrivals}")
    print(f"  Total bookings: {result.total_bookings}")
    print(f"  Booking rate: {result.booking_rate:.6f}")
    print(f"  Treated bookings: {result.treated_bookings}")
    print(f"  Control bookings: {result.control_bookings}")
    
    # Critical tests that must NEVER fail
    assert result.booking_rate <= 1.0, (
        f"CRITICAL BUG: booking_rate={result.booking_rate:.6f} > 1.0 "
        f"(arrivals={result.total_arrivals}, bookings={result.total_bookings})"
    )
    
    assert result.total_bookings <= result.total_arrivals, (
        f"CRITICAL BUG: More bookings ({result.total_bookings}) than arrivals ({result.total_arrivals})"
    )
    
    # Mathematical consistency
    if result.total_arrivals > 0:
        expected_rate = result.total_bookings / result.total_arrivals
        assert abs(result.booking_rate - expected_rate) < 1e-10, (
            f"BUG: Booking rate calculation inconsistent"
        )
    
    # Treatment consistency
    assert result.treated_bookings + result.control_bookings == result.total_bookings, (
        f"BUG: Treatment booking counts don't sum to total"
    )
    
    print("✓ All critical constraints satisfied")


def test_multiple_random_seeds():
    """Test that the bug doesn't appear with different random seeds."""
    config_base = SimConfig(
        horizon=500,
        lambda_c=0.6,
        mu=1.2,
        k=5,
        n_shifts=15,
        treatment_prob=0.1
    )
    
    # Test multiple seeds
    for seed in [42, 123, 456, 789, 999]:
        config = SimConfig(
            horizon=config_base.horizon,
            lambda_c=config_base.lambda_c,
            mu=config_base.mu,
            k=config_base.k,
            n_shifts=config_base.n_shifts,
            treatment_prob=config_base.treatment_prob,
            random_seed=seed
        )
        
        result, _, _ = run_simulation_with_tracking(config)
        
        assert result.booking_rate <= 1.0, (
            f"CRITICAL BUG with seed {seed}: booking_rate={result.booking_rate:.6f} > 1.0"
        )
        
        assert result.total_bookings <= result.total_arrivals, (
            f"CRITICAL BUG with seed {seed}: bookings ({result.total_bookings}) > arrivals ({result.total_arrivals})"
        )
        
        print(f"  Seed {seed}: arrivals={result.total_arrivals}, bookings={result.total_bookings}, rate={result.booking_rate:.3f}")


def test_high_demand_scenarios():
    """Test scenarios that might trigger the bug."""
    problematic_configs = [
        # Original notebook config
        SimConfig(horizon=500, lambda_c=0.6, mu=1.2, k=5, n_shifts=15, treatment_prob=0.1, random_seed=42),
        
        # Variations that might trigger the bug
        SimConfig(horizon=500, lambda_c=0.6, mu=1.2, k=5, n_shifts=15, treatment_prob=0.1, random_seed=None),
        SimConfig(horizon=1000, lambda_c=0.6, mu=1.2, k=5, n_shifts=15, treatment_prob=0.1, random_seed=42),
        SimConfig(horizon=500, lambda_c=1.0, mu=1.2, k=5, n_shifts=15, treatment_prob=0.1, random_seed=42),
        SimConfig(horizon=500, lambda_c=0.6, mu=0.5, k=5, n_shifts=15, treatment_prob=0.1, random_seed=42),
    ]
    
    for i, config in enumerate(problematic_configs):
        try:
            result, _, _ = run_simulation_with_tracking(config)
            
            print(f"Config {i}: arrivals={result.total_arrivals}, bookings={result.total_bookings}, rate={result.booking_rate:.3f}")
            
            assert result.booking_rate <= 1.0, (
                f"Config {i}: booking_rate={result.booking_rate:.6f} > 1.0"
            )
            
            assert result.total_bookings <= result.total_arrivals, (
                f"Config {i}: bookings ({result.total_bookings}) > arrivals ({result.total_arrivals})"
            )
            
        except Exception as e:
            print(f"Config {i} failed with error: {e}")
            raise


def run_notebook_bug_tests():
    """Run all notebook bug reproduction tests."""
    print("Running Notebook Bug Reproduction Tests")
    print("=" * 50)
    
    test_functions = [
        test_notebook_booking_rate_bug,
        test_multiple_random_seeds,
        test_high_demand_scenarios
    ]
    
    passed = 0
    failed = 0
    
    for test_func in test_functions:
        print(f"\n{test_func.__name__}:")
        try:
            test_func()
            print(f"✓ {test_func.__name__} PASSED")
            passed += 1
        except Exception as e:
            print(f"✗ {test_func.__name__} FAILED: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"Notebook Bug Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✓ ALL NOTEBOOK BUG TESTS PASSED!")
        print("The booking rate > 1.0 bug is not reproducible.")
        return True
    else:
        print(f"⚠ {failed} tests failed - bug still exists")
        return False


if __name__ == "__main__":
    success = run_notebook_bug_tests()
    
    if success:
        print("\n🎉 Notebook bug tests pass - no reproducible bug found!")
    else:
        print("\n⚠ Notebook bug reproduced - needs immediate fix")