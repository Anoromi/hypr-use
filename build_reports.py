"""Build two standalone research reports using only the Python standard library."""
from pathlib import Path
import html
import json

ROOT = Path(__file__).parent
REPOS = {r['name']: r for r in json.loads((ROOT / 'sources.json').read_text())['repositories']}

def repo(name, path='README.md', label=None):
    r = REPOS[name]
    url = r['repository'].removesuffix('.git') + '/blob/' + r['commit'] + '/' + path
    return link(url, label or ('Hypr-Agent-Portal' if name == 'Hypr-Agent-Protal' else name))

def link(url, label):
    return f'<a href="{html.escape(url, quote=True)}">{html.escape(label)}</a>'

def p(text): return '<p>' + text + '</p>'
def table(headers, rows):
    return '<div class="table-scroll" tabindex="0" role="region" aria-label="Comparison table"><table><thead><tr>' + ''.join('<th scope="col">'+h+'</th>' for h in headers) + '</tr></thead><tbody>' + ''.join('<tr>'+''.join('<td>'+v+'</td>' for v in row)+'</tr>' for row in rows) + '</tbody></table></div>'
def ul(items): return '<ul>' + ''.join('<li>'+i+'</li>' for i in items) + '</ul>'
def pre(text): return '<pre><code>' + html.escape(text) + '</code></pre>'

official = link('https://learn.chatgpt.com/docs/computer-use', 'Official desktop documentation')
api = link('https://developers.openai.com/api/docs/guides/tools-computer-use', 'Responses API computer-use guide')
revdir = 'docs/references/codex-computer-use-reverse-engineering/'
baseline = repo('open-codex-computer-use', revdir+'baseline-architecture.md', 'Observed macOS architecture and tool schemas')
runtime = repo('open-codex-computer-use', revdir+'runtime-and-host-dependencies.md', 'Runtime and host-dependency investigation')
ipc = repo('open-codex-computer-use', revdir+'internal-ipc-surface.md', 'Internal IPC investigation')
rendering = repo('open-codex-computer-use', revdir+'state-rendering-1.0.770.md', 'State-rendering investigation, version 1.0.770')
hyprctl = link('https://wiki.hypr.land/configuring/core/advanced-configuration/using-hyprctl/', 'Hyprctl documentation')
atspi = link('https://docs.gtk.org/atspi2/class.Accessible.html', 'AT-SPI Accessible API')
pointer = link('https://wayland.app/protocols/wlr-virtual-pointer-unstable-v1', 'Virtual-pointer protocol')
capture = link('https://wayland.app/protocols/ext-image-copy-capture-v1', 'Image-copy-capture protocol')

one = []
one.append(('finding', 'What Linux needs to match',
    p('A Hyprland implementation is feasible without reproducing OpenAI\'s private desktop service. The useful compatibility target is the model-facing contract: identify an app, return a fresh image and useful UI structure, execute precisely defined actions, then report what changed.') +
    p('There are two distinct interfaces to study. Codex\'s desktop plugin exposes app-oriented MCP tools. The public Responses API supports a screenshot/action loop and code-driven computer use. They overlap in capability, but their schemas and host integration differ. Matching one does not make a drop-in replacement for the other.') +
    p('Evidence labels in this report: <strong>documented</strong> means official product or API documentation; <strong>observed by a researcher</strong> means a public reconstruction or recorded experiment; <strong>proposal</strong> means a design recommendation for hypr-use. Public code was inspected at pinned commits. No macOS or Windows binary was executed or independently disassembled for this report.')))

one.append(('platforms', 'macOS and Windows behave differently',
    table(['Platform', 'Documented behavior', 'Consequence for hypr-use'], [
        ['macOS', 'Screen Recording and Accessibility permissions. Scoped background app use; optional locked use through an Apple authorization plugin.', 'Background control is an additional engineering target. A screenshot plus global mouse injection does not reproduce it.'],
        ['Windows', 'Foreground control of the active desktop. The target must remain visible; normal operation requires an unlocked session.', 'A Hyprland implementation that temporarily owns the desktop can already offer comparable foreground behavior.'],
        ['Linux', 'The computer-use page lists macOS and Windows. It does not document first-party Linux computer use.', 'Separate lack of an official plugin from lack of model capability. An MCP implementation is an independent route.']]) +
    p(official + '. Availability also depends on region and account. This is about the computer-use feature, not whether a Linux Codex client exists.')))

