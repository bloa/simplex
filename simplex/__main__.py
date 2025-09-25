import argparse
import pathlib
import sys

# enable `python simplex` instead of `python -m simplex`
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import simplex


def main(filename, solver, method, latex):
    match solver:
        case 'bigm':
            solver = simplex.solvers.BigmSimplexSolver()
        case 'twophase' | '2phase':
            solver = simplex.solvers.TwophaseSimplexSolver()
        case _:
            msg = f'Unknown solver: {solver}'
            raise ValueError(msg)
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
        case _:
            msg = f'Unknown method: {method}'
            raise ValueError(msg)
    solver.formatter = formatter

    print('[1] PARSING INPUT')
    print('----------------------------------------')
    print(f'Raw input: ({filename})')
    with pathlib.Path.open(filename, 'r') as f:
        raw = f.read()
    for line in raw.split('\n'):
        if line.strip():
            print(f'    {line}')
    print()

    model = simplex.core.Model.parse_str(raw)
    print('Parsed program:')
    out = str(model)
    for line in out.split('\n'):
            print(f'    {line}')
    tmp = out

    print()
    print('[2] NORMALISING')
    print('----------------------------------------')
    solver.do_normalize(model)
    out = formatter.format_model(model)
    if out == tmp:
        print('Program already normalised')
    else:
        print('Normalised program:')
        for line in out.split('\n'):
            print(f'    {line}')
        tmp = out

    print()
    print('[3] SOLVING')
    print('----------------------------------------')
    solver.solve(model)

    print()
    print('[4] SUMMARY')
    print('----------------------------------------')
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
                if v2:
                    print(f'    {k} = {e} = {v} = {round(v2, 8)}')
                else:
                    print(f'    {k} = {e} = {v}')
            elif v2:
                print(f'    {k} = {v} = {round(v2, 8)}')
            else:
                print(f'    {k} = {v}')

    return solver.summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Simplex')
    parser.add_argument('--program', type=pathlib.Path, required=True)
    parser.add_argument('--solver', type=str, default='bigm', choices={'bigm', 'twophase', '2phase'})
    parser.add_argument('--method', type=str, default='dictionary', choices={'tableau', 'compact', 'dict', 'dictionary'})
    parser.add_argument('--latex', action='store_true')
    args = parser.parse_args()

    main(args.program, args.solver, args.method, args.latex)
