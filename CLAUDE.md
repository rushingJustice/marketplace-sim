# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Writing Style

Use simple language: Write plainly with short sentences.

Example: "I need help with this issue."

Avoid AI-giveaway phrases: Don't use clichés like "dive into," "unleash your potential," etc.

Avoid: "Let's dive into this game-changing solution."

Use instead: "Here's how it works."

Be direct and concise: Get to the point; remove unnecessary words.

Example: "We should meet tomorrow."

Maintain a natural tone: Write as you normally speak; it's okay to start sentences with "and" or "but."

Example: "And that's why it matters."

Avoid marketing language: Don't use hype or promotional words.

Avoid: "This revolutionary product will transform your life."

Use instead: "This product can help you."

Keep it real: Be honest; don't force friendliness.

Example: "I don't think that's the best idea."

Simplify grammar: Don't stress about perfect grammar; it's fine not to capitalize "i" if that's your style.

Example: "i guess we can try that."

Stay away from fluff: Avoid unnecessary adjectives and adverbs.

Example: "We finished the task."

Focus on clarity: Make your message easy to understand.

Example: "Please send the file by Monday."

## Project Overview

This is a marketplace interference simulation implementing the Li, Johari & Weintraub (2022) model to demonstrate how A/B tests in marketplaces are biased due to interference effects. The simulation models a nurse job board where boosting some shifts steals demand from others, showing how standard statistical methods fail in marketplace settings.

## Key Concepts

- **Interference**: When treatment affects control group outcomes through supply/demand dynamics
- **Customer Randomization (CR)**: Randomly assign each arriving customer to treatment/control
- **Listing Randomization (LR)**: Randomly assign each listing/shift to treatment/control at start
- **Positive Interventions**: Treatments that increase utilities (most common marketplace experiments)
- **Block Bootstrap**: Method to correct standard error bias by resampling time blocks

## Development Stages (Build Order)

Follow these stages sequentially - each builds on the previous:

1. **Stage 1**: Basic discrete-time model with core mechanics
2. **Stage 2**: Add visualizations (heatmaps, booking timelines)  
3. **Stage 3**: Add metrics and both randomization types (CR/LR)
4. **Stage 4**: Implement block bootstrap for correct standard errors
5. **Stage 4.5**: Bridge to continuous time with smaller timesteps
6. **Stage 5**: Full continuous time with event queues
7. **Stage 6**: Parameter sweeps for bias analysis

## Core Architecture

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

## Key Model Components

### Shift Class
```python
class Shift:
    id: int
    base_utility: float
    is_treated: bool
    status: str  # "open" or "filled"
    filled_until: float  # when it reopens
```

### Nurse Class  
```python
class Nurse:
    id: int
    arrived_at: float
    is_treated: bool  # for nurse-side randomization
```

### Position-Based Choice Model
- Nurses see top k shifts ranked by utility
- Position weights: [1.0, 0.8, 0.6, 0.4, 0.2] (first slot best)
- Probability ∝ position_weight × exp(utility)

## Critical Implementation Details

- **Treatment Assignment**: For LR, assign at shift creation, NOT each reopen
- **Ranking**: Treated shifts sort first, then by utility (not just utility boost)
- **Supply Dynamics**: When booked, shift reopens after exponential(1/μ) time
- **Block Bootstrap**: Use ~100 events per block, handle edge effects

## Common Commands

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install numpy pandas matplotlib seaborn tqdm scipy

# Run basic simulation
python -m market_sim.discrete --horizon=10000 --viz

# Reproduce paper figures
python -m market_sim.experiments --figure=7

# Custom experiment
python -m market_sim.continuous \
  --lambda_c=0.8 \
  --k=7 \
  --treatment=rank_boost \
  --randomization=LR
```

## Validation Checkpoints

1. **Sanity Check**: Set μ=1000 (instant reopen) → no bias
2. **Booking Rate**: Should ≈ λ_c × P(match|arrival)  
3. **Availability**: Fraction open = μ/(μ + λ×P(book))
4. **Bootstrap Coverage**: 95% CI should contain truth 95% of time

## Key Biases to Measure

- **GTE Bias**: Both CR and LR overestimate treatment effects
- **SE Bias**: CR underestimates standard errors (negative correlation)
- **Decision Impact**: Combination leads to false positive launches

## Critical Parameters

- **ρ = λ/μ**: Demand/supply ratio (key driver of bias magnitude)
- **k**: Consideration set size (how many shifts nurses see)
- **Treatment strength**: How much to boost treated items
- **Block size**: For bootstrap (~100 events, tune empirically)

## Paper Reference

Based on "Marketplace Experimentation: Interference, Inference, and Decisions" by Li, Johari & Weintraub (2022). The simulation should reproduce their Figures 7-8 showing bias patterns across different market conditions.