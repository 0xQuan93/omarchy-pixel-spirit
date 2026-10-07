#!/usr/bin/env python3
"""Install or remove Wisp without touching packaged Omarchy files or state."""

import ast
import datetime
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile


source = Path(__file__).resolve().parent
home = Path.home()
plugin = home / '.config/omarchy/plugins/oxquan.pixel-spirit'
shell = home / '.config/omarchy/shell.json'
stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
OWNED = '.wisp-owned-files.json'
LOCAL_OVERLAY = '.wisp-managed-overlay.json'


def write(path, data):
    """Atomically write one configuration file, retaining its previous bytes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() == data:
            return
        backup = path.with_name(path.name + '.before-wisp-' + stamp)
        suffix = 0
        while True:
            try:
                backup_fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                break
            except FileExistsError:
                suffix += 1
                backup = path.with_name(path.name + '.before-wisp-' + stamp + '-' + str(suffix))
        try:
            with os.fdopen(backup_fd, 'wb') as stream, path.open('rb') as original:
                shutil.copyfileobj(original, stream)
                stream.flush()
                os.fsync(stream.fileno())
            shutil.copystat(path, backup)
        except BaseException:
            backup.unlink(missing_ok=True)
            raise
    # Keep an existing shell.json symlink and replace its destination atomically.
    destination = path.resolve() if path.is_symlink() else path
    mode = stat.S_IMODE(destination.stat().st_mode) if destination.exists() else None
    fd, temporary = tempfile.mkstemp(prefix='.' + destination.name + '.wisp-', dir=destination.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            if mode is not None:
                os.fchmod(stream.fileno(), mode)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _relative(name):
    path = Path(name)
    return not path.is_absolute() and path.parts and all(part not in ('.', '..') for part in path.parts)


def _public_files():
    files = {path.name: path for path in (source / 'plugin').iterdir() if path.is_file()}
    files['setup_screensaver.py'] = source / 'setup_screensaver.py'
    files['tools/fetch_voice_model.py'] = source / 'tools/fetch_voice_model.py'
    return files


def _stage_generation():
    """Build a complete flat plugin away from the live plugin discovery path."""
    plugin.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.wisp-stage-', dir=plugin.parent.parent))
    try:
        if os.path.lexists(plugin):
            if plugin.is_symlink() or not plugin.is_dir():
                raise ValueError('The installed Wisp path is not a regular directory')
            if os.path.lexists(plugin / LOCAL_OVERLAY):
                raise ValueError('This Wisp installation has a managed local overlay. Use its composed installer for updates.')
            if (plugin / '.git').exists():
                raise ValueError('Use omarchy plugin update for a git-managed installation')
            # Keep user-owned local adapters and other additions in the candidate.
            shutil.copytree(plugin, stage, dirs_exist_ok=True, symlinks=True)
            for path in stage.rglob('*'):
                if path.is_symlink():
                    raise ValueError('Installed plugin contains a symlink: ' + str(path.relative_to(stage)))
            old_owned = stage / OWNED
            if old_owned.exists():
                names = json.loads(old_owned.read_text())
                if not isinstance(names, list) or any(not isinstance(n, str) or not _relative(n) for n in names):
                    raise ValueError('Invalid previous Wisp file inventory')
                for name in names:
                    target = stage / name
                    if target.is_file() or target.is_symlink():
                        target.unlink()
        owned = _public_files()
        for name, path in owned.items():
            if not _relative(name) or path.is_symlink() or not path.is_file():
                raise ValueError('Invalid Wisp source file: ' + name)
            target = stage / name
            if target.is_symlink():
                raise ValueError('Refusing to replace a symlinked plugin file: ' + name)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
        manifest = json.loads((source / 'manifest.json').read_text())
        manifest['entryPoints'] = {
            key: value.removeprefix('plugin/') for key, value in manifest['entryPoints'].items()
        }
        manifest.pop('icon', None)
        (stage / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        (stage / OWNED).write_text(json.dumps(sorted([*owned, 'manifest.json']), indent=2) + '\n')
        _validate_generation(stage)
        return stage
    except BaseException:
        shutil.rmtree(stage)
        raise


def _validate_generation(stage):
    manifest = json.loads((stage / 'manifest.json').read_text())
    if (manifest.get('schemaVersion') != 1 or manifest.get('id') != 'oxquan.pixel-spirit'
            or not isinstance(manifest.get('kinds'), list)
            or set(manifest['kinds']) != {'service', 'bar-widget'}
            or not isinstance(manifest.get('entryPoints'), dict)):
        raise ValueError('Staged Wisp manifest is incomplete')
    for key in ('service', 'barWidget'):
        name = manifest['entryPoints'].get(key)
        if not isinstance(name, str) or not _relative(name) or not (stage / name).is_file():
            raise ValueError('Missing staged Wisp entry point: ' + key)
    for path in stage.rglob('*'):
        if path.is_symlink():
            raise ValueError('Staged plugin contains a symlink: ' + str(path.relative_to(stage)))
        if path.is_file() and path.suffix == '.py':
            ast.parse(path.read_bytes(), filename=str(path))
    # The host's manifest validator catches contract changes before any switch.
    if shutil.which('omarchy'):
        subprocess.run(['omarchy', 'plugin', 'validate', str(stage)], check=True)


def _reserve_backup():
    root = plugin.parent.parent / '.wisp-install-backups'
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    candidate = root / ('oxquan.pixel-spirit-' + stamp)
    suffix = 0
    while os.path.lexists(candidate):
        suffix += 1
        candidate = root / ('oxquan.pixel-spirit-' + stamp + '-' + str(suffix))
    return candidate


def _activate(stage, data):
    """Switch generations, restoring the prior one if shell activation fails."""
    previous = _reserve_backup() if os.path.lexists(plugin) else None
    moved_old = False
    moved_new = False
    try:
        if previous is not None:
            os.replace(plugin, previous)
            moved_old = True
        os.replace(stage, plugin)
        moved_new = True
        write(shell, (json.dumps(data, indent=2) + '\n').encode())
    except BaseException as error:
        try:
            if moved_new:
                os.replace(plugin, stage)
            if moved_old:
                os.replace(previous, plugin)
        except BaseException as rollback_error:
            raise RuntimeError('Wisp install rollback failed. Previous generation remains at '
                               + str(previous) + ': ' + str(rollback_error)) from error
        raise
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return previous


def _shell_data():
    data = json.loads(shell.read_text())
    if not isinstance(data, dict) or not isinstance(data.get('bar'), dict):
        raise ValueError('Invalid Omarchy shell configuration')
    layout = data['bar'].get('layout')
    if not isinstance(layout, dict) or not isinstance(layout.get('left'), list):
        raise ValueError('Invalid Omarchy bar layout')
    plugins = data.setdefault('plugins', [])
    if not isinstance(plugins, list) or any(not isinstance(entry, dict) for entry in plugins):
        raise ValueError('Invalid Omarchy plugin list')
    for section in layout.values():
        if not isinstance(section, list) or any(not isinstance(entry, dict) for entry in section):
            raise ValueError('Invalid Omarchy bar section')
        section[:] = [entry for entry in section if entry.get('id') != 'oxquan.pixel-spirit']
    data['plugins'] = [entry for entry in plugins if entry.get('id') != 'oxquan.pixel-spirit']
    return data


def probe_host():
    """Read-only prerequisites, intended for compatibility reports."""
    return {
        'python': '.'.join(map(str, sys.version_info[:3])),
        'pythonReady': sys.version_info >= (3, 11),
        'omarchyFound': bool(shutil.which('omarchy')),
        'quickshellFound': bool(shutil.which('quickshell')),
        'shellConfigFound': shell.is_file(),
        'shellSourceFound': (Path(os.environ.get('OMARCHY_PATH', '/usr/share/omarchy')) / 'shell').is_dir(),
    }


def main():
    if '--check-host' in sys.argv:
        print(json.dumps(probe_host(), indent=2))
        return
    remove = '--remove' in sys.argv
    if remove:
        subprocess.run([sys.executable, str(source / 'setup_screensaver.py'), '--remove'], check=True)
    data = _shell_data()
    if not remove:
        data['plugins'].append({'id': 'oxquan.pixel-spirit'})
        data['bar']['layout']['left'].append({'id': 'oxquan.pixel-spirit'})
        stage = _stage_generation()
        previous = _activate(stage, data)
        model = source / 'models/ggml-tiny.en.bin'
        if model.exists():
            target = home / '.local/share/pixel-spirit/ggml-tiny.en.bin'
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                try:
                    shutil.copy2(model, target)
                except OSError as error:
                    print('Optional voice model was not copied: ' + str(error))
        if previous is not None:
            print('Previous plugin generation: ' + str(previous))
    else:
        write(shell, (json.dumps(data, indent=2) + '\n').encode())
    disabled = data.get('disabledPlugins', [])
    explicitly_disabled = isinstance(disabled, list) and 'oxquan.pixel-spirit' in disabled
    result = ('removed from shell configuration' if remove else
              'installed but disabled' if explicitly_disabled else 'installed')
    print('Wisp ' + result + '. Config backups: .before-wisp-' + stamp)
    if not remove and explicitly_disabled:
        print('Your disabled setting was preserved. To enable Wisp, open Omarchy menu > Setup > Plugins > Enable Plugin and choose Wisp (oxquan.pixel-spirit).')


if __name__ == '__main__':
    main()
