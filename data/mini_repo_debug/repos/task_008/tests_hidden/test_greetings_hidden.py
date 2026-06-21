import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from greetings import GreetingService


def test_two_users_and_locales_do_not_collide():
    service = GreetingService({"en": "Hello {user}", "fr": "Salut {user}"})
    assert service.greeting_for("ada", "fr") == "Salut ada"
    assert service.greeting_for("grace", "en") == "Hello grace"
    assert service.greeting_for("ada", "en") == "Hello ada"
