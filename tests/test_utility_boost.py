"""
Comprehensive tests for utility-based treatment effects.
Tests that treatment_boost parameter works correctly in all aspects of the simulation.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
from market_sim.config import SimConfig
from market_sim.entities import Shift
from market_sim.mechanics import (
    select_consideration_set, 
    calculate_choice_probabilities,
    process_nurse_choice
)
from market_sim.discrete import run_simulation
from market_sim.entities import Nurse


class TestUtilityBoostConfig:
    """Test that treatment_boost parameter is properly configured."""
    
    def test_default_treatment_boost(self):
        """Test that default treatment_boost is 0.0."""
        config = SimConfig()
        assert config.treatment_boost == 0.0, f"Default treatment_boost should be 0.0, got {config.treatment_boost}"
    
    def test_custom_treatment_boost(self):
        """Test that custom treatment_boost values are accepted."""
        test_values = [0.0, 0.1, 0.5, 1.0, 2.5, -0.5]
        
        for boost in test_values:
            config = SimConfig(treatment_boost=boost)
            assert config.treatment_boost == boost, f"treatment_boost {boost} not set correctly"
    
    def test_treatment_boost_validation(self):
        """Test that treatment_boost validation works."""
        # Valid values should work
        valid_values = [0, 0.0, 1, 1.5, -1.0, 100.0]
        for value in valid_values:
            try:
                config = SimConfig(treatment_boost=value)
                assert config.treatment_boost == value
            except ValueError:
                assert False, f"Valid treatment_boost {value} was rejected"
        
        # Invalid values should fail
        invalid_values = ["0.5", None, [], {}]
        for value in invalid_values:
            try:
                config = SimConfig(treatment_boost=value)
                assert False, f"Invalid treatment_boost {value} was accepted"
            except ValueError:
                pass  # Expected


class TestUtilityBoostMechanics:
    """Test that utility boost is applied correctly in choice mechanics."""
    
    def test_consideration_set_ranking_with_boost(self):
        """Test that consideration set ranking uses effective utilities."""
        config = SimConfig(k=3, treatment_boost=1.0, random_seed=42)
        
        # Create shifts where treated shift has lower base utility but higher effective utility
        shifts = [
            Shift(id=0, base_utility=2.0, is_treated=True, status="open", filled_until=0.0),   # effective: 3.0
            Shift(id=1, base_utility=2.5, is_treated=False, status="open", filled_until=0.0),  # effective: 2.5
            Shift(id=2, base_utility=1.0, is_treated=True, status="open", filled_until=0.0),   # effective: 2.0
            Shift(id=3, base_utility=1.5, is_treated=False, status="open", filled_until=0.0),  # effective: 1.5
        ]
        
        consideration_set = select_consideration_set(shifts, config)
        
        # Should be ordered by effective utility: 3.0, 2.5, 2.0
        expected_ids = [0, 1, 2]  # IDs in effective utility order
        actual_ids = [shift.id for shift in consideration_set]
        
        assert actual_ids == expected_ids, f"Expected {expected_ids}, got {actual_ids}"
        
        # Verify the effective utilities are descending
        effective_utilities = [
            shift.base_utility + (config.treatment_boost if shift.is_treated else 0.0) 
            for shift in consideration_set
        ]
        assert effective_utilities == sorted(effective_utilities, reverse=True), \
            f"Effective utilities not descending: {effective_utilities}"
    
    def test_choice_probabilities_with_boost(self):
        """Test that choice probabilities use effective utilities."""
        config = SimConfig(treatment_boost=0.5, position_weights=[1.0, 0.8, 0.6], random_seed=42)
        
        # Create consideration set with known utilities
        shifts = [
            Shift(id=0, base_utility=1.0, is_treated=True, status="open", filled_until=0.0),   # effective: 1.5
            Shift(id=1, base_utility=1.0, is_treated=False, status="open", filled_until=0.0),  # effective: 1.0
            Shift(id=2, base_utility=0.5, is_treated=True, status="open", filled_until=0.0),   # effective: 1.0
        ]
        
        probabilities = calculate_choice_probabilities(shifts, config)
        
        # Check that probabilities sum to 1
        assert abs(np.sum(probabilities) - 1.0) < 1e-10, f"Probabilities don't sum to 1: {np.sum(probabilities)}"
        
        # First shift (treated, highest effective utility) should have highest probability
        assert probabilities[0] > probabilities[1], "Treated shift should have higher probability"
        assert probabilities[0] > probabilities[2], "Higher effective utility should win"
        
        # Manually verify calculation
        position_weights = np.array([1.0, 0.8, 0.6])
        effective_utilities = np.array([1.5, 1.0, 1.0])  # After boost
        expected_weighted = position_weights * np.exp(effective_utilities)
        expected_probs = expected_weighted / np.sum(expected_weighted)
        
        np.testing.assert_array_almost_equal(probabilities, expected_probs, decimal=10)
    
    def test_zero_boost_equivalent_to_no_treatment(self):
        """Test that treatment_boost=0.0 is equivalent to no treatment effect."""
        config_zero_boost = SimConfig(treatment_boost=0.0, treatment_prob=0.5, random_seed=42)
        config_no_treatment = SimConfig(treatment_boost=0.0, treatment_prob=0.0, random_seed=42)
        
        # Create identical shifts for both scenarios
        shifts_zero = [
            Shift(id=0, base_utility=2.0, is_treated=True, status="open", filled_until=0.0),
            Shift(id=1, base_utility=1.5, is_treated=False, status="open", filled_until=0.0),
            Shift(id=2, base_utility=1.0, is_treated=True, status="open", filled_until=0.0),
        ]
        
        shifts_none = [
            Shift(id=0, base_utility=2.0, is_treated=False, status="open", filled_until=0.0),  # Same utility, different treatment
            Shift(id=1, base_utility=1.5, is_treated=False, status="open", filled_until=0.0),
            Shift(id=2, base_utility=1.0, is_treated=False, status="open", filled_until=0.0),
        ]
        
        probs_zero = calculate_choice_probabilities(shifts_zero, config_zero_boost)
        probs_none = calculate_choice_probabilities(shifts_none, config_no_treatment)
        
        # Should get identical probabilities when boost is zero
        np.testing.assert_array_almost_equal(probs_zero, probs_none, decimal=10)
    
    def test_negative_boost_effects(self):
        """Test that negative treatment_boost works correctly."""
        config = SimConfig(k=2, treatment_boost=-0.5, random_seed=42)
        
        # Create shifts where treated has higher base utility but lower effective utility
        shifts = [
            Shift(id=0, base_utility=2.0, is_treated=True, status="open", filled_until=0.0),   # effective: 1.5
            Shift(id=1, base_utility=1.7, is_treated=False, status="open", filled_until=0.0),  # effective: 1.7
            Shift(id=2, base_utility=1.0, is_treated=False, status="open", filled_until=0.0),  # effective: 1.0
        ]
        
        consideration_set = select_consideration_set(shifts, config)
        
        # Should rank by effective utility: 1.7, 1.5
        expected_ids = [1, 0]  # Control shift should rank higher despite lower base utility
        actual_ids = [shift.id for shift in consideration_set]
        
        assert actual_ids == expected_ids, f"Negative boost ranking failed: expected {expected_ids}, got {actual_ids}"


class TestUtilityBoostSimulation:
    """Test utility boost effects in full simulations."""
    
    def test_no_boost_minimal_interference(self):
        """Test that treatment_boost=0.0 shows minimal interference effect."""
        config = SimConfig(
            horizon=500,
            lambda_c=0.8,
            mu=1.0,
            k=3,
            n_shifts=10,
            treatment_prob=0.5,
            treatment_boost=0.0,  # No boost
            random_seed=42
        )
        
        result = run_simulation(config)
        
        # With no boost, treatment rate may be slightly elevated due to tiebreaker
        # but should not show strong interference
        treatment_rate = result.treated_bookings / result.total_bookings if result.total_bookings > 0 else 0
        
        # Should be reasonably close to treatment_prob, allowing for tiebreaker effect
        assert 0.45 <= treatment_rate <= 0.65, \
            f"With zero boost, treatment rate should be ~0.5±0.15, got {treatment_rate}"
        
        # Should be much less biased than with positive boost
        assert treatment_rate < 0.75, f"Zero boost should not create strong bias: {treatment_rate}"
        
        print(f"  No boost: treatment_rate={treatment_rate:.3f} (minimal tiebreaker effect)")
    
    def test_positive_boost_creates_interference(self):
        """Test that positive treatment_boost creates visible interference effects."""
        config = SimConfig(
            horizon=500,
            lambda_c=0.8,
            mu=1.0,
            k=3,
            n_shifts=10,
            treatment_prob=0.5,
            treatment_boost=0.5,  # Positive boost
            random_seed=42
        )
        
        result = run_simulation(config)
        
        # With positive boost, treated shifts should get more bookings
        treatment_rate = result.treated_bookings / result.total_bookings if result.total_bookings > 0 else 0
        
        # Should be significantly higher than treatment_prob
        assert treatment_rate > 0.6, \
            f"With positive boost, treatment rate should be > 0.6, got {treatment_rate}"
        
        # Treated:Control ratio should be > 1.0
        if result.control_bookings > 0:
            ratio = result.treated_bookings / result.control_bookings
            assert ratio > 1.5, f"Treated:Control ratio should show interference, got {ratio}"
        
        print(f"  Positive boost: treatment_rate={treatment_rate:.3f}, ratio={ratio:.2f} (interference detected)")
    
    def test_boost_magnitude_effects(self):
        """Test that larger boosts create stronger interference effects."""
        base_config = {
            'horizon': 500,
            'lambda_c': 0.8,
            'mu': 1.0,
            'k': 3,
            'n_shifts': 10,
            'treatment_prob': 0.5,
            'random_seed': 42
        }
        
        boost_values = [0.0, 0.2, 0.5, 1.0]
        treatment_rates = []
        
        for boost in boost_values:
            config = SimConfig(treatment_boost=boost, **base_config)
            result = run_simulation(config)
            
            treatment_rate = result.treated_bookings / result.total_bookings if result.total_bookings > 0 else 0
            treatment_rates.append(treatment_rate)
            
            print(f"  Boost {boost:.1f}: treatment_rate={treatment_rate:.3f}")
        
        # Treatment rates should generally increase with boost size
        # (allowing for some randomness in small samples)
        assert treatment_rates[0] < treatment_rates[-1], \
            f"Treatment rate should increase with boost: {treatment_rates}"
        
        # Should see clear progression
        assert treatment_rates[1] >= treatment_rates[0], "Rate should increase with boost"
        assert treatment_rates[2] >= treatment_rates[1], "Rate should increase with boost"
    
    def test_extreme_boost_values(self):
        """Test simulation behavior with extreme treatment_boost values."""
        base_config = {
            'horizon': 200,
            'lambda_c': 0.5,
            'mu': 1.0,
            'k': 3,
            'n_shifts': 5,
            'treatment_prob': 0.5,
            'random_seed': 42
        }
        
        # Test very large positive boost
        config_large = SimConfig(treatment_boost=5.0, **base_config)
        result_large = run_simulation(config_large)
        
        # Should strongly favor treated shifts
        treatment_rate_large = result_large.treated_bookings / result_large.total_bookings if result_large.total_bookings > 0 else 0
        assert treatment_rate_large > 0.8, f"Large boost should create strong bias: {treatment_rate_large}"
        
        # Test large negative boost  
        config_negative = SimConfig(treatment_boost=-2.0, **base_config)
        result_negative = run_simulation(config_negative)
        
        # Should favor control shifts
        treatment_rate_negative = result_negative.treated_bookings / result_negative.total_bookings if result_negative.total_bookings > 0 else 0
        assert treatment_rate_negative < 0.3, f"Negative boost should hurt treated shifts: {treatment_rate_negative}"
        
        print(f"  Large positive boost: {treatment_rate_large:.3f}")
        print(f"  Large negative boost: {treatment_rate_negative:.3f}")


class TestUtilityBoostEdgeCases:
    """Test edge cases and corner scenarios for utility boost."""
    
    def test_all_shifts_treated_with_boost(self):
        """Test behavior when all shifts are treated."""
        config = SimConfig(
            k=3,
            treatment_prob=1.0,  # All treated
            treatment_boost=0.3,
            random_seed=42
        )
        
        shifts = [
            Shift(id=i, base_utility=float(i), is_treated=True, status="open", filled_until=0.0)
            for i in range(5)
        ]
        
        consideration_set = select_consideration_set(shifts, config)
        probabilities = calculate_choice_probabilities(consideration_set, config)
        
        # Should still work normally
        assert len(consideration_set) == 3
        assert len(probabilities) == 3
        assert abs(np.sum(probabilities) - 1.0) < 1e-10
        
        # All shifts have same boost, so ranking by base utility + boost
        expected_order = [4, 3, 2]  # Highest base utilities first
        actual_order = [shift.id for shift in consideration_set]
        assert actual_order == expected_order
    
    def test_no_shifts_treated_with_boost(self):
        """Test behavior when no shifts are treated."""
        config = SimConfig(
            k=3,
            treatment_prob=0.0,  # None treated
            treatment_boost=0.3,  # Should have no effect
            random_seed=42
        )
        
        shifts = [
            Shift(id=i, base_utility=float(i), is_treated=False, status="open", filled_until=0.0)
            for i in range(5)
        ]
        
        consideration_set = select_consideration_set(shifts, config)
        probabilities = calculate_choice_probabilities(consideration_set, config)
        
        # Should work normally, boost irrelevant
        assert len(consideration_set) == 3
        assert len(probabilities) == 3
        assert abs(np.sum(probabilities) - 1.0) < 1e-10
        
        # Ranking by base utility only
        expected_order = [4, 3, 2]
        actual_order = [shift.id for shift in consideration_set]
        assert actual_order == expected_order
    
    def test_boost_with_identical_base_utilities(self):
        """Test boost effects when base utilities are identical."""
        config = SimConfig(k=3, treatment_boost=0.5, random_seed=42)
        
        # All shifts have same base utility
        shifts = [
            Shift(id=0, base_utility=1.0, is_treated=True, status="open", filled_until=0.0),   # effective: 1.5
            Shift(id=1, base_utility=1.0, is_treated=False, status="open", filled_until=0.0),  # effective: 1.0
            Shift(id=2, base_utility=1.0, is_treated=True, status="open", filled_until=0.0),   # effective: 1.5
            Shift(id=3, base_utility=1.0, is_treated=False, status="open", filled_until=0.0),  # effective: 1.0
        ]
        
        consideration_set = select_consideration_set(shifts, config)
        
        # Treated shifts should come first due to higher effective utility
        treated_in_top_k = sum(1 for shift in consideration_set if shift.is_treated)
        assert treated_in_top_k == 2, f"Both treated shifts should be in top 3, got {treated_in_top_k}"
        
        # First two positions should be treated (tie-breaking)
        assert consideration_set[0].is_treated, "First position should be treated"
        assert consideration_set[1].is_treated, "Second position should be treated"


def run_utility_boost_tests():
    """Run all utility boost tests."""
    print("Running Utility Boost Tests")
    print("=" * 60)
    
    test_classes = [
        TestUtilityBoostConfig,
        TestUtilityBoostMechanics,
        TestUtilityBoostSimulation,
        TestUtilityBoostEdgeCases
    ]
    
    total_passed = 0
    total_failed = 0
    
    for test_class in test_classes:
        print(f"\n{test_class.__name__}:")
        class_instance = test_class()
        
        test_methods = [method for method in dir(class_instance) if method.startswith('test_')]
        
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
    print(f"Utility Boost Test Results: {total_passed} passed, {total_failed} failed")
    
    if total_failed == 0:
        print("✅ ALL UTILITY BOOST TESTS PASSED!")
        print("\nUtility-Based Treatment System Verified:")
        print("• treatment_boost parameter works correctly")
        print("• Effective utilities used in ranking and choice")
        print("• Interference effects visible with positive boost")
        print("• Clean separation between algorithm and treatment")
        return True
    else:
        print(f"❌ {total_failed} utility boost tests failed")
        return False


if __name__ == "__main__":
    success = run_utility_boost_tests()
    
    if success:
        print("\n🎉 UTILITY BOOST SYSTEM FULLY VALIDATED!")
        print("Ready for marketplace interference experiments.")
    else:
        print("\n⚠ Utility boost implementation needs fixes")