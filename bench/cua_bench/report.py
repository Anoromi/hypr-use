from __future__ import annotations

import html, json, shutil
from collections import defaultdict
from pathlib import Path

LABEL = {"scripted": "Scripted baseline", "agentic": "Agentic (Codex)", "unknown": "Unclassified legacy"}


def mode(row: dict) -> str:
    value = row.get("mode")
    return value if value in {"scripted", "agentic"} else "unknown"


def render(run_dir: Path, output: Path, baseline_path: Path | None = None) -> Path:
    paths = sorted(p for p in run_dir.rglob("result.json") if not p.is_relative_to(output))
    entries = [(json.loads(p.read_text()), p) for p in paths]
    rows = [r for r, _ in entries]
    output.mkdir(parents=True, exist_ok=True)
    summaries = []
    for p in run_dir.rglob("summary.json"):
        try: summaries.append(json.loads(p.read_text()))
        except json.JSONDecodeError: pass
    groups = defaultdict(list)
    for row in rows: groups[mode(row)].append(row)
    metrics = []
    for kind in ("scripted", "agentic"):
        group = groups.get(kind, [])
        if not group: continue
        model = next((s.get("model") for s in summaries if s.get("mode") in {kind, "both"} and s.get("model")), None)
        name = LABEL[kind] + (f" · {html.escape(str(model))}" if model and kind == "agentic" else "")
        step_values = [int(row["steps"]) for row in group if row.get("steps") is not None]
        step_summary = f" · {sum(step_values)/len(step_values):.1f} mean steps" if step_values else ""
        metrics.append(f"<div><strong>{name}</strong><span>{sum(bool(r.get('passed')) for r in group)}/{len(group)} completed{step_summary}</span></div>")
    tiers = defaultdict(list)
    for row in rows: tiers[(mode(row), str(row.get("tier", "real")))].append(row)
    tier_html = "".join(f"<tr><td>{LABEL[k]}</td><td>{html.escape(t)}</td><td>{sum(bool(r.get('passed')) for r in g)}/{len(g)}</td><td>{sum(int(r['steps']) for r in g if r.get('steps') is not None)/sum(r.get('steps') is not None for r in g):.1f}</td></tr>" for (k,t),g in sorted(tiers.items()) if any(r.get("steps") is not None for r in g))

    paired = defaultdict(lambda: defaultdict(list))
    for row, path in entries: paired[str(row.get("id", "task"))][mode(row)].append((row, path))
    task_html = []
    for task_id, variants in sorted(paired.items()):
        tier = next(iter(next(iter(variants.values()))))[0].get("tier", "real"); cells = []
        for kind in (("scripted", "agentic", "unknown") if "unknown" in variants else ("scripted", "agentic")):
            if kind not in variants: cells.append("<td class=empty>not run</td>"); continue
            runs = []
            for index, (row, result_path) in enumerate(variants[kind], 1):
                relkey = result_path.parent.relative_to(run_dir).as_posix().replace("/", "-")
                links = []; evidence = output / "evidence" / kind / relkey
                names = {"result.json", "transcript.jsonl", "tool-evidence.json", "t6-evidence.json", "state.json", "stderr.txt", "wire.jsonl", "prompt.txt"}
                names.update(path.name for pattern in ("wire-*.jsonl", "final*.txt") for path in result_path.parent.glob(pattern))
                for name in sorted(names):
                    source = result_path.parent / name
                    if source.is_file():
                        evidence.mkdir(parents=True, exist_ok=True); shutil.copy2(source, evidence / name)
                        links.append(f"<a href='evidence/{kind}/{html.escape(relkey)}/{html.escape(name)}'>{html.escape(name)}</a>")
                recording = row.get("recording") or str(result_path.parent / "desktop.mp4")
                if Path(recording).is_file():
                    target = output / "media" / kind / f"{relkey}.mp4"; target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(recording, target)
                    links.append(f"<a href='media/{kind}/{html.escape(relkey)}.mp4'>video</a>")
                detail = html.escape(str(row.get("error") or row.get("detail") or "")[:140])
                step_text = str(row.get("steps")) if row.get("steps") is not None else "unavailable"
                runs.append(f"<strong>{'complete' if row.get('passed') else 'incomplete'}</strong><small>run {index} · {step_text} steps</small><small>{html.escape(str(row.get('failure_class') or ''))} {detail}</small><small>{' · '.join(links)}</small>")
            cells.append(f"<td>{'<hr>'.join(runs)}</td>")
        task_html.append(f"<tr><th>{html.escape(task_id)}<small>{html.escape(str(tier))}</small></th>{''.join(cells)}</tr>")

    comparison = ""
    candidate = baseline_path or run_dir / "baseline.json"
    if candidate.exists() and len(groups) == 1 and "unknown" not in groups:
        old_data = json.loads(candidate.read_text()); old_rows = old_data.get("results", []) if isinstance(old_data, dict) else old_data
        current_mode = next(iter(groups)); old = {r["id"]: r for r in old_rows if r.get("mode") == current_mode}
        deltas = [float(bool(r.get("passed")))-float(bool(old[r["id"]].get("passed"))) for r in rows if r.get("id") in old]
        if deltas: comparison = f" Same-mode completion delta: {sum(deltas)/len(deltas):+.1%} across {len(deltas)} tasks."
    (output / "results.json").write_text(json.dumps(rows, indent=2)+"\n")
    payload = json.dumps(rows, separators=(",", ":")).replace("<", "\\u003c")
    legacy_head = "<th>Unclassified legacy</th>" if "unknown" in groups else ""
    (output / "index.html").write_text(f"""<!doctype html><html lang=en><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>CUA benchmark report</title><style>:root{{--bg:#0d1117;--panel:#161b22;--line:#30363d;--text:#e6edf3;--muted:#8b949e;--link:#58a6ff}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font:14px/1.5 system-ui,sans-serif}}main{{max-width:1380px;margin:auto;padding:32px 24px}}h1{{font-size:24px;margin:0 0 6px}}h2{{font-size:16px;margin:28px 0 8px}}p,small,.empty{{color:var(--muted)}}.summary{{display:flex;gap:1px;background:var(--line);border:1px solid var(--line)}}.summary div{{display:flex;flex:1;flex-direction:column;background:var(--panel);padding:14px 16px}}table{{width:100%;border-collapse:collapse;border:1px solid var(--line)}}th,td{{padding:10px 12px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}}thead th{{background:var(--panel)}}tbody th{{width:18%}}small{{display:block;margin-top:3px}}hr{{border:0;border-top:1px solid var(--line);margin:10px 0}}a{{color:var(--link)}}@media(max-width:720px){{main{{padding:20px 10px}}.summary{{display:block}}table{{font-size:12px}}th,td{{padding:7px}}}}</style><main><h1>CUA benchmark report</h1><p>Scripted runs are deterministic baselines. Agentic runs measure Codex. They share tasks and grading; completion and step counts stay separate by mode.{comparison}</p><div class=summary>{''.join(metrics)}</div><h2>Results by mode and tier</h2><table><thead><tr><th>Mode</th><th>Tier</th><th>Completion</th><th>Mean steps</th></tr></thead><tbody>{tier_html}</tbody></table><h2>Paired task evidence</h2><table><thead><tr><th>Task</th><th>Scripted baseline</th><th>Agentic (Codex)</th>{legacy_head}</tr></thead><tbody>{''.join(task_html)}</tbody></table><script type=application/json id=results>{payload}</script></main></html>""")
    return output / "index.html"
