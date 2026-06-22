from task_056_lib.stats import report


def test_report_empty_list_returns_zeros():
    result = report([])
    assert result["sum"] == 0.0
    assert result["count"] == 0
    assert result["mean"] == 0.0
