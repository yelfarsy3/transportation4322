"""Second verification pass, separate from normal tests.

Run from the project root: .venv/bin/python -B tests/audit_reference.py
Includes a larger finite exhaustive domain and deliberately broken variants.
No source files are modified by the mutation checks.
"""
from contextlib import redirect_stderr
import io
from itertools import product
from pathlib import Path
import sys
import types
import unittest

from brute_force_reference import solve_tiny
import test_brute_force_reference as reference_tests


def exhaustive_flat_matrix_check():
    # Third formulation: a flat list of ALL 4^4 matrices, filtered by row/column
    # capacities. No recursion, per-unit assignment, or production helpers.
    matrices = list(product(range(4), repeat=4))
    checked = 0
    for a, b, x, y in product(range(4), repeat=4):
        feasible = [q for q in matrices
                    if q[0]+q[1] <= a and q[2]+q[3] <= b
                    and q[0]+q[2] <= x and q[1]+q[3] <= y]
        maximum = max(sum(q) for q in feasible)
        maximum_matrices = [q for q in feasible if sum(q) == maximum]
        for prices in product(range(4), repeat=4):
            cheapest = min(sum(qi * ci for qi, ci in zip(q, prices))
                           for q in maximum_matrices)
            result = solve_tiny([a,b], [x,y], [prices[:2],prices[2:]])
            assert (result.units, result.cost_cents) == (maximum, cheapest), (a,b,x,y,prices)
            flattened = tuple(q for row in result.shipments for q in row)
            assert flattened in maximum_matrices
            assert sum(qi * ci for qi, ci in zip(flattened, prices)) == cheapest
            checked += 1
    print(f'PASS: {checked} exhaustive 2x2 cases (quantities and costs each 0..3), flat-matrix oracle')


def mutation_checks():
    source = (Path(__file__).parent / 'brute_force_reference.py').read_text()
    mutations = [
        ('cost prioritized before units', 'key = (-units, cost)', 'key = (cost, -units)'),
        ('maximum feasible route quantity omitted', 'range(min(stock[w], needs[s]) + 1)',
         'range(max(1, min(stock[w], needs[s])))'),
        ('wrong store price used', 'quantity * costs[w][s]', 'quantity * costs[w][0]'),
    ]
    original = reference_tests.solve_tiny
    try:
        for index, (name, old, new) in enumerate(mutations):
            assert source.count(old) == 1
            module_name = f'_reference_mutant_{index}'
            module = types.ModuleType(module_name)
            sys.modules[module_name] = module
            try:
                exec(compile(source.replace(old, new), module_name, 'exec'), module.__dict__)
                reference_tests.solve_tiny = module.solve_tiny
                # Target algorithm checks only: avoid artificial exception-class
                # differences between independently loaded modules.
                names = ['test_manual_original_and_partial_ui',
                         'test_manual_greedy_counterexample',
                         'test_units_take_priority_over_cost',
                         'test_zero_exact_excess_and_shortage',
                         'test_ties_and_free_shipping']
                suite = unittest.TestSuite(reference_tests.BruteForceReferenceTests(n) for n in names)
                with redirect_stderr(io.StringIO()):
                    result = unittest.TextTestRunner(stream=io.StringIO()).run(suite)
                assert not result.wasSuccessful(), f'Tests missed mutation: {name}'
                assert result.failures, f'Mutation caused only errors, not assertion failures: {name}'
                print(f'PASS: tests detected deliberate defect: {name}')
            finally:
                del sys.modules[module_name]
    finally:
        reference_tests.solve_tiny = original


if __name__ == '__main__':
    exhaustive_flat_matrix_check()
    mutation_checks()
