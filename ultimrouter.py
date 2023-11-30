import sys
from pathlib import Path
import datetime
import geojson
import requests
import xarray as xr

#Open source and modular platform designed to experiment routing algorithm for Virtual Regatta
#https://github.com/datasets/geo-countries
#https://geojson-maps.ash.ms/

#https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25_1hr.pl?file=gfs.t12z.pgrb2.0p25.f000&var_UGRD=on&var_VGRD=on&leftlon=0&rightlon=360&toplat=90&bottomlat=-90&dir=%2Fgfs.20210111%2F12
# 0 120 step 1
# 123 384 step 3

from PySide2.QtWidgets import (QApplication, QLabel, QPushButton,
                               QVBoxLayout, QWidget, QGraphicsScene, QGraphicsView, QGraphicsPolygonItem, QMainWindow, QProgressBar, QSizePolicy,
                               QGraphicsLineItem )
from PySide2.QtGui import QPolygonF, QTransform, QPen, QBrush, QColor, QCloseEvent
from PySide2.QtCore import QObject, Signal, Slot, Qt, QDataStream, QPointF, QRectF, QThread, QSettings, QStandardPaths, QCoreApplication, QThreadPool, QRunnable


K_UI_DEBUG = False
K_GRIB_PRECISION = '0p50'



def toDms_(l):
    d = int(l)
    l = 60*(l - d)
    m = int(l)
    l = 60*(l - m)
    s = int(l)
    return str(d)+'°'+str(m)+'"'+str(s)+'\''

def toDms(point):
    if point.y() >= 0.0:
        lat = toDms_(point.y())+'N'
    else:
        lat = toDms_(-point.y())+'S'
    if point.x() >= 0.0:
        long = toDms_(point.x())+'E'
    else:
        long = toDms_(-point.x())+'W'
    return lat+' '+long

def frange(start, stop=None, step=None):
    start = float(start)
    if stop == None:
        stop = start + 0.0
        start = 0.0
    if step == None:
        step = 1.0

    while start < stop:
        yield start
        start += step
        
def rmdir(pth):
    for sub in pth.iterdir():
        if sub.is_dir():
            rmdir(sub)
        else:
            sub.unlink()
    pth.rmdir()


