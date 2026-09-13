# hypr-use

An experimental Codex-compatible computer-use MCP server for Hyprland, with research and recorded background-use benchmarks.

The [unified MCP server](mcp/unified/README.md) exposes `js`, `js_reset` and `turn_ended`, with the inspected OpenAI native-app `cua` methods implemented over Hypr-Agent-Portal. The [API declarations and provenance](research/2026-09-12/unified-api.md) describe the September 11 app bundle used as the reference. Browser-provider methods, launching apps and rich paste are not implemented.

Live testing uses a locally built Hyprland 0.56.2 plugin, GTK fixtures, Zen and LibreOffice Calc. [Benchmark recordings](testing/unified-benchmark/) include separate GPT-6 Astra CLI processes, compositor focus monitoring, exact tool calls, screenshots and nested timings. See [the independent performance review](testing/unified-benchmark/performance-review.md) and [current findings](testing/unified-benchmark/findings.md).

Current scope: background operation while the user works, MCP for Codex only, and no constraint on Hyprland version. See [SCOPE.md](SCOPE.md) for requirements and evaluation criteria.

The original feasibility reports compare Hypr-Agent-Portal 0.4.0 with the smaller Gabriel-Kahen background plugin. They predate the implementation and live tests above.

[Local Hyprnav comparison](HYPRNAV-COMPARISON.md) explains the C++ plugin / Rust daemon split and how it could inform hypr-use.

- [Codex implementation and model expectations](reports/codex-computer-use.html)
- [Hyprland feasibility and limits](reports/hyprland-feasibility.html)

Initial research date: 6 September 2026. Reports distinguish official documentation, public reverse-engineering observations, source inspection and design proposals.

Rebuild both standalone HTML files with `python build_reports.py`. `sources.json` records the inspected upstream commits.

An independent upstream Git clone lives at `vendor/hypr-agent-portal/`, with its history and origin preserved. The modified local implementation lives at `vendor/hypr-agent-portal-0.56.2/`. See [vendor/README.md](vendor/README.md).

Published reports:

- [Codex implementation](https://artifacts-33e667f674b8cc14518350eea9255a5d.anoromi.com/hypr-use-codex-research/)
- [Hyprland feasibility](https://artifacts-33e667f674b8cc14518350eea9255a5d.anoromi.com/hypr-use-hyprland-research/)

Initial report validation checked local HTML anchors and links, protected artifact routes, and desktop/mobile layout. Current live backend evidence is recorded separately in the benchmark directory.

The initial background-use reassessment checked upstream commits, releases and CI in `maintenance-evidence.json`. Its four offline Portal checks are in `headless-checks.json`; those checks predate native plugin testing.
