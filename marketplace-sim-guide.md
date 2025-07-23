# Marketplace Interference Simulation - Implementation Guide

## Why Build This

A/B tests in marketplaces are broken. When you boost some listings, they steal demand from others. Standard stats miss this. You think you've got a winner, but it fails in production.

This simulation shows you exactly how bad it gets. And how to fix it.

## How Interference Works

Picture a nurse job board:
1. You boost some shifts to the top
2. Nurses book those shifts more
3. Those shifts disappear (they're filled)
4. Control nurses now see different options
5. Everyone's outcomes are connected

Result: Your test says +20% bookings. Reality: +5%. You waste money on a bad feature.

## What We're Building

A fake marketplace that acts like the real one. Run experiments, measure bias, test fixes.

Based on: Li, Johari & Weintraub (2022) paper from Berkeley.

## Build Plan - Don't Skip Steps

### Stage 1: Basic Discrete-Time Model
**Goal**: Get the mechanics working. Nurses arrive each second, pick shifts, done.

**What to build**:
```python
class Shift:
    id: int
    base_utility: float
    is_treated: bool
    status: str  # "open" or "filled"
    filled_until: float  # when it reopens

class Nurse:
    id: int
    arrived_at: float
    is_treated: bool  # for nurse-side randomization
```

**Core loop**:
```python
for t in range(horizon):
    # Some nurses arrive (Bernoulli)
    # Each nurse:
    #   - Sees top k available shifts
    #   - Picks one (or none) based on utilities
    #   - That shift becomes unavailable
    # Some filled shifts reopen
```

**Check**: Count bookings. Should roughly match arrival_rate × match_probability.

### Stage 2: Add Visuals
**Goal**: See what's happening before you measure it.

**Build these plots**:
- Shift availability over time (heatmap: shift ID vs time, colored by open/filled)
- Booking timeline (scatter: x=time, y=shift ID, color=treated/control)
- Running booking rate (line chart with treated vs control)

**Check**: Treated shifts should have darker bands in the heatmap (filled more often).

### Stage 3: Add Metrics & Both Randomizations
**Goal**: Measure the actual bias.

**Randomization types**:
- **CR (Customer Randomization)**: Flip a coin for each nurse
- **LR (Listing Randomization)**: Flip a coin for each shift at start

**Key metrics**:
```python
# For shifts (LR analysis)
fill_rate = bookings / time_available

# For nurses (CR analysis)  
match_rate = 1 if booked else 0

# Overall
lift = mean(treated) - mean(control)
se_naive = std(outcomes) / sqrt(n)
```

**Check**: LR should have less bias than CR (but not zero).

### Stage 4: Fix the Standard Errors
**Goal**: Get confidence intervals that actually work.

**Block Bootstrap**:
1. Cut your timeline into chunks (say, 100 seconds each)
2. Resample chunks with replacement
3. Compute lift on each resample
4. Use the spread as your standard error

```python
def block_bootstrap(bookings, block_size=100):
    # Group bookings by time block
    # Resample blocks
    # Compute lift for this resample
    # Repeat 1000 times
    # Return std dev of lifts
```

**Check**: Run 100 experiments. Your 95% CI should contain truth 95% of the time.

### Stage 4.5: Baby Steps to Continuous Time
**Goal**: Bridge to full continuous model.

Change the loop to smaller timesteps:
```python
dt = 0.1  # seconds
for t in np.arange(0, horizon, dt):
    # Arrivals now Poisson-ish
    # Everything else same
```

**Check**: Results should converge to Stage 4 as dt → 0.

### Stage 5: Full Continuous Time
**Goal**: Match the paper exactly.

Event queue approach:
```python
events = []  # (time, type, data)
heapq.heappush(events, (0.5, 'arrival', nurse_id))

while events and time < horizon:
    time, event_type, data = heapq.heappop(events)
    if event_type == 'arrival':
        # Handle booking
        # Schedule next arrival
    elif event_type == 'release':
        # Shift becomes available again
```

**Check**: Reproduce paper's Figures 7-8.

### Stage 6: Parameter Sweeps
**Goal**: Understand when interference is worst.

Vary:
- **ρ = demand/supply ratio**: 0.25 to 2.0
- **k**: consideration set size (3, 5, 10)
- **Treatment strength**: how much to boost treated shifts
- **Market concentration**: variance in base utilities

Plot bias curves for each.

## Implementation Details

### Position-Based Choice Model

Nurses see top k shifts. Position matters:
```python
position_weights = [1.0, 0.8, 0.6, 0.4, 0.2]  # first slot best

# Probability of choosing shift at position i:
p[i] = position_weights[i] * exp(utility[i]) / sum(...)
```

Treatment works by forcing treated shifts higher in the ranking.

### How Treatment Changes Rankings

Two approaches:
1. **Fixed boost**: Treated shifts get +0.5 utility
2. **Rank manipulation**: Treated shifts sort first, then by utility

The paper uses approach 2. A treated shift with utility 3.0 ranks above a control shift with utility 4.0.

### Consideration Set Selection

For each nurse:
1. Get all open shifts
2. Compute effective utility for each:
   - If nurse treated (CR): treated shifts get bonus
   - If shift treated (LR): it gets bonus
3. Take top k by effective utility
4. These k shifts form the consideration set

### Supply Dynamics

When a shift is booked:
```python
reopen_time = current_time + random.exponential(1/mu)
heapq.heappush(events, (reopen_time, 'release', shift_id))
```

This models "nurses work the shift then it reopens."

### Edge Cases

- **No available shifts**: Nurse leaves without booking
- **Ties in utility**: Break randomly
- **Partial blocks in bootstrap**: Drop them or wrap around

## Validation Milestones

1. **Sanity check**: Set mu=1000 (instant reopen) → no interference → no bias
2. **Booking rate**: Should ≈ λ_c × P(match|arrival)
3. **Availability fraction**: In equilibrium, fraction open = μ/(μ + λ×P(book))
4. **Bootstrap coverage**: Run 1000 sims, check 95% CI contains truth 950 times

## Code Structure

```
market_sim/
├── entities.py      # Shift, Nurse classes
├── mechanics.py     # Choice model, ranking logic  
├── discrete.py      # Stages 1-4
├── continuous.py    # Stage 5
├── metrics.py       # Bias calculations
├── bootstrap.py     # Block bootstrap
├── experiments.py   # Parameter sweeps
├── validation.py    # Theoretical benchmarks
└── plots.py         # All visualizations

notebooks/
├── 01_basic_sim.ipynb
├── 02_visualize.ipynb
├── 03_measure_bias.ipynb
├── 04_bootstrap.ipynb
└── 05_reproduce_paper.ipynb
```

## Common Mistakes

1. **Wrong randomization timing**: For LR, assign treatment when shift is created, not each time it reopens
2. **Missing correlations**: Don't just track means. Plot outcome correlations between nearby events
3. **Bad block size**: Too small = underestimate variance. Too big = lose data. Use ~100 events per block
4. **Forgetting edge effects**: First and last blocks are partial. Handle them

## Quick Start Commands

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install numpy pandas matplotlib seaborn tqdm scipy

# Run basic sim
python -m market_sim.discrete --horizon=10000 --viz

# Reproduce paper
python -m market_sim.experiments --figure=7

# Your experiment
python -m market_sim.continuous \
  --lambda_c=0.8 \
  --k=7 \
  --treatment=rank_boost \
  --randomization=LR
```

## Next Steps After Building

1. **Calibrate to your marketplace**: Measure real λ_c, μ, k from logs
2. **Test your actual treatment**: Not just rank boosts
3. **Try time-varying demand**: Peak hours matter
4. **Add hetereogeneity**: Not all nurses/shifts are equal

## Bottom Line

Standard A/B testing lies to you in marketplaces. This simulation proves it and tests fixes. Build it step by step. Validate each stage. Then trust the results.

The goal: Never launch a failed experiment again because you measured it wrong.