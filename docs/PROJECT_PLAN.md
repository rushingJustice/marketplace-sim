# Project Plan - Marketplace Interference Simulation

## Current Stage: Stage 1 - Basic Discrete-Time Model
**Status**: Planning Phase  
**Active Agent**: Planner  
**Last Updated**: 2025-01-23

## Project Overview
Build a marketplace interference simulation that demonstrates how A/B testing fails in two-sided markets. This follows the Li, Johari & Weintraub (2022) research paper.

## Stage 1 Specifications

### Goal
Get the basic mechanics working. Nurses arrive each second, pick shifts, done.

### Core Components to Implement

#### 1. Shift Class (`market_sim/entities.py`)
```python
class Shift:
    id: int
    base_utility: float
    is_treated: bool
    status: str  # "open" or "filled"
    filled_until: float  # when it reopens
```

#### 2. Nurse Class (`market_sim/entities.py`)
```python
class Nurse:
    id: int
    arrived_at: float
    is_treated: bool  # for nurse-side randomization
```

#### 3. Choice Model (`market_sim/mechanics.py`)
- Position-based choice with weights [1.0, 0.8, 0.6, 0.4, 0.2]
- Nurses see top k available shifts
- Probability ∝ position_weight × exp(utility)
- Multinomial selection from consideration set

#### 4. Main Simulation Loop (`market_sim/discrete.py`)
```python
for t in range(horizon):
    # Some nurses arrive (Bernoulli)
    # Each nurse:
    #   - Sees top k available shifts
    #   - Picks one (or none) based on utilities
    #   - That shift becomes unavailable
    # Some filled shifts reopen
```

### Success Criteria
1. **Booking Rate Check**: Count bookings should roughly match arrival_rate × match_probability
2. **Basic Functionality**: Nurses arrive, see shifts, make choices, shifts reopen
3. **No Crashes**: Simulation runs to completion without errors
4. **Reasonable Output**: Generated data looks realistic

### Implementation Requirements

#### File Structure for Stage 1
```
market_sim/
├── __init__.py
├── entities.py      # Shift and Nurse classes
├── mechanics.py     # Choice model logic
└── discrete.py      # Main simulation loop
```

#### Key Implementation Details
1. **Arrival Process**: Bernoulli arrivals (probability λ × dt per timestep)
2. **Choice Process**: Top-k selection, then position-weighted multinomial logit
3. **Supply Dynamics**: When booked, shift reopens after exponential(1/μ) time
4. **Treatment Assignment**: For now, random 50/50 split

#### Configuration Parameters
- `horizon`: Simulation time horizon (default: 1000)
- `lambda_c`: Customer arrival rate (default: 0.5)
- `mu`: Shift reopening rate (default: 1.0)
- `k`: Consideration set size (default: 5)
- `n_shifts`: Number of shifts (default: 20)

### Testing Requirements
1. **Unit Tests**: Test each class and function individually
2. **Integration Test**: Run full simulation and check output format
3. **Parameter Sweep**: Try different parameter values
4. **Edge Cases**: No available shifts, single shift, etc.

### Next Stages Preview
- Stage 2: Add visualizations (heatmaps, timelines)
- Stage 3: Add both randomization types (CR/LR) and metrics
- Stage 4: Implement block bootstrap for SE correction
- Stage 5: Convert to continuous time model
- Stage 6: Parameter sweeps and paper reproduction

## Implementation Notes
- Keep it simple for Stage 1
- Focus on getting mechanics right
- Don't optimize for speed yet
- Use clear, readable code
- Add docstrings for all functions

## Validation Checklist
- [ ] Shift class implemented with all required fields
- [ ] Nurse class implemented with all required fields  
- [ ] Choice model follows position-weighted multinomial logit
- [ ] Main simulation loop handles arrivals, choices, reopenings
- [ ] Basic configuration system works
- [ ] Unit tests pass
- [ ] Integration test produces reasonable output
- [ ] Code follows project style guidelines