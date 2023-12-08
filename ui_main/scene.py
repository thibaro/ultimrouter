import geojson

from PySide2.QtWidgets import QGraphicsScene, QGraphicsPolygonItem, QSizePolicy, QGraphicsLineItem
from PySide2.QtGui import QPolygonF, QPen, QBrush, QColor
from PySide2.QtCore import Signal, Slot, Qt, QPointF


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

        geofile = 'data/world.medium.geojson'
        with open(geofile, 'r') as file:
            dbjson = geojson.loads(file.read())

        if not dbjson:
            print('continent not loaded')
            exit()
        for country in dbjson['features']:
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
