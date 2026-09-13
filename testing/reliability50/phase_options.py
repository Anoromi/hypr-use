"""Require explicit resumption so an old phase cannot masquerade as a fresh run."""
import argparse
import re


def prepare_phase(argv, runs, task_ids):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase')
    parser.add_argument('tasks', nargs='*')
    parser.add_argument('--resume', action='store_true', help='Explicitly reuse completed results and continue missing tasks; source hashes must still match')
    args = parser.parse_args(argv)
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', args.phase):
        parser.error('Phase must be a single directory name')
    selected = set(args.tasks)
    unknown = selected - set(task_ids)
    if unknown:
        parser.error('Unknown task IDs: ' + ', '.join(sorted(unknown)))
    out = runs / args.phase
    if args.resume:
        if not (out / 'manifest.json').is_file():
            parser.error('--resume requires an existing phase manifest')
    else:
        try:
            out.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            parser.error('Phase already exists; choose a new name for a fresh run, or explicitly use --resume to reuse its results')
    return args.phase, selected, out, args.resume
