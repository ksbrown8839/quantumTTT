# Quantum Tic-Tac-Toe
Play Quantum Tic-Tac-Toe with real IBM hardware (when available) with a backup of Qiskit's quantum simulator. Includes optional “chaos mode” for extra quantum shenanigans.

## Features
- Quantum coin flips sourced from IBM qubit hardware, with Aer simulator and classical simulation as backup options.
- Tkinter GUI with spooky move selection, loop-induced collapse, and winner detection.
- Chaos mode: entangling circuit drives extra effects (swap/rotate/flip), rare green Y “gifts” that block cells.
- Async prefill of quantum bits to reduce UI stalls; optional histogram export of measurement counts.
- Flags to force simulator (`--force-aer`) or enable chaos (`--chaos`).

## Prerequisites
- Python 3.10+ recommended.
- Packages: `qiskit-ibm-runtime`, `qiskit-aer`, `matplotlib`, `tk`. (The game prints a warning and falls back if missing.)
- IBM Quantum account configured for hardware access if you want real device runs.

## Setup
```bash
pip install qiskit-ibm-runtime qiskit-aer matplotlib
```
If Tkinter is missing on your platform, install the system Tk packages (varies by OS).

## Running
```bash
python quantum_ttt.py [--force-aer] [--chaos]
```

### Flags
- `--force-aer`: skip hardware, use the Aer simulator immediately.
- `--chaos`: enable chaos effects (swap/rotate/flip) and rare green Y blocking marks (~5% chance per collapse by default).

### Gameplay Basics
- Click one square to start a spooky pair; click a different square to place it. Click the same square again to cancel your first selection.
- Forming a loop triggers collapse mode; the designated player chooses which square each spooky marker collapses to.
- During collapse, you can press “Quantum collapse” to let the quantum coin pick (0 -> first square, 1 -> second square).
- Chaos mode may introduce random board tweaks and green Y markers that block a cell for the rest of the game.

## Quantum Bits & Histograms
- Quantum coins are prefetched asynchronously; a buffer refills in the background.
- If `matplotlib` is available and `save_histogram=True` (default), measurement counts are saved to `Q-histogram.png`.

## Troubleshooting
- Missing `qiskit-ibm-runtime` or `qiskit-aer`: the app logs a warning and falls back (hardware -> Aer -> classical RNG).
- Long hardware waits: use `--force-aer` or increase shots only if needed.
- Tkinter not found: install your OS’s Tk package (e.g., `sudo apt-get install python3-tk` on Debian/Ubuntu).

## License
MIT (if you prefer another license, update this section.)
