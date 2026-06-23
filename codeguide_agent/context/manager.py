from __future__ import annotations

from codeguide_agent.context.budget import apply_budget, estimate_tokens
from codeguide_agent.context.compaction import compact_run_test
from codeguide_agent.context.schemas import ContextBudget, ContextItem, ContextPack, ItemRole


class ContextManager:
    def __init__(self, budget: ContextBudget | None = None) -> None:
        self.budget = budget or ContextBudget()

    def build_pack(
        self,
        issue: str = "",
        repo_map: str = "",
        files: dict[str, str] | None = None,
        test_summary: str = "",
        tool_traces: list[str] | None = None,
        history_rag: list[dict[str, str]] | None = None,
    ) -> ContextPack:
        pack = ContextPack(items=[], budget=self.budget)

        if issue:
            pack.items.append(ContextItem(role=ItemRole.ISSUE, content=issue, token_estimate=estimate_tokens(issue)))

        if repo_map:
            pack.items.append(ContextItem(role=ItemRole.REPO_MAP, content=repo_map, token_estimate=estimate_tokens(repo_map)))

        for path, content in (files or {}).items():
            item = ContextItem(
                role=ItemRole.RETRIEVED_FILE,
                content=f"# {path}\n```\n{content}\n```",
                token_estimate=estimate_tokens(content),
                meta={"file_path": path},
            )
            pack.items.append(item)

        if test_summary:
            ts_item = ContextItem(role=ItemRole.TEST_SUMMARY, content=test_summary, token_estimate=estimate_tokens(test_summary))
            ts_item = compact_run_test(ts_item)
            pack.items.append(ts_item)

        for i, trace in enumerate(tool_traces or []):
            pack.items.append(
                ContextItem(role=ItemRole.TOOL_TRACE, content=trace, token_estimate=estimate_tokens(trace), meta={"trace_index": i})
            )

        for rag_item in history_rag or []:
            pack.items.append(
                ContextItem(
                    role=ItemRole.HISTORY_RAG,
                    content=rag_item.get("retrieval_text", ""),
                    token_estimate=estimate_tokens(rag_item.get("retrieval_text", "")),
                    meta=rag_item,
                )
            )

        pack = apply_budget(pack)
        return pack
