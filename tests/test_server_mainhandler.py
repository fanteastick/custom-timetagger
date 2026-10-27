"""Tests for main handler routing with path_prefix and app_redirect configuration.

Note: this fork also serves the app at the domain root, in addition to
under path_prefix. The tests below are adapted from upstream accordingly.
"""

import sys

from asgineer.testutils import MockTestServer
from _common import run_tests

from timetagger import config
from timetagger._config import set_config


# Mock asset handlers to avoid compilation overhead
async def mock_app_asset_handler(request, path):
    """Mock app asset handler that returns identifiable response."""
    return 200, {}, "app"


async def mock_web_asset_handler(request, path):
    """Mock web asset handler that returns identifiable response.
    Like the real one, it gives a 404 for unknown paths.
    """
    if path:
        return 404, {}, f"not found: {path}"
    return 200, {}, "web"


async def mock_api_handler(request, path):
    """Mock API handler that returns identifiable response."""
    if not path and request.method == "GET":
        return 200, {}, "api"
    return 200, {}, "api"


def get_main_handler():
    """Get the real main_handler with mocked asset handlers.

    This ensures we test the actual routing logic from __main__.py
    while avoiding the overhead of compiling assets.

    Returns:
        The main_handler function from timetagger.__main__.
    """
    # Remove cached module to force reimport with current config
    if "timetagger.__main__" in sys.modules:
        del sys.modules["timetagger.__main__"]

    # Import the module
    import timetagger.__main__ as main_module

    # Replace the asset handlers with mocks
    main_module.app_asset_handler = mock_app_asset_handler
    main_module.web_asset_handler = mock_web_asset_handler
    main_module.api_handler = mock_api_handler

    return main_module.main_handler


def test_path_prefix_default():
    """Test routing with default path_prefix (/timetagger/)."""
    set_config([], {})
    assert config.path_prefix == "/timetagger/"
    assert config.app_redirect is False

    main_handler = get_main_handler()

    with MockTestServer(main_handler) as p:
        # Root serves the landing page too (custom)
        r = p.get("/")
        assert r.status == 200
        assert r.body.decode() == "web"

        # The prefix without trailing slash redirects (custom)
        r = p.get("/timetagger")
        assert r.status == 307
        assert r.headers["location"] == "/timetagger/"

        # The app is also served at the root (custom)
        r = p.get("/app/")
        assert r.status == 200
        assert r.body.decode() == "app"
        r = p.get("/status")
        assert r.body.decode() == "ok"

        # Status endpoint
        r = p.get("/timetagger/status")
        assert r.status == 200
        assert r.body.decode() == "ok"

        # Web assets (landing page)
        r = p.get("/timetagger/")
        assert r.status == 200
        assert r.body.decode() == "web"

        # App route
        r = p.get("/timetagger/app/")
        assert r.status == 200
        assert r.body.decode() == "app"

        # API root
        r = p.get("/timetagger/api/v2/")
        assert r.status == 200
        assert r.body.decode() == "api"

        # Unknown paths should 404
        r = p.get("/other/path")
        assert r.status == 404
        r = p.get("/timetagger/other/path")
        assert r.status == 404


def test_path_prefix_custom():
    """Test routing with custom path_prefix."""
    set_config(["--path_prefix=/custom/path/"], {})
    assert config.path_prefix == "/custom/path/"

    main_handler = get_main_handler()

    with MockTestServer(main_handler) as p:
        # Root serves the landing page too (custom)
        r = p.get("/")
        assert r.status == 200
        assert r.body.decode() == "web"

        # Status endpoint at custom prefix
        r = p.get("/custom/path/status")
        assert r.status == 200
        assert r.body.decode() == "ok"

        # Web assets at custom prefix
        r = p.get("/custom/path/")
        assert r.status == 200
        assert r.body.decode() == "web"

        # App route at custom prefix
        r = p.get("/custom/path/app/")
        assert r.status == 200
        assert r.body.decode() == "app"

        # API at custom prefix
        r = p.get("/custom/path/api/v2/")
        assert r.status == 200
        assert r.body.decode() == "api"

        # Old path should not work
        r = p.get("/timetagger/")
        assert r.status == 404


