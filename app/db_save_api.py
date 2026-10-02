import base64
import hashlib
import os
import tempfile
import threading
from pathlib import Path

class DbSaveApi:
    def __init__(self):
        self.window = None
        self.root = None
        self.lock = threading.Lock()

    def save_dbf(self, entries):
        if not self.lock.acquire(False):
            return {'ok': False, 'error': 'Zapis jest już w toku.'}
        try:
            return self._save(entries)
        except Exception as e:
            return {'ok': False, 'error': str(e)}
        finally:
            self.lock.release()

    def _save(self, entries):
        import webview
        if not entries:
            raise ValueError('Brak danych do zapisu.')
        if self.root is None:
            dialog = getattr(getattr(webview, 'FileDialog', None), 'FOLDER', None)
            if dialog is None:
                dialog = webview.FOLDER_DIALOG
            selected = self.window.create_file_dialog(dialog)
            if not selected:
                return {'ok': False, 'error': 'Anulowano wybór folderu. Zmiany pozostają niezapisane.'}
            self.root = Path(selected[0]).resolve()
        prepared = []
        seen = set()
        for entry in entries:
            name = entry['name']
            if Path(name).name != name or '/' in name or '\\' in name or not name.lower().endswith('.dbf'):
                raise ValueError('Nieprawidłowa nazwa DBF.')
            original = base64.b64decode(entry['original'], validate=True)
            new = base64.b64decode(entry['data'], validate=True)
            matches = []
            for parent, dirs, files in os.walk(self.root, followlinks=False):
                dirs[:] = [d for d in dirs if not (Path(parent)/d).is_symlink()]
                for f in files:
                    target = Path(parent)/f
                    if f.casefold() == name.casefold() and not target.is_symlink():
                        current = target.read_bytes()
                        if current == original:
                            matches.append((target, current))
            if len(matches) != 1:
                self.root = None
                raise ValueError('Plik '+name+': znaleziono '+str(len(matches))+' zgodnych oryginałów. Wybierz dokładny podfolder danych przy następnym zapisie. Nie podmieniono DBF.')
            target, current = matches[0]
            if target in seen:
                raise ValueError('Powtórzony plik docelowy.')
            seen.add(target)
            prepared.append((target,current,new))
        staged = []
        changed = []
        try:
            for target,original,new in prepared:
                if target.read_bytes() != original:
                    raise ValueError('Plik zmienił się na dysku: '+target.name)
                fd,tmp = tempfile.mkstemp(prefix='.mietek-',dir=target.parent)
                with os.fdopen(fd,'wb') as stream:
                    stream.write(new);stream.flush();os.fsync(stream.fileno())
                staged.append((target,Path(tmp),original))
            # Create all backups before replacing any DBF.
            for target,tmp,original in staged:
                backup=target.with_suffix('.bak')
                if backup.exists():
                    n=1
                    while backup.with_name(backup.name+'.'+str(n)).exists(): n+=1
                    os.replace(backup,backup.with_name(backup.name+'.'+str(n)))
                fd,btmp=tempfile.mkstemp(prefix='.mietek-bak-',dir=target.parent)
                try:
                    with os.fdopen(fd,'wb') as stream:
                        stream.write(original);stream.flush();os.fsync(stream.fileno())
                    os.replace(btmp,backup)
                finally:
                    if os.path.exists(btmp):os.unlink(btmp)
            for target,tmp,original in staged:
                if target.read_bytes()!=original:
                    raise ValueError('Plik został zmieniony przez inny program: '+target.name)
                os.replace(tmp,target)
                changed.append((target,original))
            return {'ok':True,'files':[str(t) for t,_,_ in prepared]}
        except Exception as error:
            rollback_errors=[]
            for target,original in reversed(changed):
                try:
                    fd,tmp=tempfile.mkstemp(prefix='.mietek-restore-',dir=target.parent)
                    with os.fdopen(fd,'wb') as stream:
                        stream.write(original);stream.flush();os.fsync(stream.fileno())
                    os.replace(tmp,target)
                except Exception as e: rollback_errors.append(str(target)+': '+str(e))
            if rollback_errors:
                raise RuntimeError(str(error)+'; BŁĄD PRZYWRACANIA: '+'; '.join(rollback_errors))
            raise
        finally:
            for _,tmp,_ in staged:
                if tmp.exists():tmp.unlink()
