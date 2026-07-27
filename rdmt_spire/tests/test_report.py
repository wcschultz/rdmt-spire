from datetime import datetime

from ..constants.dmd import FileTypes
from ..constants.lambdas import GUIDE_WINDOW_REPORTING_TOPIC, SCIENCE_REPORTING_TOPIC
from ..lambdas.report import (
    _get_report_spec,
    get_failed_evaluations,
    get_monitored_files,
)


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class _FakeDuckDBConnection:
    def __init__(self, rows):
        self._rows = rows
        self.last_query = None
        self.last_params = None

    def execute(self, query, params):
        self.last_query = query
        self.last_params = params
        return _FakeResult(self._rows)


def test_get_report_spec_science_and_guide_window():
    params = {
        SCIENCE_REPORTING_TOPIC: "science-topic",
        GUIDE_WINDOW_REPORTING_TOPIC: "guide-window-topic",
    }

    science_spec = _get_report_spec(FileTypes.L2_SCIENCE, params)
    guide_window_spec = _get_report_spec(FileTypes.L1_GUIDE_WINDOW, params)

    assert science_spec.start_time_column == "exp_start_datetime"
    assert science_spec.summary_id_column == "observation_id"
    assert science_spec.reporting_topic_name == "science-topic"

    assert guide_window_spec.start_time_column == "acq_start_datetime"
    assert guide_window_spec.summary_id_column == "acquisition_id"
    assert guide_window_spec.reporting_topic_name == "guide-window-topic"


def test_get_failed_evaluations_uses_report_specific_columns():
    params = {GUIDE_WINDOW_REPORTING_TOPIC: "guide-window-topic"}
    report_spec = _get_report_spec(FileTypes.L1_GUIDE_WINDOW, params)
    report_time = datetime(2026, 7, 8, 12, 0, 0)
    connection = _FakeDuckDBConnection(
        [("file.asdf", 2, "mean_noise", 1.23456, False)]
    )

    eval_str = get_failed_evaluations(
        connection,
        "s3://bucket/*/*/*.parquet",
        report_time,
        report_spec,
    )

    assert "acq_start_datetime" in connection.last_query
    assert "mean_noise = 1.2346" in eval_str
    assert connection.last_params == (report_time,)


def test_get_monitored_files_uses_report_specific_summary_column():
    params = {GUIDE_WINDOW_REPORTING_TOPIC: "guide-window-topic"}
    report_spec = _get_report_spec(FileTypes.L1_GUIDE_WINDOW, params)
    report_time = datetime(2026, 7, 8, 12, 0, 0)
    connection = _FakeDuckDBConnection(
        [(datetime(2026, 7, 8).date(), 1, 42, 7, ["wfi01", "wfi03"], 2)]
    )

    info_str = get_monitored_files(
        connection,
        "s3://bucket/*/*/*.parquet",
        report_time,
        report_spec,
    )

    assert "acquisition_id" in connection.last_query
    assert "acq_start_datetime" in connection.last_query
    assert "7 (rep # 1)" in info_str
    assert "ALERT: Only received detectors 1 ,3" in info_str
    assert connection.last_params == (report_time,)