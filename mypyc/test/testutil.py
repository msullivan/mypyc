"""Helpers for writing tests"""

import contextlib
import os.path
import shutil
from typing import List

from mypy import build
from mypy.errors import CompileError
from mypy.options import Options
from mypy.test.config import test_temp_dir

from mypyc import genops
from mypyc.ops import FuncIR
from mypyc.test.config import test_data_prefix

# The builtins stub used during icode generation test cases.
ICODE_GEN_BUILTINS = os.path.join(test_data_prefix, 'fixtures/ir.py')


def builtins_wrapper(func, path):
    """Decorate a function that implements a data-driven test case to copy an
    alternative builtins module implementation in place before performing the
    test case. Clean up after executing the test case.
    """
    return lambda testcase: perform_test(func, path, testcase)


@contextlib.contextmanager
def use_custom_builtins(builtins_path, testcase):
    for path, _ in testcase.files:
        if os.path.basename(path) == 'builtins.pyi':
            default_builtins = False
            break
    else:
        # Use default builtins.
        builtins = os.path.join(test_temp_dir, 'builtins.pyi')
        shutil.copyfile(builtins_path, builtins)
        default_builtins = True

    # Actually peform the test case.
    yield None

    if default_builtins:
        # Clean up.
        os.remove(builtins)


def perform_test(func, builtins_path, testcase):
    for path, _ in testcase.files:
        if os.path.basename(path) == 'builtins.py':
            default_builtins = False
            break
    else:
        # Use default builtins.
        builtins = os.path.join(test_temp_dir, 'builtins.py')
        shutil.copyfile(builtins_path, builtins)
        default_builtins = True

    # Actually peform the test case.
    func(testcase)

    if default_builtins:
        # Clean up.
        os.remove(builtins)


def build_ir_for_single_file(input_lines: List[str]) -> List[FuncIR]:
    program_text = '\n'.join(input_lines)

    options = Options()
    options.show_traceback = True
    options.use_builtins_fixtures = True
    options.strict_optional = True

    source = build.BuildSource('main', '__main__', program_text)
    # Construct input as a single single.
    # Parse and type check the input program.
    result = build.build(sources=[source],
                         options=options,
                         alt_lib_path=test_temp_dir)
    if result.errors:
        raise CompileError(result.errors)
    module = genops.build_ir(result.files['__main__'], result.types)
    return module.functions
