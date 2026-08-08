import time

import pytest

from dotify.api.adapter import validate_response_contract
from dotify.plugins import PluginManager


@pytest.mark.performance
def test_contract_validation_regression_budget():
    response = {"data": {"trackUnion": {}}}
    started = time.perf_counter()
    for _ in range(50_000):
        validate_response_contract("track", response)
    elapsed = time.perf_counter() - started

    # Intentionally generous: catches algorithmic regressions without turning
    # normal differences between CI runners into flaky failures.
    assert elapsed < 2.0


@pytest.mark.performance
def test_plugin_dispatch_regression_budget():
    class NeverMatches:
        def supports(self, item):
            return False

        async def download(self, item):
            return None

    manager = PluginManager(downloaders=[NeverMatches() for _ in range(20)])
    started = time.perf_counter()
    for _ in range(20_000):
        manager.select_downloader(object())
    elapsed = time.perf_counter() - started

    assert elapsed < 2.0
