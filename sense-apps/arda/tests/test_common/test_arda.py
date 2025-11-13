import pytest
from pytest import raises


@pytest.mark.unittest
def test_exception():
    """Standard, clean format for exception testing"""

    def raise_error():
        raise KeyError("Key not found")

    # Begin by trying to catch *any* exception to handle no-exception cases
    with raises(Exception) as excinfo:  # don't test for error type here
        raise_error()  # if no exception, will fail with "DID NOT RAISE <class Exception>"

    # Now be specific about the Exception.. the traceback is your oyster
    assert isinstance(excinfo.type(), KeyError)
    assert "not found" in str(excinfo.value)
    # Did the exception happen on line number lucky 14??
    assert excinfo.tb.tb_lineno == 14
