from rb_errata import config, doctor
from rb_errata.doctor import Status


def test_unreachable_database_is_a_fail_not_a_crash() -> None:
    # Port 1 on localhost: nothing listens there, so the connection is refused.
    s = config.load({"RB_DATABASE_URL": "postgresql://x:x@127.0.0.1:1/x"})
    check = doctor.check_database(s)
    assert check.status is Status.FAIL
    assert "unreachable" in check.detail
