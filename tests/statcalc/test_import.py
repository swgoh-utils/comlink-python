def test_statcalc_imported_from_package_root() -> None:
    from swgoh_comlink import StatCalc

    assert StatCalc is not None
