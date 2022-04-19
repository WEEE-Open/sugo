import sys
from PyQt5 import QtCore, QtGui, QtWidgets, uic
from PyQt5.QtCore import Qt

MOUSE_THRESHOLD = 3


class Ui(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("asdone.ui", self)
        width = 500
        height = 500
        self.resize(QtCore.QSize(width, height))

        self.graphicsView = self.findChild(QtWidgets.QGraphicsView, "graphicsView")
        self.scene = GraphicsScene(self, self.graphicsView.rect())
        self.graphicsView.setScene(self.scene)

        # self.label = self.findChild(QtWidgets.QLabel, "draw_label")
        # self.label.setScaledContents(True)
        # self.textLabel = self.findChild(QtWidgets.QLabel, "textLabel")
        # self.canvas = QtGui.QPixmap(100,100)
        # self.label.setPixmap(self.canvas)
        #
        # self.painter = QtGui.QPainter(self.label.pixmap())

        self.show()


class GraphicsScene(QtWidgets.QGraphicsScene):
    def __init__(self, parent: QtWidgets.QMainWindow, rect: QtCore.QRect):
        QtWidgets.QGraphicsScene.__init__(self, parent)
        self.setSceneRect(QtCore.QRectF(rect))

        self.lastMousePosition = None
        self.redBrush = QtGui.QBrush(Qt.red)
        self.blackPen = QtGui.QPen(Qt.black)

        self.clearShortcut = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+D"), parent)
        self.clearShortcut.activated.connect(self.clear)

    def mousePressEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        self.lastMousePosition = event.scenePos()

    def mouseMoveEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        if self.lastMousePosition is None:
            return

        position = event.scenePos()
        if (position - self.lastMousePosition).manhattanLength() > MOUSE_THRESHOLD:
            self.addLine(QtCore.QLineF(self.lastMousePosition, position), self.blackPen)
            self.lastMousePosition = position

    def mouseReleaseEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        self.lastMousePosition = None


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = Ui()
    app.exec()


if __name__ == "__main__":
    main()