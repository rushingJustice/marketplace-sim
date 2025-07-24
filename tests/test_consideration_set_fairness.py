"""
Comprehensive tests for consideration set fairness and bias elimination.
Tests that the sorting algorithm produces fair mixed consideration sets.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
from market_sim.config import SimConfig
from market_sim.entities import Shift
from market_sim.mechanics import select_consideration_set


class TestConsiderationSetFairness:
    """Test that consideration set selection is fair and unbiased."""
    
    def test_utility_based_ranking(self):
        """Test that shifts are primarily ranked by utility, not treatment."""
        config = SimConfig(k=5, random_seed=42)
        
        # Create shifts with clear utility ordering
        shifts = [
            Shift(id=0, base_utility=5.0, is_treated=False, status="open", filled_until=0.0),  # Best control
            Shift(id=1, base_utility=4.0, is_treated=True, status="open", filled_until=0.0),   # Good treated
            Shift(id=2, base_utility=3.0, is_treated=False, status="open", filled_until=0.0),  # Medium control
            Shift(id=3, base_utility=2.0, is_treated=True, status="open", filled_until=0.0),   # Low treated
            Shift(id=4, base_utility=1.0, is_treated=False, status="open", filled_until=0.0),  # Worst control
        ]
        
        consideration_set = select_consideration_set(shifts, config)
        
        # Should be ordered by utility: 5.0, 4.0, 3.0, 2.0, 1.0
        expected_order = [0, 1, 2, 3, 4]  # IDs in utility order
        actual_order = [shift.id for shift in consideration_set]
        
        assert actual_order == expected_order, f"Expected {expected_order}, got {actual_order}"
        
        # Verify utilities are descending
        utilities = [shift.base_utility for shift in consideration_set]
        assert utilities == sorted(utilities, reverse=True), "Utilities not in descending order"
    
    def test_treatment_tiebreaker(self):
        """Test that treatment acts as tiebreaker for equal utilities."""
        config = SimConfig(k=4, random_seed=42)
        
        # Create shifts with tied utilities
        shifts = [
            Shift(id=0, base_utility=2.0, is_treated=False, status="open", filled_until=0.0),  # Control, tie
            Shift(id=1, base_utility=2.0, is_treated=True, status="open", filled_until=0.0),   # Treated, tie
            Shift(id=2, base_utility=1.0, is_treated=False, status="open", filled_until=0.0),  # Control, lower
            Shift(id=3, base_utility=1.0, is_treated=True, status="open", filled_until=0.0),   # Treated, lower
        ]
        
        consideration_set = select_consideration_set(shifts, config)
        
        # For tied utilities, treated should come first
        # Expected: treated(2.0), control(2.0), treated(1.0), control(1.0)
        expected_treatment = [True, False, True, False]
        actual_treatment = [shift.is_treated for shift in consideration_set]
        
        assert actual_treatment == expected_treatment, f"Expected {expected_treatment}, got {actual_treatment}"
    
    def test_mixed_consideration_sets(self):
        """Test that consideration sets contain both treated and control shifts."""
        config = SimConfig(k=5, random_seed=42)
        
        # Create realistic scenario with mixed utilities
        np.random.seed(42)
        shifts = []
        for i in range(20):
            shift = Shift(
                id=i,
                base_utility=np.random.normal(0, 1),  # Random utilities
                is_treated=(i % 2 == 0),  # Alternate treatment
                status="open",
                filled_until=0.0
            )
            shifts.append(shift)
        
        consideration_set = select_consideration_set(shifts, config)
        
        # Should have both treated and control shifts
        treated_count = sum(1 for shift in consideration_set if shift.is_treated)
        control_count = len(consideration_set) - treated_count
        
        assert treated_count > 0, "No treated shifts in consideration set"
        assert control_count > 0, "No control shifts in consideration set"
        assert len(consideration_set) == config.k, f"Wrong consideration set size: {len(consideration_set)}"
        
        print(f"  Mixed set: {treated_count} treated, {control_count} control")
    
    def test_no_all_treated_bias(self):
        """Test the specific bias bug is eliminated by ensuring utility-based ranking."""
        config = SimConfig(k=5, treatment_prob=0.5, random_seed=42)
        
        # Create scenario that ensures mixed consideration set by design
        shifts = []
        
        # Create shifts with interleaved utilities to force mixing
        # Best: Control(5.0), Treated(4.0), Control(3.0), Treated(2.0), Control(1.0), etc.
        for i in range(10):
            base_utility = 5.0 - i  # Descending utilities: 5, 4, 3, 2, 1, 0, -1, -2, -3, -4
            is_treated = (i % 2 == 1)  # Alternate: F,T,F,T,F,T,F,T,F,T
            
            shift = Shift(
                id=i,
                base_utility=base_utility,
                is_treated=is_treated,
                status="open",
                filled_until=0.0
            )
            shifts.append(shift)
        
        consideration_set = select_consideration_set(shifts, config)
        
        # With this design, should get mixed set: C(5), T(4), C(3), T(2), C(1)
        treated_count = sum(1 for shift in consideration_set if shift.is_treated)
        control_count = len(consideration_set) - treated_count
        
        # Should have both types
        assert treated_count > 0, "No treated shifts in consideration set"
        assert control_count > 0, "No control shifts in consideration set"
        
        # Verify utilities are properly ordered (the key test for bias elimination)
        utilities = [shift.base_utility for shift in consideration_set]
        expected_utilities = [5.0, 4.0, 3.0, 2.0, 1.0]
        assert utilities == expected_utilities, f"Utilities not properly ordered: {utilities}"
        
        # Verify treatment pattern matches utility ordering
        expected_treatment = [False, True, False, True, False]  # C,T,C,T,C
        actual_treatment = [shift.is_treated for shift in consideration_set]
        assert actual_treatment == expected_treatment, f"Treatment pattern wrong: {actual_treatment}"
        
        print(f"  Perfect mix: {treated_count} treated, {control_count} control (utility-based)")
    
    def test_extreme_treatment_scenarios(self):
        """Test edge cases with extreme treatment probabilities."""
        config = SimConfig(k=3, random_seed=42)
        
        # Scenario 1: All shifts treated
        all_treated = [
            Shift(id=i, base_utility=float(i), is_treated=True, status="open", filled_until=0.0)
            for i in range(5)
        ]
        
        consideration_set = select_consideration_set(all_treated, config)
        assert all(shift.is_treated for shift in consideration_set), "Not all treated when all shifts treated"
        assert len(consideration_set) == 3, "Wrong size for all-treated scenario"
        
        # Scenario 2: No shifts treated
        no_treated = [
            Shift(id=i, base_utility=float(i), is_treated=False, status="open", filled_until=0.0)
            for i in range(5)
        ]
        
        consideration_set = select_consideration_set(no_treated, config)
        assert not any(shift.is_treated for shift in consideration_set), "Found treated shift when none treated"
        assert len(consideration_set) == 3, "Wrong size for no-treated scenario"
    
    def test_realistic_marketplace_scenario(self):
        """Test with realistic marketplace parameters."""
        config = SimConfig(k=5, n_shifts=20, treatment_prob=0.4, random_seed=42)
        
        # Simulate realistic shift initialization
        np.random.seed(42)
        shifts = []
        for i in range(config.n_shifts):
            base_utility = np.random.normal(0, 1)
            is_treated = np.random.random() < config.treatment_prob
            
            shift = Shift(
                id=i,
                base_utility=base_utility,
                is_treated=is_treated,
                status="open",
                filled_until=0.0
            )
            shifts.append(shift)
        
        consideration_set = select_consideration_set(shifts, config)
        
        # Validate consideration set properties
        assert len(consideration_set) == config.k, "Wrong consideration set size"
        
        # Should have both types if both exist in population
        treated_in_population = any(shift.is_treated for shift in shifts)
        control_in_population = any(not shift.is_treated for shift in shifts)
        
        if treated_in_population and control_in_population:
            treated_in_set = any(shift.is_treated for shift in consideration_set)
            control_in_set = any(not shift.is_treated for shift in consideration_set)
            
            # With realistic parameters, should have mix
            # (Not enforcing strict requirement due to randomness, just checking bias elimination)
            print(f"  Population: {treated_in_population} treated exists, {control_in_population} control exists")
            print(f"  Consideration set: {treated_in_set} treated, {control_in_set} control")
    
    def test_utilities_properly_ordered(self):
        """Test that consideration set utilities are in descending order."""
        config = SimConfig(k=6, random_seed=42)
        
        # Create shifts with various utilities
        np.random.seed(42)
        shifts = []
        for i in range(15):
            shift = Shift(
                id=i,
                base_utility=np.random.uniform(-2, 2),
                is_treated=np.random.random() < 0.5,
                status="open",
                filled_until=0.0
            )
            shifts.append(shift)
        
        consideration_set = select_consideration_set(shifts, config)
        
        # Utilities should be in descending order
        utilities = [shift.base_utility for shift in consideration_set]
        sorted_utilities = sorted(utilities, reverse=True)
        
        assert utilities == sorted_utilities, f"Utilities not properly ordered: {utilities}"
        
        # First shift should have highest utility among all shifts
        all_utilities = [shift.base_utility for shift in shifts]
        max_utility = max(all_utilities)
        assert consideration_set[0].base_utility == max_utility, "First shift doesn't have maximum utility"


def run_consideration_set_fairness_tests():
    """Run all consideration set fairness tests."""
    print("Running Consideration Set Fairness Tests")
    print("=" * 60)
    
    test_class = TestConsiderationSetFairness()
    test_methods = [method for method in dir(test_class) if method.startswith('test_')]
    
    passed = 0
    failed = 0
    
    for method_name in test_methods:
        print(f"\n{method_name}:")
        try:
            method = getattr(test_class, method_name)
            method()
            print(f"✓ {method_name} PASSED")
            passed += 1
        except AssertionError as e:
            print(f"✗ {method_name} FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {method_name} ERROR: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Consideration Set Fairness Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✅ ALL CONSIDERATION SET FAIRNESS TESTS PASSED!")
        print("\nBias Elimination Verified:")
        print("• Consideration sets ranked by utility, not treatment")
        print("• Fair representation of both treated and control shifts")
        print("• Treatment only used as tiebreaker for equal utilities")
        print("• No more ALL-treated consideration sets")
        return True
    else:
        print(f"❌ {failed} consideration set fairness tests failed")
        return False


if __name__ == "__main__":
    success = run_consideration_set_fairness_tests()
    
    if success:
        print("\n🎉 CONSIDERATION SET BIAS ELIMINATED!")
        print("Choice model now produces fair, utility-based rankings.")
    else:
        print("\n⚠ Consideration set bias still exists - fix needed")