def test_path_prefix_root():
    """Test routing with path_prefix set to root (/)."""
    set_config(["--path_prefix=/"], {})
    assert config.path_prefix == "/"

    main_handler = get_main_handler()

    with MockTestServer(main_handler) as p:
        # Root path serves the landing page (upstream's known 500 does not apply here)
        r = p.get("/")
        assert r.status == 200
        assert r.body.decode() == "web"

        # App route at root
        r = p.get("/status")
        assert r.status == 200
        assert r.body.decode() == "ok"

        # App route at root
        r = p.get("/app/")
        assert r.status == 200
        assert r.body.decode() == "app"

        # API at root
        r = p.get("/api/v2/")
        assert r.status == 200
        assert r.body.decode() == "api"


def test_app_redirect_default_prefix():
    """Test app_redirect with default path_prefix."""
    set_config(["--app_redirect=true"], {})
    assert config.path_prefix == "/timetagger/"
    assert config.app_redirect is True

    main_handler = get_main_handler()

    with MockTestServer(main_handler) as p:
        # Root should redirect to app when app_redirect is true
        r = p.get("/")
        assert r.status == 307
        assert r.headers["location"] == "/timetagger/app/"

        # App should be accessible
        r = p.get("/timetagger/app/")
        assert r.status == 200
        assert r.body.decode() == "app"

        # Landing page should still be accessible
        r = p.get("/timetagger/")
        assert r.status == 200
        assert r.body.decode() == "web"


def test_app_redirect_custom_prefix():
    """Test app_redirect with custom path_prefix."""
    set_config(["--app_redirect=true", "--path_prefix=/custom/"], {})
    assert config.path_prefix == "/custom/"
    assert config.app_redirect is True

    main_handler = get_main_handler()

    with MockTestServer(main_handler) as p:
        # Root should redirect to custom app path
        r = p.get("/")
        assert r.status == 307
        assert r.headers["location"] == "/custom/app/"

        # App should be accessible at custom path
        r = p.get("/custom/app/")
        assert r.status == 200
        assert r.body.decode() == "app"


def test_app_redirect_root_prefix():
    """Test app_redirect with path_prefix at root (/)."""
    set_config(["--app_redirect=true", "--path_prefix=/"], {})
    assert config.path_prefix == "/"
    assert config.app_redirect is True

    main_handler = get_main_handler()

    with MockTestServer(main_handler) as p:
        # Root should redirect to /app/
        r = p.get("/")
        assert r.status == 307
        assert r.headers["location"] == "/app/"

        # App should be accessible
        r = p.get("/app/")
        assert r.status == 200
        assert r.body.decode() == "app"


def test_path_prefix_normalization():
    """Test that path_prefix is normalized correctly."""
    # Test various input formats
    test_cases = [
        ("custom", "/custom/"),
        ("/custom", "/custom/"),
        ("custom/", "/custom/"),
        ("/custom/", "/custom/"),
        ("custom/path", "/custom/path/"),
        ("/custom/path/", "/custom/path/"),
        ("/", "/"),
    ]

    for input_val, expected in test_cases:
        set_config([f"--path_prefix={input_val}"], {})
        assert (
            config.path_prefix == expected
        ), f"Input '{input_val}' should normalize to '{expected}', got '{config.path_prefix}'"


def test_combined_features():
    """Test path_prefix and app_redirect working together."""
    set_config(["--path_prefix=/myapp/", "--app_redirect=true"], {})
    assert config.path_prefix == "/myapp/"
    assert config.app_redirect is True

    main_handler = get_main_handler()

    with MockTestServer(main_handler) as p:
        # Root redirects to app at custom prefix
        r = p.get("/")
        assert r.status == 307
        assert r.headers["location"] == "/myapp/app/"

        # All endpoints work at custom prefix
        r = p.get("/myapp/app/")
        assert r.status == 200
        assert r.body.decode() == "app"

        r = p.get("/myapp/api/v2/")
        assert r.status == 200
        assert r.body.decode() == "api"

        r = p.get("/myapp/")
        assert r.status == 200
        assert r.body.decode() == "web"

        r = p.get("/myapp/status")
        assert r.status == 200
        assert r.body.decode() == "ok"

        # Other paths should 404
        r = p.get("/other/")
        assert r.status == 404


if __name__ == "__main__":
    run_tests(globals())
