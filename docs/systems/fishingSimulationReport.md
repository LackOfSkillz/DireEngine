# Fishing Simulation Report

Generated: 2026-04-09 14:50:08
Scenario: fishing-simulation-100
Runs per pass: 100
Passes: 2
Fish group: River 1
Location safety: safe-zone enabled

## Expected Distribution
- Fish: 64.0%
- Common junk: 28.0%
- Valuable junk: 6.0%
- Event: 2.0%

## Pass A
- Fish: 60 (60.0%)
- Common junk: 28 (28.0%)
- Valuable junk: 9 (9.0%)
- Event: 3 (3.0%)
- Total value sold: 1323 coins
- Average sale per run: 13.23 coins
- Outdoorsmanship pool gain: 1000.00
- Skinning pool gain: 0.00
- Mindstates: outdoorsmanship 0 -> 34, skinning 0 -> 0
- Violent tug line breaks: 3
- Failure count: 0

## Pass B
- Fish: 71 (71.0%)
- Common junk: 20 (20.0%)
- Valuable junk: 8 (8.0%)
- Event: 1 (1.0%)
- Total value sold: 1747 coins
- Average sale per run: 17.47 coins
- Outdoorsmanship pool gain: 1000.00
- Skinning pool gain: 0.00
- Mindstates: outdoorsmanship 0 -> 34, skinning 0 -> 0
- Violent tug line breaks: 1
- Failure count: 0

## Catch Breakdown
- Pass A fish: {'silver trout': 41, 'mud carp': 19}
- Pass A junk: {'weeds': 10, 'tangled line': 8, 'broken branch': 4, 'old boot': 6, 'trinket': 3, 'coin pouch': 2, 'rusted dagger': 2, 'lost charm': 2}
- Pass B fish: {'silver trout': 50, 'mud carp': 21}
- Pass B junk: {'coin pouch': 4, 'broken branch': 11, 'old boot': 4, 'trinket': 2, 'rusted dagger': 2, 'weeds': 5}

## Distribution Comparison
- Fish actual vs expected: 65.5% vs 64.0%
- Common junk actual vs expected: 24.0% vs 28.0%
- Valuable junk actual vs expected: 8.5% vs 6.0%
- Event actual vs expected: 2.0% vs 2.0%
- Pass variance: {'fish': 11.0, 'junk': 8.000000000000004, 'valuable_junk': 1.0, 'event': 2.0}

## Bite Timing
- Avg: 7.0s
- Min: 4.0s
- Max: 10.0s

## Balance Answers
- Is junk too frequent? No.
- Are valuable junk items too generous? No.
- Are violent tug events noticeable but not annoying? Yes.
- Stable across rerun? No. Variance exceeded the acceptable 10% band.

## Safety
- Total violent tug events: 4
- Total line breaks: 4
- Total gear damage events: 4
- Total failures: 0
