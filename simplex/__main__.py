import argparse
import pathlib
import sys

# enable `python simplex` instead of `python -m simplex`
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import simplex


def main(filename, solver, method, latex, m):
    # resolve CLI parameters
    match solver:
        case 'bigm':
            solver = simplex.solvers.BigmSimplexSolver()
            solver.m = m
        case 'twophase' | '2phase':
            solver = simplex.solvers.TwophaseSimplexSolver()
    match method:
        case 'tableau' | 'tableau_alt':
            if latex:
                formatter = simplex.formatters.TableauLatexFormatter()
            else:
                formatter = simplex.formatters.TableauCliFormatter()
            formatter.opposite_obj = 'alt' not in method
        case 'compact' | 'compact_alt':
            if latex:
                formatter = simplex.formatters.TableauLatexFormatter()
            else:
                formatter = simplex.formatters.TableauCliFormatter()
            formatter.compact = True
            formatter.opposite_obj = 'alt' not in method
        case 'dict' | 'dictionary':
            if latex:
                formatter = simplex.formatters.DictLatexFormatter()
            else:
                formatter = simplex.formatters.DictCliFormatter()
    solver.formatter = formatter

    # parse input
    print(formatter.format_section('Initialization'))
    print(formatter.format_step(f'Raw input ({filename})'))
    with pathlib.Path.open(filename, 'r') as f:
        raw = f.read()
    print(formatter.format_raw_model(raw))
    print()

    # print parsed program
    print(formatter.format_step('Parsed program'))
    model = simplex.core.Model.parse_str(raw)
    print(formatter.format_raw_model(str(model)))
    print()

    # call solver
    solver.solve(model)

    # print solver summary
    print()
    print(formatter.format_section('Summary'))
    print(formatter.format_summary(solver.summary, solver.renames))

    # return summary for automated testing purposes
    return solver.summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Simple Simplex Solver')
    parser.add_argument('--program', type=pathlib.Path, required=True)
    parser.add_argument('--solver', type=str, default='bigm', choices={'bigm', 'twophase', '2phase'})
    parser.add_argument('--method', type=str, default='dictionary', choices={'tableau', 'compact', 'tableau_alt', 'compact_alt', 'dict', 'dictionary'})
    parser.add_argument('--latex', action='store_true')
    parser.add_argument('--m', type=int, default=3628800)
    args = parser.parse_args()

    main(args.program, args.solver, args.method, args.latex, args.m)
