from task_077_lib.stack import IntStack


def test_clear_resets_popped_count():
    s = IntStack()
    s.push(10)
    s.push(20)
    s.pop()
    assert s.popped_count() == 1
    s.clear()
    assert s.popped_count() == 0


def test_fresh_stack_has_zero_popped_count():
    s = IntStack()
    assert s.popped_count() == 0
    s.push(1)
    s.pop()
    assert s.popped_count() == 1
