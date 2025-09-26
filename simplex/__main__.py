import argparse
import pathlib
import sys

# enable `python simplex` instead of `python -m simplex`
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import simplex


def main(filename, solver, method, latex):
    # resolve CLI parameters
    match solver:
        case 'bigm':
            solver = simplex.solvers.BigmSimplexSolver()
        case 'twophase' | '2phase':
            solver = simplex.solvers.TwophaseSimplexSolver()
    match method:
        case 'tableau':
            if latex:
                formatter = simplex.formatters.TableauLatexFormatter()
            else:
                formatter = simplex.formatters.TableauCliFormatter()
        case 'compact':
            if latex:
                formatter = simplex.formatters.TableauLatexFormatter()
            else:
                formatter = simplex.formatters.TableauCliFormatter()
            formatter.compact = True
        case 'dict' | 'dictionary':
            if latex:
                formatter = simplex.formatters.DictLatexFormatter()
            else:
                formatter = simplex.formatters.DictCliFormatter()
    solver.formatter = formatter

    # parse input
    print(formatter.format_section('Parsing Input'))
    with pathlib.Path.open(filename, 'r') as f:
        raw = f.read()
    out = formatter.format_raw_model(raw)
    if out:
        print(f'Raw input: ({filename})')
        print(out)
        print()

    # print parsed program
    model = simplex.core.Model.parse_str(raw)
    out = formatter.format_raw_model(str(model))
    if out:
        print('Parsed program:')
        print(out)
        print()

    # call solver
    solver.solve(model)

    # print solver summary
    print()
    print(formatter.format_section('Summary'))
    status = solver.summary['status']
    print(f'Status: {status}')
    if solver.summary['values']:
        print('Final values:')
        for k, v in solver.summary['values'].items():
            e = simplex.parsing.ExprTree.from_string(str(v))
            solver.rewriter.normalize(e)
            v2 = e.evaluate({})
            if str(e) == str(v2):
                v2 = None
            if k in solver.renames:
                e = solver.renames[k]
                if str(e) == str(v):
                    print(f'    {k} = {v}')
                elif v2:
                    print(f'    {k} = {e} = {v} = {round(v2, 8)}')
                else:
                    print(f'    {k} = {e} = {v}')
            elif v2:
                print(f'    {k} = {v} = {round(v2, 8)}')
            else:
                print(f'    {k} = {v}')

    # return summary for automated testing purposes
    return solver.summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Simple Simplex Solver')
    parser.add_argument('--program', type=pathlib.Path, required=True)
    parser.add_argument('--solver', type=str, default='bigm', choices={'bigm', 'twophase', '2phase'})
    parser.add_argument('--method', type=str, default='dictionary', choices={'tableau', 'compact', 'dict', 'dictionary'})
    parser.add_argument('--latex', action='store_true')
    args = parser.parse_args()

    main(args.program, args.solver, args.method, args.latex)