one.append(('mac', 'The reconstructed macOS implementation',
    p('The iFurySt investigation records a signed <code>SkyComputerUseClient</code> and a separate <code>SkyComputerUseService</code>. Codex launches the client with <code>mcp</code> over stdio; a <code>turn-ended</code> command participates in cleanup. The service owns system interaction and app-session state. ' + baseline + '.') +
    pre('Codex agent\n  → MCP tools over stdio\n  → SkyComputerUseClient\n  → authenticated local requests\n  → SkyComputerUseService\n  → accessibility, window capture, input\n\nThe service also connects to Codex host IPC for turn events and integration.') +
    p('Researchers observed Apple Events requests identified as <code>SkCu/SndR</code>, sender-authentication failures, and a service connection to a <code>codex-ipc</code> Unix socket. A signed Codex parent alone did not make every external invocation work. This is evidence of host coupling, not a supported API to reuse on Linux. Earlier notes speculate about XPC; the later runtime observations are stronger evidence. ' + runtime + '.') +
    p('Internal symbols name app-start, app-modify, app-action, skyshot and turn-ended requests. They suggest a common action dispatcher and a composite screenshot/UI-tree observation. They do not establish a complete wire format, a public HTTP endpoint, or a stable external protocol. ' + ipc + '.') +
    table(['Layer', 'Evidence', 'What it supports'], [
        ['UI structure', '<code>AXUIElementCopyAttributeValue</code>, <code>AXUIElementPerformAction</code>, <code>AXUIElementSetAttributeValue</code>', 'Read roles, names, values and available actions; invoke controls or change supported values.'],
        ['Capture', '<code>ScreenCaptureKit</code>, <code>SCScreenshotManager</code>, window-list APIs', 'Target-window images alongside the accessibility tree.'],
        ['State rendering', 'Symbols for pruning empty groups, flattening redundant hierarchy and merging text', 'The model receives a compact representation, rather than an unfiltered accessibility dump. Exact transform order remains unknown.']]) +
    p(rendering + '.') +
    p('The paralym reconstruction reports synthetic-focus classes, event taps and window-routing APIs. Its own fallback stack uses AX actions, process-targeted events and brief real activation with window masking. That implementation is not proof that Codex uses the same fallback order. Its reported Electron offsets and menu-bar flashes also show why "background" is an app-dependent property. ' + repo('codex-computer-use-cli') + '.')))

one.append(('contract', 'The recovered tool contract',
    p('These nine tools come from the researcher\'s recorded official macOS interface, primarily April 2026 builds. Treat them as a dated compatibility profile, not a guarantee about every current desktop build. ' + baseline + '.') +
    table(['Tool', 'Inputs and semantics to preserve'], [
        ['<code>list_apps</code>', 'No inputs. Discover running/recent apps with identity and usage metadata.'],
        ['<code>get_app_state</code>', '<code>app</code>. Establish/reuse app session; return key-window screenshot, indexed accessibility tree and app identity.'],
        ['<code>click</code>', '<code>app</code>; string <code>element_index</code> or screenshot-pixel <code>x,y</code>; optional click count and mouse button.'],
        ['<code>perform_secondary_action</code>', '<code>app, element_index, action</code>. Action must be one actually exposed by that element.'],
        ['<code>scroll</code>', '<code>app, element_index, direction</code>, optional fractional <code>pages</code>. Element-scoped.'],
        ['<code>drag</code>', '<code>app, from_x, from_y, to_x, to_y</code>, in screenshot pixels.'],
        ['<code>type_text</code>', '<code>app, text</code>. Literal text, distinct from shortcuts.'],
        ['<code>press_key</code>', '<code>app, key</code>. Xdotool-style key spelling; OS-specific modifier meaning.'],
        ['<code>set_value</code>', '<code>app, element_index, value</code>. Write a supported accessibility value.']]) +
    p('Proposal: keep these familiar names in a compatibility adapter, but use Linux app IDs and window handles internally. Scope element references to a snapshot; reject stale IDs. Preserve screenshot-to-window transforms. Return an image content block the client can actually deliver to the model, with text metadata beside it. Never return a base64 string as if it were a visible image.') +
    p('Do not invent macOS semantics on Linux. For example, <code>super+c</code> describes Command-C in a Mac-oriented workflow, while Super usually controls Hyprland. Teach the model Linux shortcuts, normally Control-C for copying in GUI apps. A missing semantic action should return unsupported or select an explicit coordinate fallback, not silently pretend it succeeded.') +
    p('The open implementation adds options such as <code>click_method</code> and tree-size limits. Those are extensions, not evidence that the recorded official schema contained them. ' + repo('open-codex-computer-use', 'packages/OpenComputerUseKit/Sources/OpenComputerUseKit/ToolDefinitions.swift', 'Current clone tool definitions') + '.')))

one.append(('windows', 'What is known about Windows internals',
    p('Evidence is thinner than on macOS. A first-hand Codex issue reports a Chrome modal dialog visible through UI Automation but rejected as an input target because it has a different HWND from the selected parent. That supports investigating window ownership and transient dialogs. It does not reveal the full capture or injection backend. ' + link('https://github.com/openai/codex/issues/36603', 'Codex issue #36603') + '.') +
    p('Public Codex source includes platform-specific app-policy configuration. The inspected checkout exposes macOS bundle IDs and Windows AUMID/executable identity structures; it does not provide a complete Windows computer-use executor in the files located by this investigation. ' + repo('codex', 'codex-rs/config/src/computer_use.rs', 'Codex app-policy source') + '.') +
    table(['API or project', 'What it tells us', 'Evidence boundary'], [
        ['Microsoft UI Automation', 'Semantic element trees and control patterns are available to automation clients.', link('https://learn.microsoft.com/en-us/windows/win32/winauto/entry-uiauto-win32', 'Microsoft documentation') + '. An OS capability, not proof of every Codex code path.'],
        ['Win32 <code>SendInput</code>', 'Synthesizes keyboard/mouse input; UIPI restricts injection to equal or lower integrity targets.', link('https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendinput', 'Microsoft documentation') + '. Do not claim Codex uses this without binary/source evidence.'],
        ['iFurySt Windows implementation', 'Uses UI Automation first and window-message fallbacks; attempts background-compatible operations.', repo('open-codex-computer-use', 'apps/OpenComputerUseWindows/main.go', 'Independent Windows implementation') + '. Its behavior differs from official foreground-only product behavior.']]) +
    p('Unresolved: exact official Windows tool schemas, screenshot backend, input APIs and focus-recovery logic for the current build. A follow-up should record tools/list and harmless tool traces on a Windows installation, then compare module imports and window ownership checks. There is no verified private Windows endpoint to build against in this evidence set.')))

