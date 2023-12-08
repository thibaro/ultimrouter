from pathlib import Path
import datetime
import requests
import xarray as xr

from PySide2.QtCore import Qt, QObject, Signal, Slot, QThreadPool, QStandardPaths, QThread, QRunnable


K_GRIB_PRECISION = '0p50'

def rmdir(pth):
    for sub in pth.iterdir():
        if sub.is_dir():
            rmdir(sub)
        else:
            sub.unlink()
    pth.rmdir()

        

class GfsDownloadThread(QRunnable):
        
    def __init__(self, file, url):
        QRunnable.__init__(self)
        self.setAutoDelete(True)
        self.file = file
        self.url = url
        self.signals = GfsDownloadThread.ObjectSignals()
    
    class ObjectSignals(QObject):
        gfs_load = Signal(object)
        terminate_pass = Signal(object)
        terminate_fail = Signal(object)
    
    def run(self):
        if not self.file.is_file():
            download_ok = False
            for attempt in range(3):
                download_ok = self.download_attempt()
                if download_ok:
                    break
                else:
                    QThread().sleep(1)
        else:
            download_ok = True
        if download_ok:
            #gribdata = xr.open_dataset(str(self.file), engine='cfgrib', backend_kwargs={'filter_by_keys':{'typeOfLevel': 'unknown'}})
            #self.signals.gfs_load.emit(gribdata)
            self.signals.terminate_pass.emit(self.file)
        else:
            self.signals.terminate_fail.emit(self.file)
        return download_ok
            
    def download_attempt(self):
        try:
            r = requests.get(self.url)
            if r:
                with self.file.open(mode='wb') as f:
                    f.write(r.content)
                return True
            else:
                return False
        except:
            return False
 
        
class GribDownloadThread(QObject, QRunnable):
    def __init__(self):
        QObject.__init__(self)
        QRunnable.__init__(self)
        if K_GRIB_PRECISION == '0p25':
            self.resolution = '0p25'
        else:
            self.resolution = '0p50'
        self.setAutoDelete(False)
        self.threads = QThreadPool()
        self.threads.setMaxThreadCount(16)
        self.gribfiles = []
        self.gribdata = None
        
    progress = Signal()
    progressInit = Signal(int)
    terminated = Signal(object)
    
    def run(self):
        # Start at last grib
        date = datetime.date.today().strftime("%Y%m%d")
        hour = int(datetime.datetime.now().hour / 6)
        # Try upto 5 previous
        for attempt in range(5):
            if self.loadGfs(date, 6*hour):
                break
            if hour > 0:
                hour = hour - 1
            else:
                yesterday = datetime.datetime.now() - datetime.timedelta(days = 1)
                date = yesterday.strftime("%Y%m%d")
                hour = 3
        # Clean data
        outdir = Path(QStandardPaths.writableLocation(QStandardPaths.DataLocation)) / ('gfs.'+self.resolution+'.'+date+'.t'+'{:02d}'.format(hour)+'z')
        outdir = str(outdir.resolve())
        p = Path(QStandardPaths.writableLocation(QStandardPaths.DataLocation))
        for sub in p.iterdir():
            if sub.is_dir() and not( str(sub.resolve()) == outdir ):
                #rmdir(sub)
                print("Cleaned "+str(sub.resolve())+" "+outdir)
        # Terminate
        self.progressInit.emit(-1)
        self.terminated.emit(self.gribdata)
        #ds.u.sel(latitude=0,longitude=0).item(0)
        
    def loadGfs(self, date, hour):
        hour = '{:02d}'.format(hour)
        dir = Path(QStandardPaths.writableLocation(QStandardPaths.DataLocation)) / ('gfs.'+self.resolution+'.'+date+'.t'+hour+'z')
        dir.mkdir(parents=True, exist_ok=True)
        if self.resolution == '0p25':
            h_list = [i for j in (range(121), range(123, 385, 3)) for i in j]
        else:
            h_list = range(0, 145, 3)
        self.progressInit.emit(len(h_list))
        first = True
        for h in h_list:
            h = '{:03d}'.format(h)
            file = dir / ('gfs.'+self.resolution+'.'+date+'.t'+hour+'z.f'+h+'.grib2')
            if self.resolution == '0p25':
                url = 'https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25_1hr.pl?file=gfs.t'+hour+'z.pgrb2.0p25.f'+h+'&var_UGRD=on&var_VGRD=on&leftlon=0&rightlon=360&toplat=90&bottomlat=-90&dir=%2Fgfs.'+date+'%2F'+hour+'%2Fatmos'
            else:
                url = 'https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p50.pl?file=gfs.t'+hour+'z.pgrb2full.0p50.f'+h+'&var_UGRD=on&var_VGRD=on&leftlon=0&rightlon=360&toplat=90&bottomlat=-90&dir=%2Fgfs.'+date+'%2F'+hour+'%2Fatmos'
            th = GfsDownloadThread(file, url)
            th.signals.terminate_pass.connect(self.gfsTerminatePass, Qt.BlockingQueuedConnection)
            th.signals.terminate_fail.connect(self.gfsTerminateFail, Qt.BlockingQueuedConnection)
            th.signals.gfs_load.connect(self.gfsLoadData, Qt.BlockingQueuedConnection)
            if first:
                if not th.run():
                    return False
            else:
                self.threads.start(th)
            first = False
        self.threads.waitForDone()
        return True
    
    @Slot(object)
    def gfsTerminatePass(self, file):
        self.progress.emit()
        self.gribfiles.append(file)
        print('Loaded '+str(file))
            
    @Slot(object)
    def gfsTerminateFail(self, file):
        self.progress.emit()
        file.unlink(missing_ok=True)
        print('Fail load '+str(file))
            
    @Slot(object)
    def gfsLoadData(self, gribdata):
        if not self.gribdata:
            self.gribdata = gribdata
        else:
            self.gribdata = xr.concat([self.gribdata, gribdata], 'valid_time')
            
    @Slot()
    def abort(self):
        self.threads.clear()
        self.threads.waitForDone()
    
