import json
from dataclasses import asdict

import asdf

from ..constants.codes import StatusCodes
from ..manager import MonitorManager
from ..monitors.monitor_base import BaseMonitor
from ..monitors.noise_1f import Noise1fMonitor


def test_monitor_manager():
    """
    Testing class MonitorManager
    """
    BaseMonitor.__abstractmethods__ = set()
    monitor_manager = MonitorManager(asdf.AsdfFile(), "base_monitor")
    monitor_manager.process()
    assert monitor_manager.statusCode == StatusCodes.SUCCESS
    assert len(monitor_manager.monitor_objects) == 1
    assert monitor_manager.monitor_objects[0].monitor_name == "base_monitor"

    # Checking class MonitorManager.response_for_lambda()
    response = monitor_manager.response_for_lambda()
    assert response["statusCode"] == StatusCodes.SUCCESS
    data_cards = monitor_manager.monitor_objects[0].get_data_card("all")
    body = json.loads(response["body"])
    assert len(body) == len(data_cards)
    for i, data_card in enumerate(data_cards):
        assert body[i] == asdict(data_card)
    # Checking class MonitorManager handling of exceptions
    # Check exceptions are correctly handled
    monitor_manager = MonitorManager("", "base_monitor")
    monitor_manager.process()
    assert monitor_manager.statusCode == StatusCodes.FAILURE
    response = monitor_manager.response_for_lambda()
    body = json.loads(response["body"])
    assert "error_message" in body[0]

    monitor_manager = MonitorManager(asdf.AsdfFile(), "non_existing_monitor")
    monitor_manager.process()
    assert monitor_manager.statusCode == StatusCodes.FAILURE
    response = monitor_manager.response_for_lambda()
    body = json.loads(response["body"])
    assert "error_message" in body[0]


def test_monitor_manager_double():
    """
    Testing class MonitorManager
    """
    # Checking class MonitorManager with two monitors
    monitor_config = {"astrometry": {"datadir": ""}}
    monitor_manager = MonitorManager(
                                        asdf.AsdfFile(), 
                                        "astrometry", 
                                        monitor_config=monitor_config
                                    )
    monitor_manager.monitor_objects.append(Noise1fMonitor(asdf.AsdfFile()))
    assert len(monitor_manager.monitor_objects) == 2
    assert monitor_manager.monitor_objects[0].monitor_name == "astrometry"
    assert monitor_manager.monitor_objects[1].monitor_name == "noise_1f"
    monitor_manager.process()
    assert monitor_manager.statusCode == StatusCodes.FAILURE
    data_cards = []
    for monitor_obj in monitor_manager.monitor_objects:
        data_cards.extend(monitor_obj.get_data_card("all"))
    assert len(data_cards) == 2