one.append(('api', 'The public model interface is another valid target',
    p('The current API guide recommends code execution for GPT-6 Astra and also supports the structured <code>computer</code> tool. A <code>computer_call</code> contains ordered <code>actions</code>; the client executes them and returns a matching <code>computer_call_output</code> with a screenshot. Supported actions include click, double-click, drag, move, scroll, keypress, type, wait and screenshot. ' + api + '.') +
    p('Scope update: implement MCP for Codex only. Responses API material is retained as research background, not an implementation requirement or planned adapter.') +
    p('Coordinates must refer to the image actually supplied. Preserve original image detail where supported, and undo any crop or resize before delivering input. Old <code>computer-use-preview</code> examples are a separate legacy profile, not the current schema. API access and billing are also separate from installing a tool in a signed-in Codex client.')))

one.append(('benchmarks', 'What OSWorld actually proves',
    table(['Benchmark', 'Scope', 'Useful lesson'], [
        ['OSWorld / OSWorld-Verified', 'Original benchmark has 369 tasks. Verified repairs task and evaluation problems.', 'Real Linux desktop tasks already test screenshot and keyboard/mouse control. '+repo('OSWorld')+'.'],
        ['OSWorld 2.0', '108 longer workflows, with binary completion and partial credit. The paper uses a 500-step primary setting.', 'Long tasks expose state tracking and recovery failures hidden by short demos. '+link('https://arxiv.org/abs/2606.29537', 'OSWorld 2.0 paper')+'.']]) +
    p('A particularly relevant result is image handling. OpenAI reports GPT-5.2 at 47.3% and GPT-5.4 at 75.0% on OSWorld-Verified. It also revises GPT-5.3-Codex from 64.7% to 74.0% when original image resolution is preserved. That is direct evidence that observation quality can change results substantially even without changing the named model. These are reported results under the publisher\'s evaluation settings, not expected success rates on your desktop. ' + link('https://openai.com/index/introducing-gpt-5-4/', 'GPT-5.4 release evaluation') + '.') +
    p('OSWorld 2.0 is a different task distribution. In the paper\'s reported setting, the best listed system completes 20.6% with 54.8% partial credit. Do not compare that percentage directly to 75% on Verified, or mistake a partial score for task completion. The figures describe the paper, not a freshly rerun leaderboard. ' + link('https://arxiv.org/abs/2606.29537', 'Paper and evaluation setting') + '.') +
    p('The repositories expose the environment interface, screenshot/accessibility observation routes, action execution and evaluators. The inspected V2 OpenAI adapter translates model requests into a PyAutoGUI action space. That makes it useful adapter code, but does not make PyAutoGUI a native Hyprland input solution. ' + repo('OSWorld', 'desktop_env/server/main.py', 'OSWorld desktop server') + '; ' + repo('OSWorld-V2', 'mm_agents/gpt_response_api.py', 'V2 OpenAI adapter') + '.') +
    p('For reproducibility, V2 currently recommends release <code>osworld-v2-2026.08.08</code>. Its manifest pins code, task hashes, assets, mocked websites and provider images. Task classes and complete assets require gated Hugging Face access; cloning the public repository is insufficient. ' + repo('OSWorld-V2', 'benchmark_releases/osworld-v2-2026.08.08.json', 'Release manifest') + '; ' + repo('OSWorld-V2') + '.') +
    p('Proposal: compare a Codex MCP agent in a controlled desktop environment with matched tasks on Hyprland. Record model version, reasoning settings, image detail, action budget, success, time and retries. The Hyprland run is a ported evaluation and must be labeled separately. Improvements could come from the model, image resolution, tools or task setup; this comparison helps distinguish them.')))

one.append(('decision', 'Recommended compatibility target',
    ul(['Build a Codex MCP adapter around the nine app-oriented operations, with a documented Linux capability profile.',
        'Make fresh observations, coordinate transforms, stale-reference checks and action verification the first milestones.',
        'Require background operation while the user works in another app. Never switch to foreground input as an automatic fallback.',
        'Evaluate through Codex MCP and reproducible desktop fixtures. Hyprland upgrades are acceptable; assess maintenance independently of version numbers.']) +
    p('This is an engineering recommendation based on the sources above. Equal tool names alone do not promise equal model performance or integration with the official plugin\'s approval UI.')))

two = []
two.append(('finding', 'Hyprland is a viable target',
    p('The required first version is a Codex MCP service that works in the background while the user continues working. Prioritize compositor-assisted input, exact window capture and AT-SPI actions. A foreground-only implementation does not meet the project scope.') +
    p('The hard part is reliable background input across toolkits, popups and XWayland. A virtual monitor alone does not create an independent keyboard and mouse. An operation that needs foreground takeover must report that limitation instead of silently taking over.') +
    p('This report includes read-only checks of the current machine and source inspection. It does not claim an end-to-end automation test. No input was injected, apps moved, permissions changed or plugins loaded.')))

