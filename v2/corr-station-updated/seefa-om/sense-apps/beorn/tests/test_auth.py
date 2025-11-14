import pytest

from beorn_app.common.auth import get_creds, hash_dict, unhash_dict


@pytest.mark.unittest
def test_auth_hash():
    """Are the hashing functions working as expected?
    Don't test against actual plain text creds.."""
    plain_dict = {"username": "my_username", "password": "my_password"}
    hashed = hash_dict(plain_dict).decode("utf-8")  # decode goes from bytes -> str
    assert unhash_dict(hashed) == plain_dict


@pytest.mark.unittest
def test_auth_interface():
    """Is the interface function working as expected?
    Do not spell out plain text creds here"""
    ret = get_creds("sense")
    assert "password" in ret
