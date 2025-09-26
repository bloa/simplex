# Simple Simplex Solver

A minimal Python implementation of the simplex algorithm, intended for academic and teaching purposes.


## Installation

No installation is required beyond cloning this repository.  
The solver has no external dependencies.
Python 3.11 or later is recommended.

```bash
git clone https://github.com/bloa/simplex.git
cd simplex
```


## Usage

To try the solver, run it on the provided example problems:

```bash
python3 simplex --program examples/test_solved1
```

You can choose between the big-M (with `bigm`, the default) and the Two-Phase (`twophase`) methods using `--solver`.
You can choose between a tableau-based (with `tableau` or `compact`) or dictionary-based (with `dictionnary`, the default) representation using `--method`.
For example:

```bash
python3 simplex --program examples/test_solved6 --solver twophase --method tableau
```

LaTeX formatting is supported through the `--latex` option:

```bash
python3 simplex --program examples/test_solved4 --method compact --latex
```

In doubt, consult the help message:

```bash
python3 simplex --help
```


## Testing

Run the test suite with [pytest](https://pytest.org/):

```bash
pytest
```

## Contributions

Contributions are welcome via pull requests.

Planned improvements include:
- interactive mode for selecting pivots
- support for solving through the dual problem