two.append(('local', 'Your current session',
    table(['Read-only check', 'Observed result', 'Meaning'], [
        ['System', 'NixOS; Hyprland 0.55.4; Codex CLI 0.153.4', 'Pin dependencies to the installed compositor, especially native plugin headers.'],
        ['Display', '2880 × 1800 pixels, scale 1.6, no rotation', 'Logical desktop is 1800 × 1125. Passing physical screenshot coordinates directly to logical input would miss.'],
        ['Window metadata', '3 native Wayland windows; all expose <code>stableId</code>', 'The session has candidate identifiers for exact toplevel capture. Capture itself was not exercised.'],
        ['Tools', '<code>hyprctl</code>, <code>grim</code>, <code>wl-copy</code>, <code>busctl</code> available', '<code>grim -h</code> advertises <code>-T</code> toplevel capture.'],
        ['Missing from PATH', '<code>wtype</code>, <code>ydotool</code>, <code>wayland-info</code>', 'These command backends are not ready through the current PATH. This does not prove packages are absent.'],
        ['Session services', '<code>org.a11y.Bus</code> and desktop portal present', 'Accessibility and portal entry points exist. App tree coverage and individual portal interfaces remain to be tested.']]) +
    p('Source: local <code>hyprctl version/monitors/clients -j</code>, command discovery, <code>grim -h</code>, and the user D-Bus service list, inspected 6 September 2026. Window titles and contents were excluded from the report.')))

two.append(('capabilities', 'What can be implemented',
    table(['Capability', 'Backend', 'Boundary'], [
        ['Discover/focus/move windows', '<code>hyprctl</code> JSON and dispatchers', 'Use window identity plus process lifetime. Titles and classes are ambiguous and not security identities. '+hyprctl+'.'],
        ['Capture visible output or region', '<code>grim</code>, screencopy or ScreenCast/PipeWire', 'A region crop contains occluding windows. It is not an independent window capture.'],
        ['Capture a background window', '<code>grim -T stableId</code> and toplevel capture support', 'Probe actual frame freshness, inactive workspaces, popups and GPU paths. Do not infer support from a binary flag alone. '+capture+'.'],
        ['Read controls and values', 'AT-SPI on the accessibility bus', 'GTK/Qt/browser coverage varies. Canvas content and some Electron apps need image fallback. '+atspi+'.'],
        ['Invoke or edit controls semantically', 'AT-SPI Action, EditableText and Value', 'Only where the app exposes the interface. Setting a value may bypass keyboard events. Verify the resulting state.'],
        ['General click/scroll/drag', 'Wayland virtual pointer, optionally compositor cursor positioning', 'Normal input shares the seat and can move focus. It is not address-targeted background injection. '+pointer+'.'],
        ['Unicode typing and keys', '<code>wtype</code> or a virtual-keyboard client with XKB keymaps', 'Focused-target behavior; compose/IME workflows need testing. '+link('https://wayland.app/protocols/virtual-keyboard-unstable-v1', 'Keyboard protocol')+'.'],
        ['Targeted shortcuts', 'Hyprland <code>sendshortcut</code>', 'Useful for some windows, not a complete text/IME or independent-seat solution. '+link('https://wiki.hypr.land/0.52.0/Configuring/Dispatchers/', 'Versioned dispatcher documentation')+'.'],
        ['Fallback input', '<code>ydotool</code> through uinput', 'Requires device permissions and a daemon. Broad input capability; retain only if native protocols are insufficient.'],
        ['Clipboard', '<code>wl-clipboard</code>', 'Shared selection state; preserve/restore carefully. Some apps only accept paste with focus and a valid selection offer.']]) +
    p('The capture and input mechanisms above are separate. The XDPH interface declaration lists Screenshot, ScreenCast, GlobalShortcuts and InputCapture, but not RemoteDesktop. Therefore a libei/RemoteDesktop recipe cannot be assumed to work through XDPH. InputCapture captures input; it is not a substitute for RemoteDesktop injection. ' + link('https://raw.githubusercontent.com/hyprwm/xdg-desktop-portal-hyprland/master/hyprland.portal', 'XDPH portal declaration') + '.')))

two.append(('existing', 'Existing projects worth inspecting first',
    table(['Project', 'Relevant implementation', 'Assessment'], [
        [repo('hypruse'), 'Hyprctl, grim, wtype, direct virtual-pointer protocol and AT-SPI. Snapshot mapping, sequences and event waits.', 'Closest foreground starting point. Its README explicitly acknowledges a shared seat. Similar name; this new local project remains hypr-use.'],
        [repo('open-codex-computer-use'), 'Cross-platform implementation of the nine familiar tools.', 'Useful compatibility reference. Linux uses AT-SPI first; its own source calls pointer/key synthesis best-effort, not universal Wayland background input.'],
        [repo('hyprland-codex-background-computer-use'), 'Exact capture, native target-pointer extension, XTEST route, temporary headless fallback.', 'Author reports acceptance on 0.55.4, matching your version. Source reviewed; not independently runtime-validated here.'],
        [repo('Hypr-Agent-Protal'), 'Compositor rendering and direct keyboard/pointer transactions, related-dialog handling, MCP bridge.', 'Broader experimental background design, including 0.56-specific paths. Review ABI and security before adoption.'],
        [link('https://github.com/agent-sh/computer-use-linux', 'agent-sh/computer-use-linux'), 'AT-SPI with several compositor discovery backends, including Hyprland.', 'Maintainer reports real-session validation on GNOME; Hyprland implementation/test coverage is not equivalent to desktop validation.']]) +
    p('Read the code and reuse selectively before starting another complete automation stack. The likely contribution for hypr-use is a well-tested Codex contract, exact image mapping and honest background guarantees. ' + repo('open-codex-computer-use', 'apps/OpenComputerUseLinux/main.go', 'Linux implementation boundary') + '.')))

