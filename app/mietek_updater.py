import sys, os, json, re, hashlib, tempfile, subprocess, threading, time
import urllib.request
from pathlib import Path

API='https://api.github.com/repos/wskakuj/MIETEK-v2/releases/latest'

def version_tuple(value):
    text=str(value).strip().lstrip('vV')
    if not re.fullmatch(r'\d+(?:\.\d+)*',text):raise ValueError('Nieobsługiwany numer wersji: '+text)
    parts=tuple(int(x) for x in text.split('.'))
    return parts+(0,)*(max(0,4-len(parts)))

def current_version():
    root=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent.parent))
    p=root/'VERSION'
    if not p.is_file():raise ValueError('Brak VERSION. Zbuduj EXE po zastosowaniu poprawki V6.')
    return p.read_text(encoding='utf-8-sig').strip()

class MietekUpdater:
    def __init__(self,window):
        self.window=window;self.release=None;self.lock=threading.Lock()
    def check(self):
        try:
            current=current_version()
            req=urllib.request.Request(API,headers={'User-Agent':'MIETEK-v2-Updater','Accept':'application/vnd.github+json'})
            with urllib.request.urlopen(req,timeout=10) as r:release=json.load(r)
            if release.get('draft') or release.get('prerelease'):raise ValueError('Nieprawidłowe wydanie stabilne.')
            tag=release['tag_name']
            newer=version_tuple(tag)>version_tuple(current)
            self.release=release if newer else None
            return {'ok':True,'available':newer,'current':current,'latest':tag,'notes':release.get('body',''),'frozen':bool(getattr(sys,'frozen',False))}
        except Exception as e:return {'ok':False,'error':str(e)}
    def install(self,expected_tag):
        if not getattr(sys,'frozen',False) or os.name!='nt':
            return {'ok':False,'error':'Instalacja automatyczna działa wyłącznie w skompilowanym EXE na Windows. W źródłach dostępne jest sprawdzanie wersji.'}
        if not self.lock.acquire(False):return {'ok':False,'error':'Aktualizacja już trwa.'}
        try:
            release=self.release
            if not release or release['tag_name']!=expected_tag:raise ValueError('Sprawdź aktualizacje ponownie.')
            allowed=('mietek.v2.by.forestly.exe','mietek v2 by forestly.exe')
            assets=[a for a in release.get('assets',[]) if a.get('name','').casefold() in allowed]
            if len(assets)!=1:raise ValueError('Wydanie nie zawiera jednoznacznego pliku EXE MIETKA.')
            asset=assets[0];url=asset['browser_download_url']
            if not url.startswith('https://github.com/wskakuj/MIETEK-v2/releases/download/'):
                raise ValueError('Niedozwolony adres pobierania.')
            digest=asset.get('digest','')
            if not re.fullmatch(r'sha256:[0-9a-fA-F]{64}',digest):raise ValueError('Brak sumy SHA-256 wydania — nie podmieniono EXE.')
            target=Path(sys.executable).resolve()
            fd,tmp=tempfile.mkstemp(prefix='.MIETEK-update-',suffix='.exe',dir=target.parent)
            try:
                req=urllib.request.Request(url,headers={'User-Agent':'MIETEK-v2-Updater'})
                hashed=hashlib.sha256();size=0
                with os.fdopen(fd,'wb') as out,urllib.request.urlopen(req,timeout=60) as source:
                    while True:
                        chunk=source.read(1024*1024)
                        if not chunk:break
                        out.write(chunk);hashed.update(chunk);size+=len(chunk)
                    out.flush();os.fsync(out.fileno())
                if size!=asset.get('size') or hashed.hexdigest().lower()!=digest.split(':')[1].lower():
                    raise ValueError('Nieprawidłowy rozmiar lub SHA-256 pobranego EXE.')
                with open(tmp,'rb') as f:
                    if f.read(2)!=b'MZ':raise ValueError('Pobrany plik nie jest EXE.')
                ps=self._script(target,Path(tmp))
                script=Path(tempfile.mkdtemp(prefix='MIETEK-updater-'))/'install.ps1'
                script.write_text(ps,encoding='utf-8-sig')
                env={k:v for k,v in os.environ.items() if not k.upper().startswith(('_MEI','_PYI')) and k.upper() not in ('PYTHONHOME','PYTHONPATH','TCL_LIBRARY','TK_LIBRARY')}
                env['PATH']=os.pathsep.join(p for p in os.environ.get('PATH','').split(os.pathsep) if '_MEI' not in p.upper())
                subprocess.Popen(['powershell.exe','-NoProfile','-STA','-ExecutionPolicy','Bypass','-File',str(script)],env=env,creationflags=subprocess.CREATE_NO_WINDOW)
                threading.Timer(1.0,self.window.destroy).start()
                return {'ok':True}
            except Exception:
                if os.path.exists(tmp):os.unlink(tmp)
                raise
        except Exception as e:return {'ok':False,'error':str(e)}
        finally:self.lock.release()
    def _script(self,target,download):
        def q(s):return "'"+str(s).replace("'","''")+"'"
        backup=str(target)+'.old_'+str(time.time_ns())
        ps=r"""Add-Type -AssemblyName System.Windows.Forms
$ErrorActionPreference='Stop'
$target=__TARGET__
$download=__DOWNLOAD__
$backup=__BACKUP__
$form=New-Object System.Windows.Forms.Form
$form.Text='MIETEK v2 — Aktualizacja'
$form.Width=500;$form.Height=150;$form.StartPosition='CenterScreen'
$label=New-Object System.Windows.Forms.Label
$label.Left=20;$label.Top=25;$label.Width=450;$label.Height=60
$label.Text='Pobrano i zweryfikowano EXE. Czekam na zamknięcie MIETKA...'
$form.Controls.Add($label)
$form.Add_Shown({
  $renamed=$false
  try {
    $clock=[Diagnostics.Stopwatch]::StartNew()
    while(Get-Process -Id __PID__ -ErrorAction SilentlyContinue){
      [Windows.Forms.Application]::DoEvents();Start-Sleep -Milliseconds 200
      if($clock.Elapsed.TotalSeconds -gt 60){throw 'Program nie zamknął się. Nie podmieniono EXE.'}
    }
    $label.Text='Instalowanie nowej wersji...';$form.Refresh()
    Move-Item -LiteralPath $target -Destination $backup -ErrorAction Stop
    $renamed=$true
    Move-Item -LiteralPath $download -Destination $target -ErrorAction Stop
    $env:PYINSTALLER_RESET_ENVIRONMENT='1'
    Start-Process -FilePath $target -WorkingDirectory (Split-Path $target) -ErrorAction Stop
    $label.Text='Aktualizacja zakończona. Kopia starego EXE została zachowana.'
    $form.Refresh();Start-Sleep -Seconds 2
  } catch {
    $msg=$_.Exception.Message
    if($renamed){
      try {
        if(Test-Path -LiteralPath $target){Move-Item -LiteralPath $target -Destination ($target+'.failed_'+[DateTime]::Now.Ticks)}
        Move-Item -LiteralPath $backup -Destination $target
      } catch {$msg+=' Nie udało się przywrócić EXE. Kopia: '+$backup}
    }
    [Windows.Forms.MessageBox]::Show($msg,'Błąd aktualizacji') | Out-Null
  }
  $form.Close()
})
[void]$form.ShowDialog()
"""
        return ps.replace('__TARGET__',q(target)).replace('__DOWNLOAD__',q(download)).replace('__BACKUP__',q(backup)).replace('__PID__',str(os.getpid()))
