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
        except PermissionError as e:
            return {'ok': False, 'error': 'Odmowa dostępu Windows. Zamknij MIETKA/vDos i inne programy korzystające z DBF; sprawdź atrybut Tylko do odczytu oraz uprawnienia pliku. Nie wymuszono zapisu. Szczegóły: '+str(e)}
        except Exception as e:
            return {'ok': False, 'error': str(e)}
        finally:
            self.lock.release()

    def _save(self, entries):
        import webview
        if not entries:
            raise ValueError('Brak danych do zapisu.')
        prepared = []
        seen = set()
        for entry in entries:
            name = entry['name']
            if Path(name).name != name or '/' in name or '\\' in name or not name.lower().endswith('.dbf'):
                raise ValueError('Nieprawidłowa nazwa DBF.')
            original = base64.b64decode(entry['original'], validate=True)
            new = base64.b64decode(entry['data'], validate=True)
            target = getattr(self, 'sources', {}).get(entry.get('token'))
            if target is None:
                raise ValueError('Wczytaj dane ponownie przez Wybierz folder lub Wybierz pliki w oknie programu. Przeciąganie i import przez przeglądarkę nie zachowują ścieżek zapisu.')
            current = target.read_bytes()
            matches = [(target,current)] if current == original else []
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


    def load_native(self, folder=True):
        import webview, uuid
        try:
            kind = getattr(getattr(webview,'FileDialog',None), 'FOLDER' if folder else 'OPEN', None)
            if kind is None: kind=webview.FOLDER_DIALOG if folder else webview.OPEN_DIALOG
            chosen=self.window.create_file_dialog(kind,allow_multiple=not folder)
            if not chosen:return {'ok':False,'cancelled':True}
            paths=[]
            if folder:
                root=Path(chosen[0]).resolve()
                for parent,dirs,files in os.walk(root,followlinks=False):
                    dirs[:]=[d for d in dirs if not (Path(parent)/d).is_symlink()]
                    paths.extend(Path(parent)/f for f in files if Path(f).suffix.lower() in ('.dbf','.lst') and not (Path(parent)/f).is_symlink())
            else:
                paths=[Path(p).resolve() for p in chosen if Path(p).suffix.lower() in ('.dbf','.lst')]
                root=Path(os.path.commonpath([str(p.parent) for p in paths])) if paths else Path(chosen[0]).parent
            self.sources={}
            result=[]
            for p in sorted(paths,key=lambda p:str(p).casefold()):
                token=uuid.uuid4().hex;self.sources[token]=p
                result.append({'name':p.name,'relative':root.name+'/'+p.relative_to(root).as_posix(),'token':token,'data':base64.b64encode(p.read_bytes()).decode('ascii')})
            return {'ok':True,'files':result}
        except Exception as e:return {'ok':False,'error':str(e)}

    def open_report(self, html, print_now=False):
        import webbrowser
        try:
            fd,p=tempfile.mkstemp(prefix='MIETEK-wydruk-',suffix='.html')
            if print_now:
                html=html.replace('</body>','<script>window.addEventListener("load",function(){setTimeout(function(){window.print();},350);});</script></body>')
            with os.fdopen(fd,'w',encoding='utf-8') as stream:stream.write(html)
            if not webbrowser.open(Path(p).resolve().as_uri()):
                return {'ok':False,'error':'Nie udało się otworzyć przeglądarki. Plik: '+p}
            return {'ok':True}
        except Exception as e:return {'ok':False,'error':str(e)}
