"""
Comprehensive unit tests for Stage 1 implementation.
"""

import pytest
import numpy as np
from market_sim.config import SimConfig
from market_sim.entities import Shift, Nurse, BookingEvent, SimulationResult
from market_sim.mechanics import (
    get_available_shifts,
    select_consideration_set,
    calculate_choice_probabilities,
    make_choice,
    process_nurse_choice,
    update_shift_statuses
)
from market_sim.discrete import (
    initialize_shifts,
    generate_arrivals,
    simulate_timestep,
    run_simulation
)


class TestSimConfig:
    """Test SimConfig dataclass and validation."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = SimConfig()
        assert config.horizon == 1000
        assert config.lambda_c == 0.5
        assert config.mu == 1.0
        assert config.k == 5
        assert config.n_shifts == 20
        assert config.treatment_prob == 0.5
        assert config.position_weights == [1.0, 0.8, 0.6, 0.4, 0.2]
        assert config.random_seed is None
    
    def test_config_validation(self):
        """Test configuration validation."""
        # Test invalid horizon
        with pytest.raises(ValueError, match="horizon must be positive"):
            SimConfig(horizon=0)
        
        # Test invalid lambda_c
        with pytest.raises(ValueError, match="lambda_c must be non-negative"):
            SimConfig(lambda_c=-1.0)
        
        # Test invalid mu
        with pytest.raises(ValueError, match="mu must be positive"):
            SimConfig(mu=0)
        
        # Test invalid k
        with pytest.raises(ValueError, match="k must be positive"):
            SimConfig(k=0)
        
        # Test invalid treatment_prob
        with pytest.raises(ValueError, match="treatment_prob must be between 0 and 1"):
            SimConfig(treatment_prob=1.5)
        
        # Test empty position_weights
        with pytest.raises(ValueError, match="position_weights cannot be empty"):
            SimConfig(position_weights=[])


class TestShift:
    """Test Shift entity class."""
    
    def test_shift_creation(self):
        """Test Shift class initialization."""
        shift = Shift(id=1, base_utility=2.5, is_treated=True)
        assert shift.id == 1
        assert shift.base_utility == 2.5
        assert shift.is_treated is True
        assert shift.status == "open"
        assert shift.filled_until == 0.0
    
    def test_shift_availability(self):
        """Test shift availability logic."""
        shift = Shift(id=1, base_utility=1.0, is_treated=False)
        
        # Initially available
        assert shift.is_available(0.0) is True
        
        # Book the shift
        shift.book_shift(0.0, mu=1.0)
        assert shift.status == "filled"
        assert shift.filled_until > 0.0
        
        # Not available immediately after booking
        assert shift.is_available(0.0) is False
        
        # Available after filled_until time
        assert shift.is_available(shift.filled_until + 1.0) is True
    
    def test_shift_reopening(self):
        """Test shift reopening logic."""
        shift = Shift(id=1, base_utility=1.0, is_treated=False)
        
        # Book the shift
        shift.book_shift(0.0, mu=1.0)
        assert shift.status == "filled"
        
        # Check reopening before time
        assert shift.check_reopening(0.0) is False
        assert shift.status == "filled"
        
        # Check reopening after time
        assert shift.check_reopening(shift.filled_until + 1.0) is True
        assert shift.status == "open"


class TestNurse:
    """Test Nurse entity class."""
    
    def test_nurse_creation(self):
        """Test Nurse class initialization."""
        nurse = Nurse(id=1, arrived_at=5.0, is_treated=False)
        assert nurse.id == 1
        assert nurse.arrived_at == 5.0
        assert nurse.is_treated is False
    
    def test_nurse_validation(self):
        """Test nurse parameter validation."""
        with pytest.raises(ValueError, match="arrived_at must be non-negative"):
            Nurse(id=1, arrived_at=-1.0, is_treated=False)


class TestMechanics:
    """Test choice mechanics functions."""
    
    def test_get_available_shifts(self):
        """Test filtering available shifts."""
        shifts = [
            Shift(id=1, base_utility=1.0, is_treated=False, status="open", filled_until=0.0),
            Shift(id=2, base_utility=2.0, is_treated=True, status="filled", filled_until=10.0),
            Shift(id=3, base_utility=3.0, is_treated=False, status="open", filled_until=0.0)
        ]
        
        available = get_available_shifts(shifts, 5.0)
        assert len(available) == 2
        assert available[0].id == 1
        assert available[1].id == 3
    
    def test_consideration_set(self):
        """Test consideration set selection."""
        config = SimConfig(k=2)
        shifts = [
            Shift(id=1, base_utility=1.0, is_treated=False),
            Shift(id=2, base_utility=2.0, is_treated=True),  # Should be first (treated)
            Shift(id=3, base_utility=3.0, is_treated=False), # Should be second (highest utility)
            Shift(id=4, base_utility=0.5, is_treated=False)
        ]
        
        consideration_set = select_consideration_set(shifts, config)
        assert len(consideration_set) == 2
        assert consideration_set[0].id == 2  # Treated shift first
        assert consideration_set[1].id == 3  # Highest utility control shift
    
    def test_choice_probabilities(self):
        """Test choice probability calculation."""
        config = SimConfig(position_weights=[1.0, 0.5])
        shifts = [
            Shift(id=1, base_utility=0.0, is_treated=True),
            Shift(id=2, base_utility=0.0, is_treated=False)
        ]
        
        probs = calculate_choice_probabilities(shifts, config)
        assert len(probs) == 2
        assert probs[0] > probs[1]  # First position should have higher probability
        assert abs(sum(probs) - 1.0) < 1e-10  # Should sum to 1
    
    def test_make_choice(self):
        """Test choice making."""
        np.random.seed(42)  # For reproducible test
        config = SimConfig(position_weights=[1.0, 0.0])  # Always choose first
        shifts = [
            Shift(id=1, base_utility=1.0, is_treated=True),
            Shift(id=2, base_utility=2.0, is_treated=False)
        ]
        
        choice = make_choice(shifts, config)
        assert choice == 0  # Should always choose first with these weights
    
    def test_update_shift_statuses(self):
        """Test shift status updates."""
        shifts = [
            Shift(id=1, base_utility=1.0, is_treated=False, status="filled", filled_until=5.0),
            Shift(id=2, base_utility=2.0, is_treated=True, status="filled", filled_until=15.0),
            Shift(id=3, base_utility=3.0, is_treated=False, status="open", filled_until=0.0)
        ]
        
        # At time 10.0, only first shift should reopen
        reopened = update_shift_statuses(shifts, 10.0)
        assert reopened == 1
        assert shifts[0].status == "open"
        assert shifts[1].status == "filled"
        assert shifts[2].status == "open"


class TestDiscrete:
    """Test discrete simulation functions."""
    
    def test_initialize_shifts(self):
        """Test shift initialization."""
        np.random.seed(42)
        config = SimConfig(n_shifts=5, treatment_prob=0.5)
        
        shifts = initialize_shifts(config)
        assert len(shifts) == 5
        
        # Check that all shifts are properly initialized
        for i, shift in enumerate(shifts):
            assert shift.id == i
            assert isinstance(shift.base_utility, float)
            assert isinstance(shift.is_treated, bool)
            assert shift.status == "open"
            assert shift.filled_until == 0.0
    
    def test_generate_arrivals(self):
        """Test nurse arrival generation."""
        np.random.seed(42)
        config = SimConfig(lambda_c=2.0)
        
        arrivals = generate_arrivals(config, 10.0)
        assert isinstance(arrivals, list)
        assert all(isinstance(nurse, Nurse) for nurse in arrivals)
        assert all(nurse.arrived_at == 10.0 for nurse in arrivals)
    
    def test_simulate_timestep(self):
        """Test single timestep simulation."""
        np.random.seed(42)
        config = SimConfig(n_shifts=5, lambda_c=1.0, random_seed=42)
        shifts = initialize_shifts(config)
        
        booking_events = simulate_timestep(shifts, config, 0.0)
        assert isinstance(booking_events, list)
        assert all(isinstance(event, BookingEvent) for event in booking_events)
    
    def test_run_simulation(self):
        """Test full simulation run."""
        config = SimConfig(horizon=10, random_seed=42)
        result = run_simulation(config)
        
        assert isinstance(result, SimulationResult)
        assert result.total_arrivals >= 0
        assert result.total_bookings >= 0
        assert result.total_bookings <= result.total_arrivals
        assert result.treated_bookings + result.control_bookings == result.total_bookings
        assert 0.0 <= result.booking_rate <= 1.0


class TestIntegration:
    """Integration tests for complete system."""
    
    def test_full_simulation_runs(self):
        """Test that full simulation runs without errors."""
        config = SimConfig(horizon=100, random_seed=42)
        result = run_simulation(config)
        
        # Should complete without errors
        assert result is not None
        assert result.total_arrivals > 0  # Should have some arrivals over 100 timesteps
    
    def test_booking_rate_reasonable(self):
        """Test that booking rate is reasonable."""
        config = SimConfig(horizon=1000, lambda_c=0.5, n_shifts=20, random_seed=42)
        result = run_simulation(config)
        
        # With plenty of shifts, booking rate should be reasonably high
        assert result.booking_rate > 0.1  # At least 10% booking rate
        assert result.booking_rate <= 1.0  # Cannot exceed 100%
    
    def test_empty_market_handling(self):
        """Test handling when no shifts are available."""
        config = SimConfig(horizon=10, n_shifts=1, lambda_c=5.0, mu=0.1, random_seed=42)
        result = run_simulation(config)
        
        # Should handle gracefully even with high demand and low supply
        assert result is not None
        assert result.total_bookings <= result.total_arrivals
    
    def test_deterministic_results(self):
        """Test that results are deterministic with same seed."""
        config1 = SimConfig(horizon=50, random_seed=123)
        config2 = SimConfig(horizon=50, random_seed=123)
        
        result1 = run_simulation(config1)
        result2 = run_simulation(config2)
        
        # Should get identical results with same seed
        assert result1.total_arrivals == result2.total_arrivals
        assert result1.total_bookings == result2.total_bookings
        assert result1.booking_rate == result2.booking_rate