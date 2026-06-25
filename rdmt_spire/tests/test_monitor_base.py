import asdf

from ..monitors.monitor_base import BaseMonitor


def test_base_monitor():
    """
    Testing class BaseMonitor
    """
    BaseMonitor.__abstractmethods__ = set()
    monitor=BaseMonitor(asdf.AsdfFile())
    monitor.run()
    assert monitor.monitor_name == 'base_monitor'