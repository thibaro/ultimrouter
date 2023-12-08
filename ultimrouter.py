import sys
from pathlib import Path
import datetime
import geojson
import requests
import xarray as xr

from grib import GribDownloadThread
from ui_main import MyView, MyGraphicsScene

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
