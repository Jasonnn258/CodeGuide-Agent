from task_052_lib.temperature import celsius_to_fahrenheit


def test_one_degree_is_not_integer_fahrenheit():
    assert celsius_to_fahrenheit(1) == 33.8


def test_negative_temperature_precision():
    assert celsius_to_fahrenheit(-40) == -40.0