two.append(('background', 'How far background control can go',
    table(['Approach', 'Existing app sessions?', 'Independent input?', 'Recommendation'], [
        ['AT-SPI semantic actions', 'Yes', 'Often avoids pointer/focus changes', 'Use when the target control supports the operation; confirm app behavior.'],
        ['Hidden workspace or headless output', 'Yes', 'No, still the same compositor seat', 'Capture/organization aid and explicit compatibility fallback.'],
        ['Native compositor extension', 'Yes', 'Can route selected events without moving the physical cursor', 'Experimental, per-toolkit validation required.'],
        ['Nested compositor', 'Usually requires launching new app instances', 'Separate child seat, if backend wiring is correct', 'Good development environment; not transparent access to existing top-level windows.'],
        ['VM or separate desktop login', 'No automatic reuse of existing processes', 'Yes, within that environment', 'Strongest initial isolation for repeatable evaluation.']]) +
    p('The Gabriel-Kahen plugin actually sets pointer focus to the selected native surface, sends motion/button/axis frames, then restores pointer focus. It refuses a locked session, held physical buttons, pointer constraints and active drag-and-drop. It routes XWayland through a different path. These are source-observed mechanisms, not proof of universal background behavior. ' + repo('hyprland-codex-background-computer-use', 'hyprland/target-pointer.cpp', 'Target-pointer implementation') + '.') +
    p('Two concrete limitations in that source deserve testing: the scroll path emits only a vertical axis, and the drag path uses the main surface with interpolated events rather than a full cross-window drag-and-drop protocol. The broker delegates semantic accessibility to other tooling, so it is not a self-contained replacement for the complete Codex toolset. ' + repo('hyprland-codex-background-computer-use', 'src/same_session_computer_use/server.py', 'Broker implementation') + '.') +
    p('Hypr-Agent-Protal describes direct keyboard-resource transactions with restored modifier state and an XWayland compatibility lease. It also handles some related popups and offscreen window rendering. That is a stronger background design than moving the cursor away and back, but it adds compositor-internal dependencies and cannot be accepted solely from its README. ' + repo('Hypr-Agent-Protal') + '.') +
    p('A plugin bug executes inside the compositor and can terminate the desktop session. Pin the exact ABI and evaluate in a disposable nested session or VM first. This risk is specific to the proposed implementation, not a requirement for ordinary MCP or AT-SPI use.')))

two.append(('limits', 'Limitations to state explicitly',
    ul(['No general guarantee that a human and agent can operate arbitrary apps concurrently in one Hyprland seat. Multiple MCP clients need serialized input or independent environments.',
        'No universal tree of every UI control. Hyprctl knows windows, not the buttons inside them; AT-SPI depends on application support.',
        'No promise that every minimized, hidden or unrendered window produces a current image. A capture can be unavailable, stale or omit separate popups.',
        'No automatic transfer of existing Wayland app processes into a nested compositor or VM. Separate browser instances may need separate profiles and logins.',
        'XWayland is a separate compatibility case. XTEST can help X11 clients but cannot operate native Wayland windows, and X input focus remains shared.',
        'Lock screens, authentication prompts, secure input, pointer-locked games and cross-app drag-and-drop need explicit unsupported states or separate tested paths. Do not implement automatic unlocking as part of the MVP.',
        'Toolkit accessibility bounds, output scaling, rotation, client-side decorations and transient windows can disagree. Every coordinate must carry its reference frame.',
        'Hyprland APIs and configuration syntax evolve. The current wiki contains Lua-era examples; your 0.55.4 installation needs version-appropriate commands and builds.']) +
    p('These are engineering limits inferred from the mechanisms and implementations above. A policy check in the MCP broker is not an OS sandbox if the model also has unrestricted shell access to the same compositor and accessibility sockets. Hyprland\'s permission documentation likewise notes that IPC access requires external sandboxing. ' + link('https://wiki.hypr.land/configuring/core/advanced-configuration/permissions/', 'Hyprland permissions') + '.')))

two.append(('design', 'Proposed implementation',
    pre('Codex MCP adapter\n              |\n       snapshot and action engine\n       ├─ app/window identity + capability discovery\n       ├─ screenshot + coordinate transform\n       ├─ AT-SPI tree + snapshot-scoped references\n       ├─ semantic action → selected input backend\n       └─ result verification + cancellation\n\nBackends: AT-SPI semantic actions | compositor-assisted background input') +
    p('Keep stateful sessions in one process. Each observation should include app/window identity, snapshot ID, capture time, pixel dimensions, window geometry, image-to-input transform, tree truncation flags and available action modes. Each action should identify the snapshot it relies on. Reject unexpected focus changes or stale geometry instead of guessing.') +
    p('Prefer semantic actions where available, then image-based input through the selected backend. Return distinct statuses for unsupported, denied, stale target, injection failure and observed completion. A successful event-send call is not proof that a document was saved.') +
    pre('Example mapping, unrotated output with no resize:\n  screenshot pixel = (1600, 800)\n  output scale = 1.6\n  logical desktop point = (1000, 500)\n\nFor a crop, add its logical origin after scaling.\nFor resized or rotated images, compose the full transform.\nDo not assume capture pixels always equal native panel pixels.') +
    p('Use actual capture dimensions, not only the monitor scale. Fractional rendering and screenshot options can change the relationship. Validate popup geometry and AT-SPI window-relative bounds against images. Invalidate coordinates after window moves, scaling changes or output hotplug.') +
    p('For Codex, register an ordinary stdio MCP server plus Linux-specific operating instructions. Reuse the supported MCP integration instead of editing private desktop bundles. ' + link('https://learn.chatgpt.com/docs/extend/mcp?surface=cli', 'Official MCP integration') + '. On NixOS, package runtime dependencies together and derive native plugin headers from the exact Hyprland package. A user service must inherit the intended Wayland, runtime-directory and D-Bus environment.')))

