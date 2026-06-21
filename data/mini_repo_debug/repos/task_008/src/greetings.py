from __future__ import annotations


class GreetingService:
    def __init__(self, templates: dict[str, str]):
        self.templates = templates
        self.cache: dict[str, str] = {}

    def greeting_for(self, user_id: str, locale: str) -> str:
        key = user_id
        if key not in self.cache:
            self.cache[key] = self.templates[locale].format(user=user_id)
        return self.cache[key]
