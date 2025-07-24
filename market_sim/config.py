"""
Configuration system for marketplace simulation.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SimConfig:
    """Configuration for marketplace simulation parameters."""
    
    # Simulation parameters
    horizon: int = 1000                    # Simulation time steps
    lambda_c: float = 0.5                  # Customer arrival rate per time step
    mu: float = 1.0                        # Shift reopening rate
    
    # Market structure  
    k: int = 5                             # Consideration set size
    n_shifts: int = 20                     # Total number of shifts
    
    # Treatment parameters
    treatment_prob: float = 0.5            # Probability of treatment assignment
    treatment_boost: float = 0.0           # Utility boost for treated shifts
    
    # Choice model parameters
    position_weights: List[float] = field(
        default_factory=lambda: [1.0, 0.8, 0.6, 0.4, 0.2]
    )
    
    # Random seed for reproducibility
    random_seed: Optional[int] = None
    
    def __post_init__(self):
        """Validate configuration parameters."""
        if self.horizon <= 0:
            raise ValueError("horizon must be positive")
        if self.lambda_c < 0:
            raise ValueError("lambda_c must be non-negative")
        if self.mu <= 0:
            raise ValueError("mu must be positive")
        if self.k <= 0:
            raise ValueError("k must be positive")
        if self.n_shifts <= 0:
            raise ValueError("n_shifts must be positive")
        if not (0 <= self.treatment_prob <= 1):
            raise ValueError("treatment_prob must be between 0 and 1")
        if not isinstance(self.treatment_boost, (int, float)):
            raise ValueError("treatment_boost must be numeric")
        if len(self.position_weights) == 0:
            raise ValueError("position_weights cannot be empty")
        if any(w < 0 for w in self.position_weights):
            raise ValueError("position_weights must be non-negative")