two.append(('validation', 'A concrete investigation-to-prototype sequence',
    table(['Stage', 'Work', 'Pass condition'], [
        ['1. Observation', 'Build discovery + image + bounded AT-SPI snapshot. Test a fixture on the active and inactive workspace.', 'Correct window identity, sharp image, explicit tree gaps, accurate coordinates at your 1.6 scale.'],
        ['2. Background actions', 'Add semantic actions and compositor-targeted input, cancellation and held-key cleanup.', 'Edit/save/reopen a file while the human types elsewhere. Preserve physical cursor, focus and workspace.'],
        ['3. Compatibility', 'Expose the nine app-oriented tools; replay known calls against fixture apps.', 'Literal Unicode, modifiers, fractional scroll intent, stale IDs and errors retain their documented meaning.'],
        ['4. Background experiment', 'Evaluate the 0.55.4 extension and newer portal approach in a disposable desktop.', 'Measure physical cursor/focus changes, popup routing, rendering freshness and recovery after cancellation.'],
        ['5. Model evaluation', 'Pin model/settings; compare stock OSWorld with separately labeled Hyprland tasks.', 'Record completion, latency, retries, wrong-target input and human interventions, not just demo videos.']]) +
    p('Use fixtures spanning GTK, Qt, native Electron/Chromium, a canvas UI and XWayland. Include Japanese text, multiline paste, scaling changes, window replacement, modal dialogs, interrupted drags, denied permissions and session locking. The current session has no XWayland windows, so its metadata checks provide no evidence for that path.') +
    p('Updated recommendation: compare background implementations first, without restricting the Hyprland version. Require uninterrupted human input and exact background capture. Rank maintenance by substantive recent activity, fixes and compatibility tests, not version number alone. Responses API integration is out of scope. The repository created here contains the research and reproducible report builder; it does not yet contain an automation backend.')))

# Background-only reassessment, 6 September 2026. Keep the original research
# sections, but put the scoped decision and its stronger evidence first.
portal = 'Hypr-Agent-Protal'
two.insert(1, ('best-options', 'Best options for your background-only scope',
    p('<strong>First choice to evaluate: Hypr-Agent-Portal 0.4.0.</strong> It is the most complete match found for Codex MCP controlling existing Hyprland apps without taking the human keyboard focus. The corrected Portal spelling is now canonical. This is a recommendation to validate the implementation, not a claim that it already passes your non-interference requirement in every app.') +
    table(['Rank', 'Option', 'Why it fits', 'What remains'], [
        ['1', repo(portal, label='Hypr-Agent-Portal'), 'MCP app-state/actions, direct background keyboard and pointer delivery, offscreen window rendering, related-dialog routing and cancellation.', 'Clipboard isolation, concurrent pointer activity and XWayland require special handling. Broadest implementation; larger compositor codebase.'],
        ['2', repo('hyprland-codex-background-computer-use'), 'Smaller same-session broker and target-pointer extension. Exact capture and native background pointer transactions.', 'Needs a complete semantic/text layer, stronger ongoing ABI coverage and removal or disabling of foreground fallback. More implementation work.'],
        ['Conditional', 'Separate agent desktop', 'A VM or nested session provides a separate input environment and can host an MCP server.', 'Does not transparently control your existing windows and signed-in processes. Only an option if you accept separate app instances.'],
        ['Not a complete fit', repo('hypruse'), 'Actively maintained foreground tooling and reusable capture/AT-SPI components.', 'Named-seat support does not create a second seat. Missing seat falls back to the default, conflicting with your scope.']]) +
    p('Start by evaluating Portal on native Wayland applications, keeping XWayland explicitly experimental. Use direct key or AT-SPI text operations where possible; block automatic clipboard paste in the initial background profile. Leave workspace switching, human-window focus changes and foreground fallback unavailable. These are proposed integration constraints, not an assertion that one existing setting enforces all of them.') +
    p('Do not select a project merely because it targets a newer Hyprland. Portal wins here because its recent changes address the exact failure modes that matter to you.')))

