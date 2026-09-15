"""Architectural boundaries (ADR-011): one shared data platform, separate domains.

Shared platform code must not import Trading or Investing logic; Trading and
Investing must not import each other. Ownership is declared here by module
prefix (longest prefix wins) so the existing layered layout does not need a
restructuring to be enforced. Every domain/application module must have an owner.
"""

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
PACKAGE = "arcturus_api"

OWNERSHIP: dict[str, tuple[str, ...]] = {
    "shared": (
        "arcturus_api.domain.data",
        "arcturus_api.domain.identity",
        "arcturus_api.domain.quality",
        "arcturus_api.domain.market",
        "arcturus_api.domain.watchlist",
        "arcturus_api.application.cache",
        "arcturus_api.application.identity",
        "arcturus_api.application.quality",
        "arcturus_api.application.market.service",
        "arcturus_api.application.market.directory_service",
        "arcturus_api.application.watchlist",
    ),
    "trading": (
        "arcturus_api.domain.indicators",
        "arcturus_api.domain.strategy",
        "arcturus_api.domain.backtest",
        "arcturus_api.domain.research",  # backtest experiment registry
        "arcturus_api.domain.market.regime",  # gates strategy confidence
        "arcturus_api.application.strategy",
        "arcturus_api.application.market.indicator_service",
        "arcturus_api.application.market.regime_service",
    ),
    "investing": (
        "arcturus_api.domain.investing",
        "arcturus_api.application.investing",
    ),
    # HTTP layer, composition root, adapters and config wire domains together
    "unowned": (
        "arcturus_api.api",
        "arcturus_api.infrastructure",
        "arcturus_api.core",
        "arcturus_api.main",
    ),
}

FORBIDDEN: dict[str, set[str]] = {
    "shared": {"trading", "investing"},
    "trading": {"investing"},
    "investing": {"trading"},
}


def owner(module: str) -> str | None:
    best: tuple[int, str] | None = None
    for domain, prefixes in OWNERSHIP.items():
        for prefix in prefixes:
            matches = module == prefix or module.startswith(f"{prefix}.")
            if matches and (best is None or len(prefix) > best[0]):
                best = (len(prefix), domain)
    return best[1] if best else None


def imported_modules(source: str) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.add(node.module)
            # `from package import submodule` imports the submodule too
            found.update(f"{node.module}.{alias.name}" for alias in node.names)
    return {name for name in found if name.startswith(PACKAGE)}


def module_files() -> list[tuple[str, Path]]:
    modules: list[tuple[str, Path]] = []
    for path in sorted((SRC / PACKAGE).rglob("*.py")):
        parts = path.relative_to(SRC).with_suffix("").parts
        if parts[-1] == "__init__":
            continue
        modules.append((".".join(parts), path))
    return modules


class TestBoundaries:
    def test_every_domain_and_application_module_has_an_owner(self) -> None:
        unowned = [
            module
            for module, _ in module_files()
            if module.startswith(("arcturus_api.domain.", "arcturus_api.application."))
            and owner(module) is None
        ]
        assert unowned == []

    def test_no_forbidden_cross_domain_imports(self) -> None:
        violations: list[str] = []
        for module, path in module_files():
            source_domain = owner(module)
            if source_domain not in FORBIDDEN:
                continue
            for imported in imported_modules(path.read_text(encoding="utf-8")):
                target_domain = owner(imported)
                if target_domain in FORBIDDEN[source_domain]:
                    violations.append(f"{module} ({source_domain}) -> {imported} ({target_domain})")
        assert violations == []

    def test_checker_detects_a_violation(self) -> None:
        leaked = imported_modules("from arcturus_api.domain.strategy.plugins import ALL_STRATEGIES")
        assert {owner(name) for name in leaked} == {"trading"}
        assert "trading" in FORBIDDEN[owner("arcturus_api.domain.quality.candles") or ""]
        assert owner("arcturus_api.domain.market.regime") == "trading"
        assert owner("arcturus_api.domain.market.models") == "shared"
        assert owner("arcturus_api.domain.investing.valuation") == "investing"
