"""
Tests :mod:`app` module
Command: exec
"""
import pytest

from taro import runner
from taro.execution import ExecutionState
from taro.test.observer import TestObserver
from test.util import run_app


@pytest.fixture
def observer():
    observer = TestObserver(support_waiter=True)
    runner.register_observer(observer)
    yield observer
    runner.deregister_observer(observer)


def test_exec_echo(observer: TestObserver):
    run_app('exec echo this binary universe')
    assert observer.exec_state(-1) == ExecutionState.COMPLETED
