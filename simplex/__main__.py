import argparse
import pathlib
import sys

# enable `python simplex` instead of `python -m simplex`
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import simplex


def print_tableau(tableau, method):
    if method == 'tableau':
        for line in tableau.to_tab().split('\n'):
            print(f'    {line}')
    else:
        for line in tableau.to_dict().split('\n'):
            print(f'    {line}')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Simplex')
    parser.add_argument('--program', type=pathlib.Path, required=True)
    parser.add_argument('--method', type=str, default='dictionary', choices={'tableau', 'dictionary'})
    args = parser.parse_args()

    print('[1] PARSING INPUT')
    print('-----------------')
    print(f'Raw input: ({args.program})')
    with pathlib.Path.open(args.program, 'r') as f:
        raw = f.read()
    for line in raw.split('\n'):
        if line.strip():
            print(f'    {line}')
    print()

    p = simplex.Program.parse_str(raw)
    print('Parsed program:')
    for line in str(p).split('\n'):
            print(f'    {line}')
    tmp = str(p)

    print()
    print('[2] NORMALISATION')
    print('--------------------------------')
    p.do_normalize()
    if str(p) == tmp:
        print('Program already normalised')
    else:
        print('After normalisation:')
        for line in str(p).split('\n'):
            print(f'    {line}')
        tmp = str(p)

    if p.summary['status'] == '???':
        print()
        print('[3] CONVERSION TO CANONICAL FORM')
        print('--------------------------------')
        p.do_canonical()
        if str(p) == tmp:
            print('Program already in canonical form')
        else:
            print('Program in canonical form:')
            for line in str(p).split('\n'):
                print(f'    {line}')
            tmp = str(p)
        p.do_trivial_check()
        if p.summary['status'] == '???' and str(p) != tmp:
            print('Program in canonical form: (reordered)')
            for line in str(p).split('\n'):
                print(f'    {line}')
            tmp = str(p)

    if p.summary['status'] == '???':
        print()
        print('[4] CONVERSION TO STANDARD FORM')
        print('-------------------------------')
        p.do_standard()
        if str(p) == tmp:
            print('Program already in standard form')
        else:
            print('Program in standard form:')
            for line in str(p).split('\n'):
                print(f'    {line}')

    if p.summary['status'] == '???':
        print()
        print('[5] PRE-SIMPLEX PROGRAM')
        print('-----------------------')
        p.do_tableau()
    if p.summary['status'] == '???':
        print(f'Initial {args.method}:')
        print_tableau(p.tableau, args.method)

    if p.summary['status'] == '???':
        print()
        if p.artificial_variables:
            print('[6.1] RESOLUTION (big-M)')
            print('--------------')
            to_delete = []
            while p.summary['status'] == '???':
                coefs_obj = p.tableau.coefs_obj(p.tableau.basis)
                problematic = [var for var in p.tableau.basis if coefs_obj[var] > 0]
                if not problematic:
                    break
                to_delete += problematic
                p.do_simplex_prestep()
                if p.summary['status'] == '???':
                    print_tableau(p.tableau, args.method)
                    print()
            while p.summary['status'] == '???':
                coefs = p.tableau.coefs_column('')
                problematic = [var for var in p.tableau.basis if coefs[var] < 0]
                if not problematic:
                    break
                p.do_simplex_prestep()
                if p.summary['status'] == '???':
                    print_tableau(p.tableau, args.method)
                    print()
            if p.summary['status'] == '???':
                p.do_simplify_artificial(to_delete)
                print(f'New simplified {args.method}: (removing artificial variables)')
                print_tableau(p.tableau, args.method)
                print()
                print('[6.2] RESOLUTION (main)')
                print('--------------')
        else:
            print('[6] RESOLUTION')
            print('--------------')
        if p.summary['status'] == '???':
            p.do_simplex_step()
            while p.summary['status'] == '???':
                print_tableau(p.tableau, args.method)
                print()
                p.do_simplex_step()
        if p.summary['status'] == '???':
            print()
            print(f'Final {args.method}:')
            print_tableau(p.tableau, args.method)
        p.do_simplex_final()

    print()
    print('[7] SUMMARY')
    print('-----------')
    status = p.summary['status']
    print(f'Status: {status}')
    if p.summary['values']:
        print('Final values:')
        for k, v in p.summary['values'].items():
            e = simplex.ExprTree.from_string(str(v))
            simplex.Rewriter().normalize(e)
            v2 = e.evaluate({})
            if str(e) == str(v2):
                v2 = None
            if k in p.renames:
                e = p.renames[k]
                if v2:
                    print(f'    {k} = {e} = {v} = {round(v2, 8)}')
                else:
                    print(f'    {k} = {e} = {v}')
            elif v2:
                print(f'    {k} = {v} = {round(v2, 8)}')
            else:
                print(f'    {k} = {v}')
