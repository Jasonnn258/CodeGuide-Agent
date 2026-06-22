from task_077_lib.stack import IntStack


def test_push_and_pop():
    s = IntStack()
    s.push(1)
    s.push(2)
    assert s.pop() == 2
    assert s.pop() == 1


def test_size_after_operations():
    s = IntStack()
    s.push(10)
    s.push(20)
    s.pop()
    assert s.size() == 1


def test_clear_empties_stack():
    s = IntStack()
    s.push(1)
    s.push(2)
    s.clear()
    assert s.size() == 0
    assert s.pop() is None