class MyGraphicsScene(QGraphicsScene):
    def __init__(self):
        QGraphicsScene.__init__(self)
        
        brush = QBrush()
        brush.setColor(QColor('#d5e5ff'))
        brush.setStyle(Qt.SolidPattern)
        self.setBackgroundBrush(brush)
        self.loadCountries()
        self.loadLongitudesLatitudes()
        
        self.gribdata = None
    
    def loadCountries(self):
        pen = QPen()
        pen.setWidth(0)
        pen.setColor(QColor('#a0a0a0'))
        brush = QBrush()
        brush.setColor(QColor('#fff6d5'))
        brush.setStyle(Qt.SolidPattern)
        
        self.min = QPointF(0.0, 0.0)
        self.max = QPointF(0.0, 0.0)
        
        self.countries = QGraphicsPolygonItem()
        self.countries_360 = QGraphicsPolygonItem()
        self.addItem(self.countries)
        self.addItem(self.countries_360)

        geofile = 'world.medium.geojson'
        with open(geofile, 'r') as file:
            dbjson = geojson.loads(file.read())

        if not dbjson:
            print('continent not loaded')
            exit()
        for country in dbjson['features']:
            #print(str(country['properties']['ADMIN']))
            if country['geometry']['type'] == 'MultiPolygon':
                for record in country['geometry']['coordinates']:
                    for pol in record:
                        self.loadCountriesPolygon(pol, pen, brush)    
            elif country['geometry']['type'] == 'Polygon':
                for record in country['geometry']['coordinates']:
                    self.loadCountriesPolygon(record, pen, brush)
                    
        self.wind_0 = QGraphicsPolygonItem()
        self.addItem(self.wind_0)
        
    def loadCountriesPolygon(self, iterable, pen, brush):
        polygonf = QPolygonF()
        for point in iterable:
            if self.min.x() > point[0]:
                self.min.setX(point[0])
            if self.max.x() < point[0]:
                self.max.setX(point[0])
            if self.min.y() > point[1]:
                self.min.setY(point[1])
            if self.max.y() < point[1]:
                self.max.setY(point[1])
            polygonf.append(QPointF(point[0], point[1]))
        polygon = QGraphicsPolygonItem( polygonf, self.countries)
        polygon.setPen(pen)
        polygon.setBrush(brush)

        polygon = QGraphicsPolygonItem( polygonf, self.countries_360)
        polygon.setPos(QPointF(360.0, 0.0))
        polygon.setPen(pen)
        polygon.setBrush(brush)
        
    def loadLongitudesLatitudes(self):
        pen = QPen()
        pen.setWidth(0)
        pen.setColor(QColor('#a0a0a0'))
        
        # Longitudes
        for i in range(-180, 541, 5):
            l = QGraphicsLineItem(i, -90, i, 90)
            l.setPen(pen)
            self.addItem(l)
        # Latitudes
        for i in range(-90, 91, 5):
            l = QGraphicsLineItem(-180, i, 540, i)
            l.setPen(pen)
            self.addItem(l)
            
    def loadGribData(self, gribdata):
        if not gribdata:
            return
        
        self.gribdata = gribdata
        
        pen = QPen()
        pen.setWidth(0)
        pen.setColor(QColor('#a0a0a0'))
        brush = QBrush()
        brush.setColor(QColor('#00ff00'))
        brush.setStyle(Qt.SolidPattern)
        
        polygonf = QPolygonF()
        polygonf.append(QPointF(0.0, 0.0))
        polygonf.append(QPointF(0.25, 0.12))
        polygonf.append(QPointF(0.25, -0.12))
        
        
        min = QPointF(0.0, 0.0)
        max = QPointF(0.0, 0.0)
        
        for lat in self.gribdata.latitude:
            for lon in self.gribdata.longitude:
                if min.x() > lon.item(0):
                    min.setX(lon.item(0))
                if max.x() < lon.item(0):
                    max.setX(lon.item(0))
                if min.y() > lat.item(0):
                    min.setY(lat.item(0))
                if max.y() < lat.item(0):
                    max.setY(lat.item(0))
                polygon = QGraphicsPolygonItem( polygonf, self.wind_0)
                polygon.setPos(QPointF(lon.item(0), lat.item(0)))
                polygon.setPen(Qt.NoPen)
                polygon.setBrush(brush)
        
        if False:
            for lat in frange(-90.0, 90.1, 0.5):
                for lon in frange(0.0, 360.1, 0.5):
                    polygon = QGraphicsPolygonItem( polygonf, self.wind_0)
                    polygon.setPos(QPointF(lon, lat))
                    polygon.setPen(Qt.NoPen)
                    polygon.setBrush(brush)
        
        print('grib loaded')
        print(str(self.min)+' '+str(self.max))
        print(str(min)+' '+str(max))
        
    def isOnSea(self, position):
        if (position.y() > 90.0) or (position.y() < -90.0):
            return True
        if position.x() > 180.0:
            position.setX(position.x() - 360.0)
        for country in self.countries.childItems():
            if country.boundingRect().contains(position):
                if country.contains(position):
                    return False
        return True
        
        
