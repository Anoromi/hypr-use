#!/usr/bin/env python3
"""macOS Computer Use vocabulary over Hypr-Agent-Portal; stdio MCP."""
import importlib.util
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads((Path(__file__).with_name('tools.json')).read_text())


def load_backend():
    path = ROOT / 'vendor/hypr-agent-portal-0.56.2/mcp/hypr-agent-portal-mcp.py'
    spec = importlib.util.spec_from_file_location('hypr_use_portal', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate(args, schema):
    if not isinstance(args, dict):
        raise ValueError('arguments must be an object')
    properties = schema['properties']
    if set(args) - set(properties):
        raise ValueError('Unknown arguments: ' + ', '.join(sorted(set(args) - set(properties))))
    for key in schema.get('required', []):
        if key not in args:
            raise ValueError('Missing argument: ' + key)
    for key, value in args.items():
        rule = properties[key]
        kind = rule['type']
        valid = (isinstance(value, str) if kind == 'string' else
                 type(value) is int if kind == 'integer' else
                 type(value) in (int, float))
        if not valid:
            raise ValueError(key + ' must be ' + kind)
        if 'enum' in rule and value not in rule['enum']:
            raise ValueError('Invalid ' + key)
        if 'minimum' in rule and value < rule['minimum']:
            raise ValueError(key + ' is below minimum')
        if kind == 'number':
            import math
            if not math.isfinite(value):
                raise ValueError(key + ' must be finite')


class Adapter:
    def __init__(self, backend, aliases=None, command_modifier='ctrl'):
        if command_modifier not in ('ctrl', 'super'):
            raise ValueError('HYPR_USE_COMMAND_MODIFIER must be ctrl or super')
        self.backend = backend
        self.delegate = backend.handle
        self.aliases = aliases or {}
        if not isinstance(self.aliases, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in self.aliases.items()):
            raise ValueError('HYPR_USE_APP_ALIASES must be a JSON object of strings')
        self.command_modifier = command_modifier
        self.tools = {t['name']: t for t in CONTRACT}

    def handle(self, message):
        if not isinstance(message, dict) or message.get('jsonrpc') != '2.0' or not isinstance(message.get('method'), str):
            return {'jsonrpc': '2.0', 'id': message.get('id') if isinstance(message, dict) else None,
                    'error': {'code': -32600, 'message': 'Invalid JSON-RPC request'}}
        method = message['method']
        if 'id' not in message:
            if method.startswith('notifications/'):
                self.delegate(message)
            return None
        if method == 'initialize':
            out = self.delegate(message)
            out['result']['serverInfo'] = {'name': 'hypr-use', 'version': '0.1.0'}
            out['result']['instructions'] = ('Linux/Hyprland background computer use. Use Linux app classes or configured aliases. '
                'Call get_app_state before interacting; element IDs and coordinates belong to that snapshot. '
                f'Mac super/cmd/command modifiers map to {self.command_modifier}. '
                'No app launch, recording or computer-history tools are provided. '
                'App support and focus isolation depend on the portal plugin; errors are not evidence of completion.')
            return out
        if method == 'tools/list':
            # Keep the backend owner policy authoritative for discovery as well as execution.
            allowed = {t['name'] for t in self.backend.tool_definitions()}
            return {'jsonrpc': '2.0', 'id': message['id'], 'result': {'tools': [t for t in CONTRACT if t['name'] in allowed]}}
        if method == 'tools/call':
            try:
                params = message.get('params', {})
                if not isinstance(params, dict):
                    raise ValueError('params must be an object')
                name = params.get('name')
                if not isinstance(name, str) or name not in self.tools:
                    raise ValueError('Unknown tool')
                args = dict(params.get('arguments', {})) if isinstance(params.get('arguments', {}), dict) else params['arguments']
                validate(args, self.tools[name]['inputSchema'])
                if 'app' in args:
                    args['app'] = self.aliases.get(args['app'], args['app'])
                if name == 'press_key':
                    args['key'] = ' '.join('+'.join(self.command_modifier if token.lower() in ('super', 'cmd', 'command') else token
                        for token in combo.split('+')) for combo in args['key'].split())
                forwarded = {**message, 'params': {**params, 'arguments': args}}
                return self.delegate(forwarded)
            except (ValueError, TypeError) as exc:
                return {'jsonrpc': '2.0', 'id': message['id'], 'result': {
                    'content': [{'type': 'text', 'text': str(exc)}], 'isError': True}}
        return self.delegate(message)


def main():
    backend = load_backend()
    adapter = Adapter(backend, json.loads(os.environ.get('HYPR_USE_APP_ALIASES', '{}')),
                      os.environ.get('HYPR_USE_COMMAND_MODIFIER', 'ctrl'))
    backend.handle = adapter.handle
    backend.ensure_session_environment()
    # These ten primitives are serial. Forward lifecycle notifications to Portal.
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
        except ValueError:
            out = {'jsonrpc': '2.0', 'id': None, 'error': {'code': -32700, 'message': 'Invalid JSON'}}
        else:
            try:
                out = adapter.handle(message)
            except Exception as exc:
                out = {'jsonrpc': '2.0', 'id': message.get('id') if isinstance(message, dict) else None,
                       'error': {'code': -32603, 'message': str(exc)}}
        if out is not None:
            print(json.dumps(out, ensure_ascii=False), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
