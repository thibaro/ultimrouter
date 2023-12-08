from PySide2.QtWidgets import QGraphicsView
from PySide2.QtGui import QTransform, QCloseEvent
from PySide2.QtCore import Signal, Slot, Qt, QPointF


K_UI_DEBUG = False


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
        
        
