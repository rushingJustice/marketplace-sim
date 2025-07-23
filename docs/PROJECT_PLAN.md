# Project Plan - Marketplace Interference Simulation

## Current Stage: Stage 2 - Visualization System
**Status**: Planning Phase  
**Active Agent**: Planner  
**Last Updated**: 2025-01-23

## Stage 1 Status: COMPLETED ✅
**Approval**: REVIEWER approved with excellent rating  
**Implementation**: All core functionality working correctly

## Stage 2 Specifications

### Goal
See what's happening before you measure it. Create visual tools to understand marketplace dynamics and validate that interference is occurring as expected.

### Core Visualizations to Implement

#### 1. Shift Availability Heatmap
**Purpose**: Show shift availability patterns over time  
**Design**: 
- X-axis: Time (simulation timesteps)
- Y-axis: Shift ID 
- Color: Availability status (open=light, filled=dark)
- **Expected pattern**: Treated shifts should show darker bands (filled more often)

**Technical specs**:
```python
def plot_availability_heatmap(
    result: SimulationResult, 
    shifts: List[Shift],
    config: SimConfig
) -> plt.Figure
```

#### 2. Booking Timeline Scatter Plot  
**Purpose**: Show when and which shifts get booked  
**Design**:
- X-axis: Time (when booking occurred)
- Y-axis: Shift ID
- Color: Treatment status (treated=red, control=blue)
- Point size: Could indicate utility or consideration set position

**Technical specs**:
```python
def plot_booking_timeline(
    result: SimulationResult
) -> plt.Figure
```

#### 3. Running Booking Rate Line Chart
**Purpose**: Track booking success over time for treated vs control  
**Design**:
- X-axis: Time (rolling window)
- Y-axis: Booking rate (bookings/arrivals)
- Two lines: Treated shifts vs Control shifts
- Rolling window approach for smooth visualization

**Technical specs**:
```python
def plot_running_booking_rates(
    result: SimulationResult,
    window_size: int = 50
) -> plt.Figure
```

### Implementation Requirements

#### File Structure for Stage 2
```
market_sim/
├── __init__.py          # Existing
├── config.py            # Existing  
├── entities.py          # Existing
├── mechanics.py         # Existing
├── discrete.py          # Existing
└── plots.py             # NEW - All visualization functions

notebooks/
├── 01_basic_sim.ipynb   # NEW - Interactive Stage 1 demo
└── 02_visualize.ipynb   # NEW - Stage 2 visualization demo
```

#### Enhanced Data Collection
Modify existing simulation to track additional data needed for visualizations:

**SimulationState class** (new):
```python
@dataclass
class SimulationState:
    timestep: int
    shift_statuses: List[str]  # Track all shift statuses at each timestep
    available_count: int
    filled_count: int
```

**Enhanced SimulationResult**:
- Add `simulation_states: List[SimulationState]` 
- Add `shift_history: List[List[Shift]]` (snapshots over time)

#### Visualization Functions

##### 1. Core Plotting Functions (`plots.py`)
```python
def setup_plot_style() -> None:
    """Set consistent matplotlib style for all plots."""

def plot_availability_heatmap(
    simulation_states: List[SimulationState],
    shifts: List[Shift],
    config: SimConfig,
    figsize: tuple = (12, 8)
) -> plt.Figure:
    """Create shift availability heatmap."""

def plot_booking_timeline(
    booking_events: List[BookingEvent],
    shifts: List[Shift], 
    figsize: tuple = (12, 6)
) -> plt.Figure:
    """Create booking timeline scatter plot."""

def plot_running_booking_rates(
    booking_events: List[BookingEvent],
    total_arrivals_over_time: List[int],
    window_size: int = 50,
    figsize: tuple = (10, 6)
) -> plt.Figure:
    """Plot running booking rates for treated vs control."""

def create_summary_dashboard(
    result: SimulationResult,
    shifts: List[Shift],
    config: SimConfig
) -> plt.Figure:
    """Create 2x2 dashboard with all key visualizations."""
```

##### 2. Analysis Helper Functions
```python
def calculate_shift_utilization(
    booking_events: List[BookingEvent],
    shifts: List[Shift],
    horizon: int
) -> Dict[int, float]:
    """Calculate utilization rate for each shift."""

def identify_interference_patterns(
    booking_events: List[BookingEvent],
    shifts: List[Shift]
) -> Dict[str, Any]:
    """Analyze patterns that indicate interference."""
```

### Enhanced Simulation Loop

Modify `discrete.py` to collect visualization data:

```python
def run_simulation_with_tracking(
    config: Optional[SimConfig] = None
) -> Tuple[SimulationResult, List[SimulationState], List[Shift]]:
    """
    Enhanced simulation that tracks states for visualization.
    
    Returns:
        - SimulationResult: Standard results
        - List[SimulationState]: State at each timestep  
        - List[Shift]: Final shift states
    """
```