two.insert(2, ('maintenance', 'Maintenance evidence and verification',
    table(['Project', 'Substantive activity', 'Verification evidence'], [
        ['Hypr-Agent-Portal', 'July: 0.56 adaptation. August 4: avoid global keyboard focus takeover. August 31: 0.4.0 with identity binding, cancellation policy and test fixes.', repo(portal, 'CHANGELOG.md', 'Changelog') + '; ' + link('https://github.com/gfhdhytghd/Hypr-Agent-Portal/actions/runs/33360181250', 'Successful CI at inspected HEAD') + '. Workflow checks native Debug/Release builds against 0.56.2.'],
        ['Gabriel-Kahen background tool', 'Inspected default-branch HEAD is July 10. Fixes cover capture transforms, atomic saves, session detection and Python/MCP CI.', link('https://github.com/Gabriel-Kahen/hyprland-codex-background-computer-use/actions/runs/29114441279', 'Successful CI at inspected HEAD') + '. Inspected workflow tests Python; no native-plugin build job. No published releases returned by GitHub.'],
        ['hypruse', 'August 14: named-seat keyboard/pointer work. August 31: Lua dispatcher repair and 0.10.0 release.', link('https://github.com/IlyasKhallouki/hypruse/actions/runs/33427133009', 'Successful CI at inspected HEAD') + '. Active development, but a different default input model.']]) +
    p('I refreshed upstream refs and checked GitHub release/CI metadata on 6 September 2026. Source revisions remain the same as the initial investigation. Push timestamps, default-branch commit dates and release dates are different signals; the comparison above uses actual commit content and CI configuration. The repository stores the API evidence in <code>maintenance-evidence.json</code>.') +
    p('Four Portal fixture scripts passed locally: keyboard routing, MCP geometry, identity binding and process leases. They ran with inaccessible display/session endpoints and did not load the native plugin. These checks cover Python behavior and source assertions; they do not demonstrate concurrent human/agent operation. Results are in <code>headless-checks.json</code>. ' + repo(portal, 'tests/keyboard_routing.py', 'Keyboard fixture') + '; ' + repo(portal, '.github/workflows/ci.yml', 'CI configuration') + '.') +
    p('Portal itself states that not all 0.4.0 additions were exercised in a live compositor before release. Its documented build target is 0.56.2, not an assurance of compatibility with every newer version. There is no basis here for promising production reliability or long-term maintainer support. ' + repo(portal, 'CHANGELOG.md', 'Release verification limits') + '.') +
    p('Reuse metadata: Portal declares GPL-3.0-only; hypruse declares MIT. The smaller Gabriel-Kahen checkout has no top-level license file and GitHub reports no detected license. Record that unresolved point before deciding to copy or redistribute its code.')))

two.insert(3, ('interference', 'What can still interfere with your work',
    table(['Case', 'Source finding', 'Consequence'], [
        ['Native Wayland typing', 'Portal sends enter/key/leave events to the target client keyboard resource, then restores prior surface and modifier state without changing compositor-global keyboard focus.', 'Best fit for typing in your own app while the agent types elsewhere. Still test two windows from the same application/client.'],
        ['Human mouse movement', 'Physical pointer activity cancels asynchronous agent pointer work. Human typing does not automatically cancel a native agent drag.', 'The design favors your input, but frequent mouse use may interrupt agent drags. Uninterrupted simultaneous pointer activity is not established.'],
        ['Clipboard paste', 'Paste writes the shared clipboard. Restore is opt-in and the inspected snapshot/restore helper handles text.', 'Background paste can replace what you just copied. Restore is not clipboard isolation and may race a new human copy; rich/image formats need separate handling.'],
        ['XWayland', 'Keyboard operations use temporary X focus leases, restored on human input.', 'Less isolated than the native Wayland path. Do not promise the same concurrency guarantee.'],
        ['Dialogs and background UI', 'Related-window logic keeps some same-process dialogs with the target workspace.', 'Cross-process dialogs, app-global state and attention requests remain test cases.'],
        ['Confirmation policy', 'Portal can require a physical F12 approval for classified high-risk actions.', 'Some workflows will require user attention even though normal input stays in the background.']]) +
    p(repo(portal, 'src/plugin/main.cpp', 'Native input, restoration and takeover code') + '; ' + repo(portal, 'mcp/hypr-agent-portal-mcp.py', 'Paste and clipboard implementation') + '.') +
    p('The smaller background tool also has a temporary headless-output compatibility fallback that can contend with physical input. Its Python broker exposes that path separately; exclude it from a strict background-only integration. Its native pointer path does not supply the full nine-tool semantic/text contract. ' + repo('hyprland-codex-background-computer-use', 'src/same_session_computer_use/server.py', 'Smaller broker') + '.') +
    p('A new finding in hypruse changes the earlier foreground-only description slightly: it can bind a named seat and route keyboard/pointer events there. However, it requires the compositor to provide that seat and warns before falling back to the default when missing. It does not establish an independent Hyprland seat by itself. ' + repo('hypruse', 'src/hypruse/wire.py', 'Named-seat resolution and fallback') + '.') +
    p('The upstream Hyprland discussion also narrows the native-API gap: dispatchers can target some mouse-button events, but the author reports that they do not provide complete arbitrary-coordinate motion, axis and drag transactions. The discussion is not evidence that a supported replacement API has shipped. ' + link('https://github.com/hyprwm/Hyprland/discussions/15377', 'Upstream targeting discussion') + '.')))

two.append(('choice', 'Decision and next experiment',
    p('Use hypr-use as a small Codex integration and validation repository around Hypr-Agent-Portal first. Avoid rebuilding its capture, geometry, tree and input layers until a measured gap requires it. Keep the smaller target-pointer project as an alternative if Portal proves too complex or intrusive.') +
    ul(['Build the pinned Portal revision with a matching Hyprland package in a disposable desktop. Upgrading your daily session is not needed for this investigation.',
        'Prove concurrent typing in two native apps, then two windows of the same app. Verify exact text in both and unchanged human focus/cursor/workspace.',
        'Test Japanese text, popup routing, human mouse use during agent drags, clipboard changes and cancellation. Fail an operation rather than take over the foreground.',
        'Only after these pass, test existing-session integration and XWayland separately. Keep a measured list of supported app/action combinations.']) +
    p('The recommendation is therefore Portal first, smaller custom integration second. Neither is yet demonstrated here to provide universal disturbance-free background use.')))