class MyView(QGraphicsView):
    def __init__(self, scene):
        QGraphicsView.__init__(self, scene)
        self.scale(1.0, -1.0)
        self.setMouseTracking(True)
        if not K_UI_DEBUG:
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # Zoom management
        self.zoom = 1.0
        self.zoomInFactor = 1.20
        self.zoomOutFactor = 1 / self.zoomInFactor
        # Move management
        self.leftMousePressed = False
        self._moveStartX = 0
        self._moveStartY = 0

    # Signals
    signalMouseCoordinate = Signal(QPointF)
    
    @Slot()
    def resizeEvent(self, event):
        if not K_UI_DEBUG:
            if self.zoom < self.viewport().size().width()/360.0:
                self.applyZoom(self.viewport().size().width()/360.0)
            else:
                QGraphicsView.resizeEvent(self, event)
        else:
            QGraphicsView.resizeEvent(self, event)
                
    @Slot()
    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            if event.delta() > 0:
                self.applyZoom(self.zoom * self.zoomInFactor)
            elif event.delta() < 0:
                self.applyZoom(self.zoom * self.zoomOutFactor)
        else:
            QGraphicsView.wheelEvent(self, event)
            
    @Slot()
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.leftMousePressed = True
            self._moveStartX = event.x()
            self._moveStartY = event.y()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
        else:
            QGraphicsView.mousePressEvent(self, event)
    
    @Slot()
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.leftMousePressed = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
        else:
            QGraphicsView.mouseReleaseEvent(self, event)

    @Slot()
    def mouseMoveEvent(self, event):
        self.signalMouseCoordinate.emit(self.mapToScene(event.pos()))
        if self.leftMousePressed:
            p = self.horizontalScrollBar().value() - (event.x() - self._moveStartX)
            if not K_UI_DEBUG:
                max = self.horizontalScrollBar().maximum()
                min = self.horizontalScrollBar().minimum()
                width = self.mapToScene(self.viewport().rect()).boundingRect().width()
                scroll_180 = 360.0*(max-min)/(720-width) + min
                if p < min:
                    p = p - min + scroll_180
                elif p > scroll_180:
                    p = p + min - scroll_180
            self.horizontalScrollBar().setValue(p)
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - (event.y() - self._moveStartY))
            self._moveStartX = event.x()
            self._moveStartY = event.y()
            event.accept()
        else:
            QGraphicsView.mouseMoveEvent(self, event)
            
    def applyZoom(self, zoom):
        self.zoom = zoom
        if not K_UI_DEBUG:
            if self.zoom < self.viewport().size().width()/360.0:
                self.zoom = self.viewport().size().width()/360.0
        anchor = self.transformationAnchor()
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        transform = QTransform()
        transform.scale(self.zoom, -self.zoom)
        self.setTransform(transform)
        self.setTransformationAnchor(anchor)
        
    def fitOrigin(self):
        self.applyZoom(self.viewport().size().width()/360.0)
        self.horizontalScrollBar().setValue(self.horizontalScrollBar().minimum())
        
        

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
    
                
class MyMainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.scene = MyGraphicsScene()
        self.view = MyView(self.scene)
        self.setCentralWidget(self.view)
        
        self.statusCoordinate = QLabel(toDms(QPointF(0.0, 0.0)))
        self.statusBar().addWidget(self.statusCoordinate)
        self.statusCoordinate.setFixedWidth(150)
        self.view.signalMouseCoordinate.connect(self.mouseCoordinateChange)
        
        self.progressBar = QProgressBar()
        self.statusBar().addPermanentWidget(self.progressBar)
        
        self.gribProcess = GribDownloadThread()
        self.gribProcess.progress.connect(self.progress)
        self.gribProcess.progressInit.connect(self.progressInit)
        self.gribProcess.terminated.connect(self.loadGribData)
        QThreadPool.globalInstance().start(self.gribProcess)
        
    def open(self):
        self.resize(800, 600)
        self.view.fitOrigin()
        
    @Slot(QPointF)
    def mouseCoordinateChange(self, point):
        self.statusCoordinate.setText(toDms(point))
        
    @Slot(QCloseEvent)
    def closeEvent(self, event):
        #settings = QSettings("MyCompany", "MyApp")
        #settings.setValue("geometry", self.saveGeometry())
        #settings.setValue("windowState", self.saveState())
        self.gribProcess.abort()
        QThreadPool.globalInstance().waitForDone()
        QMainWindow.closeEvent(self, event)
        
    @Slot(int)
    def progressInit(self, val):
        if val > 0:
            self.progressBar.setMaximum(val)
            self.progressBar.setValue(0)
        else:
            self.progressBar.reset()
        
    @Slot()
    def progress(self):
        self.progressBar.setValue(self.progressBar.value() + 1)
        
    @Slot(object)
    def loadGribData(self, gribdata):
        self.scene.loadGribData(gribdata)
        
        
if __name__ == "__main__":
    QCoreApplication.setOrganizationName("rtc")
    QCoreApplication.setApplicationName("ultimrouter")

    app = QApplication(sys.argv)

    window = MyMainWindow()
    window.open()
    window.show()

    sys.exit(app.exec_())
