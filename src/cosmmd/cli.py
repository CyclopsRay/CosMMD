"""Small CLI; geometry calibration is intentionally an explicit workflow stage."""
import argparse
import json
import subprocess
from pathlib import Path


def main():
    p = argparse.ArgumentParser(prog='cosmmd')
    sub = p.add_subparsers(dest='command', required=True)
    g = sub.add_parser('generate', help='Plan or run one image → Tripo model + auto-rig')
    g.add_argument('--image', required=True)
    g.add_argument('--run', required=True)
    g.add_argument('--execute', action='store_true', help='Submit generation/rig tasks; spends provider credits')
    g.add_argument('--model', default='v3.1-20260211')
    g.add_argument('--rig-model', default='v1.0-20240301')
    i = sub.add_parser('inspect', help='Inspect source geometry and skeleton')
    i.add_argument('--blender', required=True)
    i.add_argument('--source', required=True)
    i.add_argument('--output', required=True)
    i.add_argument('--save')
    r = sub.add_parser('render', help='Render every frame in a fresh Blender process')
    r.add_argument('--blender', required=True)
    r.add_argument('--scene', required=True)
    r.add_argument('--output', required=True)
    r.add_argument('--start', type=int, default=1)
    r.add_argument('--count', type=int, default=360)
    r.add_argument('--step', type=int, default=1)
    r.add_argument('--size', type=int, default=720)
    r.add_argument('--samples', type=int, default=64)
    r.add_argument('--device', default='CPU', choices=['CPU','METAL','CUDA','OPTIX','HIP'])
    q = sub.add_parser('qa', help='Scan every rendered frame and create contact sheets')
    q.add_argument('directory')
    q.add_argument('--expected', type=int)
    q.add_argument('--step', type=int)
    q.add_argument('--report', required=True)
    q.add_argument('--contact-sheets')
    a = sub.add_parser('audit', help='Audit Git index + reachable history before publishing')
    a.add_argument('directory', nargs='?', default='.')
    args = p.parse_args()
    try:
        if args.command == 'generate':
            from .tripo import generate
            print(json.dumps(generate(args.image, args.run, args.execute, args.model, args.rig_model), indent=2))
        elif args.command == 'render':
            from .render import render
            render(args.blender, args.scene, args.output, args.start, args.count,
                   args.step, args.size, args.samples, args.device)
        elif args.command == 'inspect':
            worker = Path(__file__).with_name('blender') / 'inspect_scene.py'
            command = [args.blender, '--factory-startup', '-b', '--python-exit-code', '1', '--python', str(worker), '--',
                       '--source', args.source, '--output', args.output]
            if args.save:
                command += ['--save', args.save]
            subprocess.run(command, check=True)
        elif args.command == 'qa':
            from .qa import inspect_frames, contact_sheets
            report = inspect_frames(args.directory, args.expected, args.step)
            if args.contact_sheets:
                report['contact_sheets'] = contact_sheets(args.directory, args.contact_sheets)
            Path(args.report).parent.mkdir(parents=True, exist_ok=True)
            Path(args.report).write_text(json.dumps(report, indent=2))
            print(json.dumps({k: v for k, v in report.items() if k != 'frames'}, indent=2))
            if report['errors'] or report['suspicious_frames']:
                raise SystemExit(2)
        elif args.command == 'audit':
            from .publish_guard import audit
            report = audit(args.directory)
            print(json.dumps(report, indent=2))
            if not report['ok']:
                raise SystemExit(2)
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as error:
        p.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
