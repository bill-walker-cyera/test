# Craps Simulator (Basics)

This project starts with a basic, text-based craps simulator. It focuses on
core game logic without any GUI yet.

## Rules Implemented

- Come-out roll:
  - Win on 7 or 11
  - Lose on 2, 3, or 12
  - Otherwise, that total becomes the point
- Point phase:
  - Win by rolling the point again
  - Lose by rolling a 7

## Usage

Run a single game with roll-by-roll output:

```
python craps_simulator.py
```

Simulate many games and show only summary statistics:

```
python craps_simulator.py --games 10000 --seed 42 --quiet
```

Show roll-by-roll output for each game:

```
python craps_simulator.py --games 3 --verbose
```
