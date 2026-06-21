import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from greetings import GreetingService


def test_reuses_same_user_and_locale():
    service = GreetingService({"en": "Hello {user}"})
    assert service.greeting_for("ada", "en") == "Hello ada"
    service.templates["en"] = "Changed {user}"
    assert service.greeting_for("ada", "en") == "Hello ada"


def test_cache_key_includes_locale():
    service = GreetingService({"en": "Hello {user}", "es": "Hola {user}"})
    assert service.greeting_for("ada", "en") == "Hello ada"
    assert service.greeting_for("ada", "es") == "Hola ada"
