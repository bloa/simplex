import argparse
import pathlib
import sys

# enable `python simplex` instead of `python -m simplex`
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import simplex


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Simplex')
    parser.add_argument('--program', type=pathlib.Path, required=True)
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

    print()
    print('[2] NORMALISATION')
    print('--------------------------------')
    p.do_renames()
    p.do_normalize()
    print('After normalisation:')
    for line in str(p).split('\n'):
        print(f'    {line}')

    if p.summary['status'] == '???':
        print()
        print('[3] CONVERSION TO CANONICAL FORM')
        print('--------------------------------')
        p.do_canonical()
        print('Program in canonical form:')
        for line in str(p).split('\n'):
            print(f'    {line}')

    if p.summary['status'] == '???':
        print()
        print('[4] CONVERSION TO STANDARD FORM')
        print('-------------------------------')
        p.do_standard()
        print('Program in standard form:')
        for line in str(p).split('\n'):
            print(f'    {line}')

    if p.summary['status'] == '???':
        print()
        print('[5] PRE-SIMPLEX PROGRAM')
        print('-----------------------')
        p.do_tableau()
    if p.summary['status'] == '???':
        print('Initial tableau:')
        for line in p.tableau.to_tab().split('\n'):
            print(f'    {line}')
        print()
        print('Initial dictionary:')
        for line in p.tableau.to_dict().split('\n'):
            print(f'    {line}')

    if p.summary['status'] == '???':
        print()
        print('[6] RESOLUTION')
        print('--------------')
        while p.summary['status'] == '???':
            p.do_simplex_step()
        print()
        print('Final dictionary:')
        for line in p.tableau.to_dict().split('\n'):
            print(f'    {line}')
        p.do_simplex_final()

    print()
    print('[7] SUMMARY')
    print('-----------')
    status = p.summary['status']
    print(f'Status: {status}')
    if 'values' in p.summary:
        print('Final values:')
        for k, v in p.summary['values'].items():
            e = simplex.ExprTree.from_string(str(v))
            e.normalize()
            v2 = e if str(e) != str(v) else None
            if k in p.renames:
                e = p.renames[k]
                if v2:
                    print(f'    {k} = {e} = {v2} = {v}')
                else:
                    print(f'    {k} = {e} = {v}')
            elif v2:
                print(f'    {k} = {v2} = {v}')
            else:
                print(f'    {k} = {v}')