one = [section for section in one if section[0] != 'api']
one.append(('scoped-choice', 'Result of the background-only reassessment',
    p('The Linux shortlist now favors Hypr-Agent-Portal, followed by the smaller Gabriel-Kahen background broker. The decisive differences are target-client keyboard delivery, popup handling, clipboard behavior and maintenance of the compositor integration. Responses API integration has been removed from the implementation scope.') +
    p('<a href="hyprland-feasibility.html#best-options">Read the ranked options</a> and <a href="hyprland-feasibility.html#interference">remaining interference cases</a>. Four offline Portal fixture scripts passed; live background behavior has not been tested.')))

CSS = '''
:root{color-scheme:light;--bg:#faf8f5;--paper:#fff;--ink:#292524;--muted:#57534e;--line:#d6d3d1;--link:#92400e}
*{box-sizing:border-box}html{scroll-behavior:auto}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.65 "DejaVu Sans","Liberation Sans",sans-serif}main{max-width:1080px;margin:auto;padding:32px 28px 72px}header{border-bottom:1px solid var(--line);padding-bottom:24px}h1{font-size:30px;line-height:1.25;margin:12px 0 16px;letter-spacing:-.5px}h2{font-size:23px;line-height:1.35;margin:0 0 18px}p{max-width:90ch;margin:14px 0}a{color:var(--link);text-underline-offset:3px}a:hover{text-decoration-thickness:2px}a:focus-visible,summary:focus-visible,.table-scroll:focus-visible{outline:3px solid var(--link);outline-offset:4px}.meta{color:var(--muted);font-size:14px}.topnav{display:flex;gap:20px;flex-wrap:wrap}nav.contents{padding:20px 0;border-bottom:1px solid var(--line)}nav.contents ol{columns:2;gap:40px;margin:8px 0;padding-left:24px}nav.contents li{break-inside:avoid;padding:3px 0}section{padding:32px 0;border-bottom:1px solid var(--line);scroll-margin-top:20px}.table-scroll{overflow-x:auto;margin:20px 0}table{border-collapse:collapse;width:100%;font-size:14px;line-height:1.55}th,td{text-align:left;vertical-align:top;padding:12px;border-bottom:1px solid var(--line);min-width:150px}th{background:#f0eeeb;color:var(--ink)}td:first-child{font-weight:600;min-width:170px}code{font: .9em "DejaVu Sans Mono",monospace;overflow-wrap:anywhere}pre{background:#f0eeeb;border:1px solid var(--line);padding:18px;overflow-x:auto;line-height:1.55;font-size:14px}pre code{overflow-wrap:normal}li{margin:8px 0}footer{padding-top:24px;font-size:14px;color:var(--muted)}details{margin-top:20px}summary{cursor:pointer;font-weight:600}details li{overflow-wrap:anywhere}.skip{position:absolute;left:-10000px}.skip:focus{left:20px;top:10px;background:white;padding:10px}
@media(max-width:650px){main{padding:20px 18px 48px}h1{font-size:26px}h2{font-size:21px}nav.contents ol{columns:1}section{padding:26px 0}th,td{padding:10px;min-width:140px}.topnav{gap:12px}pre{font-size:12px}}
@media print{body{background:#fff;font-size:10pt}main{max-width:none;padding:0}nav,.skip{display:none}section{break-inside:auto;padding:18px 0}h2{break-after:avoid}tr{break-inside:avoid}a{color:inherit}pre{white-space:pre-wrap}table{font-size:9pt}.table-scroll{overflow:visible}details{display:none}}
'''

def build(filename, title, sections, other, other_title):
    contents = ''.join(f'<li><a href="#{key}">{heading}</a></li>' for key,heading,_ in sections)
    body = ''.join(f'<section id="{key}" aria-labelledby="heading-{key}"><h2 id="heading-{key}">{heading}</h2>{body}</section>' for key,heading,body in sections)
    pins = ul([repo(n, label=n+' · '+r['commit'][:12]) for n,r in sorted(REPOS.items())])
    text = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="description" content="{html.escape(title)}. Source-linked research for hypr-use, 6 September 2026."><title>{html.escape(title)} | hypr-use</title><style>{CSS}</style></head>
<body><a class="skip" href="#finding">Skip to report</a><main><header><nav class="topnav" aria-label="Reports"><a href="{other}">{other_title}</a><a href="#sources">Source revisions</a></nav><h1>{title}</h1><p class="meta">hypr-use · Research checked 6 September 2026</p><p><strong>Confirmed scope:</strong> background operation while the user works; Codex MCP only; Hyprland upgrades are acceptable. Foreground mechanisms below are comparisons, not qualifying solutions.</p></header><nav class="contents" aria-label="Contents"><ol>{contents}</ol></nav>{body}<footer id="sources"><p>Inline links identify the evidence for each finding. Repository links use the exact revisions inspected. Official documentation is a live source and may change after the research date.</p><details><summary>Inspected repository revisions</summary>{pins}</details><p><a href="#">Back to top</a></p></footer></main></body></html>'''
    (ROOT/'reports'/filename).write_text(text)

build('codex-computer-use.html', 'Codex computer use: implementation and model expectations', one, 'hyprland-feasibility.html', 'Read Hyprland feasibility')
build('hyprland-feasibility.html', 'Computer use on Hyprland: feasibility and limits', two, 'codex-computer-use.html', 'Read Codex implementation')
print('Built two standalone HTML reports.')