### Jupyter Notebooks

#### `notebooks/01_basic_sim.ipynb`
- Interactive demo of Stage 1 functionality
- Parameter exploration with widgets
- Basic result interpretation

#### `notebooks/02_visualize.ipynb`  
- Demo all Stage 2 visualizations
- Interactive parameter adjustment
- Visual validation of interference patterns

### Success Criteria

1. **Availability Heatmap**: Treated shifts show darker bands (more filled time)
2. **Timeline Scatter**: Clear clustering patterns visible 
3. **Running Rates**: Treated vs control rates show divergence over time
4. **Dashboard**: All plots render correctly and are informative
5. **Notebooks**: Interactive demos work smoothly

### Validation Requirements

#### Visual Validation Tests
1. **Pattern Recognition**: Treated shifts should be filled more frequently
2. **Color Coding**: Treatment status clearly distinguishable  
3. **Timeline Accuracy**: Booking events plotted at correct times
4. **Rate Calculations**: Running rates calculated correctly

#### Technical Tests
1. **Plot Generation**: All plotting functions execute without errors
2. **Data Consistency**: Visualization data matches simulation results
3. **Performance**: Plots render in reasonable time (<5 seconds)
4. **Styling**: Consistent appearance across all visualizations

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
├── __init__.py      # Package init (already created)
├── entities.py      # Shift and Nurse classes
├── mechanics.py     # Choice model logic
├── discrete.py      # Main simulation loop
└── config.py        # Configuration parameters
```

#### Detailed Implementation Specs

##### 1. Configuration System (`config.py`)
```python
@dataclass
class SimConfig:
    horizon: int = 1000          # Simulation time steps
    lambda_c: float = 0.5        # Customer arrival rate per time step  
    mu: float = 1.0              # Shift reopening rate
    k: int = 5                   # Consideration set size
    n_shifts: int = 20           # Total number of shifts
    treatment_prob: float = 0.5  # Probability of treatment assignment
    position_weights: List[float] = field(default_factory=lambda: [1.0, 0.8, 0.6, 0.4, 0.2])
    random_seed: Optional[int] = None
```

##### 2. Entity Classes (`entities.py`)
- Use dataclasses for clean structure
- Shift tracks current availability and treatment status
- Nurse tracks arrival time and treatment assignment
- Add utility calculation methods

##### 3. Choice Mechanics (`mechanics.py`) 
- `get_available_shifts()`: Filter shifts by availability status
- `select_consideration_set()`: Top-k selection with treatment ranking
- `make_choice()`: Position-weighted multinomial logit
- `update_shift_status()`: Handle booking and reopening

##### 4. Main Loop (`discrete.py`)
- `run_simulation()`: Main entry point with configuration
- `simulate_timestep()`: Process one time step 
- `generate_arrivals()`: Bernoulli arrival process
- `process_nurse()`: Handle single nurse choice process
- `update_shifts()`: Check for shifts that should reopen

#### Configuration Parameters
- `horizon`: Simulation time horizon (default: 1000)
- `lambda_c`: Customer arrival rate (default: 0.5)
- `mu`: Shift reopening rate (default: 1.0)
- `k`: Consideration set size (default: 5)
- `n_shifts`: Number of shifts (default: 20)

### Algorithmic Details

#### Choice Model Implementation
1. **Available Shifts**: Filter where `status == "open"` and `current_time >= filled_until`
2. **Treatment Ranking**: Sort treated shifts first, then by `base_utility` (descending)
3. **Consideration Set**: Take first `k` shifts from sorted list
4. **Choice Probabilities**: `prob[i] = position_weights[i] * exp(utility[i]) / sum_all`
5. **Selection**: Use `np.random.multinomial` with calculated probabilities

#### Supply Dynamics
1. **Booking**: Set `status = "filled"`, `filled_until = current_time + exponential(1/mu)`
2. **Reopening**: Check all shifts where `current_time >= filled_until`, set `status = "open"`
3. **Treatment Assignment**: Assign randomly at shift creation, never changes

### Testing Requirements

#### Unit Tests (`tests/test_stage1.py`)
```python
def test_shift_creation()           # Test Shift class initialization
def test_nurse_creation()           # Test Nurse class initialization  
def test_available_shifts()         # Test filtering logic
def test_consideration_set()        # Test top-k selection
def test_choice_probabilities()     # Test logit calculation
def test_shift_booking()            # Test status updates
def test_shift_reopening()          # Test timing logic
```

#### Integration Tests
1. **Full Simulation**: Run with default config, verify completion
2. **Booking Rate**: Compare to theoretical λ * P(match)  
3. **Empty Market**: All shifts booked - should handle gracefully
4. **Single Shift**: k=1, n_shifts=1 - basic edge case

#### Output Validation
- Return structured data with timestamps, nurse_ids, shift_ids, treatment_status
- Track booking events and reopening events
- Verify treatment assignment stays consistent

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