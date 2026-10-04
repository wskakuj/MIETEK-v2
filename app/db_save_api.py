import base64
import hashlib
import json
import os
import tempfile
import threading
from pathlib import Path

try:                                   # uruchomienie jako skrypt (app/ na sys.path)
    from raporty_api import RaportyApi
except ImportError:                    # uruchomienie jako pakiet
    from .raporty_api import RaportyApi


class DbSaveApi(RaportyApi):
    def __init__(self):
        self._window = None
        self._root = None
        self._set_dir = None      # folder z plikami DBF (tu leży MIETEK_numery.json)
        self._lock = threading.Lock()

    # MIETEK_NUMERY_FILE_V14 ------------------------------------------------
    # Numery porządkowe i numery działek nie mieszczą się w DBF, więc trzymamy je
    # w pliku obok danych — dzięki temu jadą razem z folderem na inny komputer.
    NUMERY_PLIK = 'MIETEK_numery.json'

    def _numery_path(self):
        root = self._set_dir or self._root
        if not root:
            return None
        return Path(root) / self.NUMERY_PLIK

    def save_numery(self, wpisy):
        try:
            target = self._numery_path()
            if target is None:
                return {'ok': False, 'error': 'Najpierw wczytaj dane przez Wybierz folder lub Wybierz pliki.'}
            payload = {'wersja': 1,
                       'opis': 'MIETEK v2 — numery porządkowe i numery działek (poza DBF, do importu w Excelu)',
                       'wpisy': wpisy if isinstance(wpisy, dict) else {}}
            fd, tmp = tempfile.mkstemp(prefix='.mietek-numery-', dir=str(target.parent))
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                json.dump(payload, stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(tmp, str(target))
            return {'ok': True, 'path': str(target), 'ile': len(payload['wpisy'])}
        except Exception as e:
            return {'ok': False, 'error': str(e)}

    def save_dbf(self, entries):
        if not self._lock.acquire(False):
            return {'ok': False, 'error': 'Zapis jest już w toku.'}
        try:
            return self._save(entries)
        except PermissionError as e:
            return {'ok': False, 'error': 'Odmowa dostępu Windows. Zamknij MIETKA/vDos i inne programy korzystające z DBF; sprawdź atrybut Tylko do odczytu oraz uprawnienia pliku. Nie wymuszono zapisu. Szczegóły: '+str(e)}
        except Exception as e:
            return {'ok': False, 'error': str(e)}
        finally:
            self._lock.release()

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
            target = getattr(self, '_sources', {}).get(entry.get('token'))
            if target is None:
                raise ValueError('Wczytaj dane ponownie przez Wybierz folder lub Wybierz pliki w oknie programu. Przeciąganie i import przez przeglądarkę nie zachowują ścieżek zapisu.')
            current = target.read_bytes()
            matches = [(target,current)] if current == original else []
            if len(matches) != 1:
                self._root = None
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
            # MIETEK_DIALOG_MEMORY_V8
            chosen=self._window.create_file_dialog(kind,directory=self._last_dialog_directory(folder),allow_multiple=not folder)
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
            # folder z danymi = katalog plików DBF (tu trafi MIETEK_numery.json)
            dbf_dirs=sorted({p.parent for p in paths if p.suffix.lower()=='.dbf'},key=lambda d:str(d).casefold())
            if dbf_dirs:
                try:self._set_dir=Path(os.path.commonpath([str(d) for d in dbf_dirs]))
                except ValueError:self._set_dir=dbf_dirs[0]
            else:
                self._set_dir=root
            self._sources={}
            result=[]
            for p in sorted(paths,key=lambda p:str(p).casefold()):
                token=uuid.uuid4().hex;self._sources[token]=p
                result.append({'name':p.name,'relative':root.name+'/'+p.relative_to(root).as_posix(),'token':token,'data':base64.b64encode(p.read_bytes()).decode('ascii')})
            self._remember_dialog_directory(chosen,folder)
            # numery porządkowe / działki zapisane przy poprzedniej pracy
            numery={};sciezka=None
            np_=self._numery_path()
            if np_ is not None and np_.exists():
                sciezka=str(np_)
                try:
                    dane=json.loads(np_.read_text(encoding='utf-8'))
                    if isinstance(dane,dict) and isinstance(dane.get('wpisy'),dict):numery=dane['wpisy']
                except Exception:numery={}
            return {'ok':True,'files':result,'numery':numery,'numerySciezka':sciezka,'folder':str(self._set_dir)}
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


    def updater_check(self):
        from mietek_updater import MietekUpdater
        if not hasattr(self,'_updater'):self._updater=MietekUpdater(self._window)
        return self._updater.check()

    def updater_install(self,tag):
        if not hasattr(self,'_updater'):return {'ok':False,'error':'Najpierw sprawdź aktualizacje.'}
        return self._updater.install(tag)


    def _dialog_prefs_path(self):
        import os
        from pathlib import Path
        base = Path(os.environ.get('APPDATA') or (Path.home()/'.config'))
        return base/'MIETEK-v2'/'dialog_locations.json'

    def _read_dialog_prefs(self):
        import json
        try:
            data=json.loads(self._dialog_prefs_path().read_text(encoding='utf-8'))
            return data if isinstance(data,dict) else {}
        except (OSError,ValueError):return {}

    def _last_dialog_directory(self, folder):
        from pathlib import Path
        data=self._read_dialog_prefs()
        key='folder' if folder else 'files'
        for value in (data.get(key),data.get('last')):
            if not isinstance(value,str) or not value:continue
            try:
                p=Path(value)
                while not p.is_dir() and p!=p.parent:p=p.parent
                if p.is_dir():return str(p)
            except OSError:pass
        return str(Path.home())

    def _remember_dialog_directory(self, chosen, folder):
        import json,os,tempfile
        from pathlib import Path
        try:
            directory=Path(chosen[0]) if folder else Path(chosen[0]).parent
            data=self._read_dialog_prefs()
            data['folder' if folder else 'files']=str(directory)
            data['last']=str(directory)
            p=self._dialog_prefs_path();p.parent.mkdir(parents=True,exist_ok=True)
            fd,tmp=tempfile.mkstemp(prefix='locations-',suffix='.tmp',dir=p.parent)
            try:
                with os.fdopen(fd,'w',encoding='utf-8') as stream:
                    json.dump(data,stream,ensure_ascii=False);stream.flush();os.fsync(stream.fileno())
                os.replace(tmp,p)
            finally:
                if os.path.exists(tmp):os.unlink(tmp)
        except (OSError,ValueError):pass


    def app_version(self):
        try:
            from mietek_updater import current_version
            return {'ok':True,'version':current_version()}
        except Exception as e:
            return {'ok':False,'version':None,'error':str(e)}


    def save_export(self, name, data):
        import webview
        import base64, os, tempfile
        from pathlib import Path
        try:
            name=Path(str(name).replace('\\','/')).name
            suffix=Path(name).suffix.lower()
            if suffix not in ('.xlsx','.html','.txt','.zip'):
                raise ValueError('Nieobsługiwany format eksportu.')
            content=base64.b64decode(data,validate=True)
            dialog=getattr(getattr(webview,'FileDialog',None),'SAVE',None)
            if dialog is None:dialog=webview.SAVE_DIALOG
            selected=self._window.create_file_dialog(dialog,save_filename=name)
            if not selected:return {'ok':False,'cancelled':True}
            dest=Path(selected[0])
            if not dest.suffix:dest=dest.with_suffix(suffix)
            if dest.suffix.lower()!=suffix:raise ValueError('Wybierz plik z rozszerzeniem '+suffix+'.')
            fd,tmp=tempfile.mkstemp(prefix='.mietek-export-',dir=dest.parent)
            try:
                with os.fdopen(fd,'wb') as stream:
                    stream.write(content);stream.flush();os.fsync(stream.fileno())
                os.replace(tmp,dest)
            finally:
                if os.path.exists(tmp):os.unlink(tmp)
            return {'ok':True,'path':str(dest)}
        except Exception as e:return {'ok':False,'error':str(e)}
