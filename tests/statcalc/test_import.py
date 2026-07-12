import subprocess
import sys


def test_statcalc_imported_from_package_root() -> None:
    from swgoh_comlink import StatCalc

    assert StatCalc is not None


def _run_in_fresh_interpreter(code: str) -> None:
    """Import-order tests need a pristine interpreter — sys.modules is
    process-global, so the current process's import history would mask
    ordering bugs."""
    subprocess.run([sys.executable, "-c", code], check=True)


def test_statcalc_class_survives_submodule_import_first() -> None:
    """Regression: importing a swgoh_comlink.StatCalc.* module path makes the
    import machinery bind the subpackage onto the package, which used to
    shadow the lazy class export ('module' object is not callable)."""
    _run_in_fresh_interpreter(
        "from swgoh_comlink.StatCalc.data_builder import GameDataBuilder\n"
        "from swgoh_comlink import StatCalc\n"
        "import inspect\n"
        "assert inspect.isclass(StatCalc), type(StatCalc)\n"
    )


def test_statcalc_class_survives_submodule_import_after() -> None:
    """The reverse order must hold too: the machinery's post-import setattr
    of the subpackage must not clobber an already-resolved class."""
    _run_in_fresh_interpreter(
        "from swgoh_comlink import StatCalc\n"
        "from swgoh_comlink.StatCalc.data_builder import GameDataBuilder\n"
        "import swgoh_comlink, inspect\n"
        "assert inspect.isclass(StatCalc), type(StatCalc)\n"
        "assert inspect.isclass(swgoh_comlink.StatCalc), type(swgoh_comlink.StatCalc)\n"
    )
