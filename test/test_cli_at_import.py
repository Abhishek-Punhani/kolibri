"""
Tests for `kolibri.utils.cli` module.
These tests deliberately omit `@pytest.mark.django_db` from the tests,
so that any attempt to access the Django database during the running
of these cli methods will result in an error and test failure.
"""
from mock import patch


@patch("sqlalchemy.create_engine")
def test_status_no_db_access(create_engine_mock):
    """
    Tests that status does not try to access the database
    """
    try:
        from kolibri.utils import cli

        cli.status.callback()
    except SystemExit:
        pass
    create_engine_mock.assert_not_called()


@patch("sqlalchemy.create_engine")
def test_stop_no_db_access(create_engine_mock):
    """
    Tests that status does not try to access the database
    """
    try:
        from kolibri.utils import cli

        cli.stop.callback()
    except SystemExit:
        pass
    create_engine_mock.assert_not_called()


@patch("kolibri.utils.conf.OPTIONS")
def test_import_no_options_evaluation(options_mock):
    from kolibri.utils import cli  # noqa F401

    options_mock.__getitem__.assert_not_called()
