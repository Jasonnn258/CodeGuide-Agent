from task_056_lib.stats import report


def test_report_with_values():
    result = report([1.0, 2.0, 3.0])
    assert result["sum"] == 6.0
    assert result["count"] == 3
    assert result["mean"] == 2.0


def test_report_single_value():
    result = report([42.0])
    assert result["sum"] == 42.0
    assert result["count"] == 1
    assert result["mean"] == 42.0
