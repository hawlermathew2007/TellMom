from schemas.grooming import GroomingAnalysis
from schemas.flags import FlaggedConversation

class ExplanationCache:
    def __init__(self) -> None:
        self._entries: dict[tuple[str, str], GroomingAnalysis] = {}

    def get(self, key: tuple[str, str]) -> GroomingAnalysis | None:
        return self._entries.get(key)

    def set(self, key: tuple[str, str], analysis: GroomingAnalysis) -> None:
        self._entries[key] = analysis


explanation_cache = ExplanationCache()
flag_store: dict[str, FlaggedConversation] = {}
