import sys
from PyQt5 import QtCore, QtGui, QtWidgets, uic
from PyQt5.QtCore import Qt

MOUSE_THRESHOLD = 3


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        uic.loadUi("assets/main.ui", self)

        self.imageLabel = self.findChild(QtWidgets.QLabel, "imageLabel")
        self.show()
        self.signWidget = SignWidget()
        self.signWidget.update.connect(self.show_sign)


    def show_sign(self, pixmap: QtGui.QPixmap):
        self.imageLabel.setPixmap(pixmap)


class SignWidget(QtWidgets.QWidget):
    update = QtCore.pyqtSignal(QtGui.QPixmap, name="event")

    def __init__(self):
        super(SignWidget, self).__init__()
        uic.loadUi("assets/signwidget.ui", self)

        # Setup graphics view and scene
        self.graphicsView = self.findChild(QtWidgets.QGraphicsView, "graphicsView")
        self.scene = GraphicsScene(self, self.graphicsView.rect())
        self.graphicsView.setScene(self.scene)

        # setup buttons
        self.confirmButton = self.findChild(QtWidgets.QPushButton, "confirmButton")
        self.confirmButton.clicked.connect(self.confirm_sign)
        self.cancelButton = self.findChild(QtWidgets.QPushButton, "cancelButton")
        self.cancelButton.clicked.connect(self.close)

        self.show()

    def confirm_sign(self):
        signPixmap = QtGui.QPixmap(self.graphicsView.viewport().size())
        pixmap = QtGui.QPixmap(signPixmap.size())
        pixmap.fill(Qt.transparent)
        self.graphicsView.viewport().render(signPixmap)
        mask = signPixmap.createMaskFromColor(Qt.black, Qt.MaskOutColor)
        painter = QtGui.QPainter(pixmap)
        painter.setPen(Qt.black)
        painter.drawPixmap(pixmap.rect(), mask, mask.rect())
        painter.end()
        self.update.emit(pixmap)
        self.close()


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
    window = MainWindow()
    app.exec()


if __name__ == "__main__":
    main()