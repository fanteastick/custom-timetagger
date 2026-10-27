"""Tests for the custom routing in __main__.py: the app is served both at the
root and under the /timetagger/ prefix.
"""

import sys

from asgineer.testutils import MockTestServer
from _common import run_tests


async def mock_app_asset_handler(request, path):
    return 200, {}, "app:" + path


async def mock_web_asset_handler(request, path):
    return 200, {}, "web:" + path


async def mock_api_handler(request, path):
    return 200, {}, "api:" + path


def get_main_handler():
    """Get the real main_handler, with mocked asset and API handlers."""
    sys.modules.pop("timetagger.__main__", None)
    import timetagger.__main__ as main_module

    main_module.app_asset_handler = mock_app_asset_handler
    main_module.web_asset_handler = mock_web_asset_handler
    main_module.api_handler = mock_api_handler
    return main_module.main_handler


def test_routing_with_and_without_prefix():
    main_handler = get_main_handler()

    with MockTestServer(main_handler) as p:
        for prefix in ("", "/timetagger"):
            r = p.get(prefix + "/")
            assert r.status == 200
            assert r.body.decode() == "web:"

            r = p.get(prefix + "/status")
            assert r.status == 200
            assert r.body.decode() == "ok"

            r = p.get(prefix + "/app/")
            assert r.body.decode() == "app:"

            r = p.get(prefix + "/app/demo")
            assert r.body.decode() == "app:demo"

            r = p.get(prefix + "/api/v2/records")
            assert r.body.decode() == "api:records"

            r = p.get(prefix + "/login")
            assert r.body.decode() == "web:login"


def test_routing_redirects_prefix_without_slash():
    main_handler = get_main_handler()

    with MockTestServer(main_handler) as p:
        r = p.get("/timetagger")
        assert r.status == 307
        assert r.headers["location"] == "/timetagger/"

        # Paths that merely start with the prefix are not stripped
        r = p.get("/timetaggerfoo")
        assert r.body.decode() == "web:timetaggerfoo"


if __name__ == "__main__":
    run_tests(globals())
