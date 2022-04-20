import sys
import os
import mimetypes
from PyQt5 import QtCore, QtGui, QtWidgets, QtWebEngineWidgets, uic
from PyQt5.QtCore import Qt
import pdf2image


MOUSE_THRESHOLD = 3


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        uic.loadUi("assets/main.ui", self)
        self.setAcceptDrops(True)
        self.pdfViewer = None

        self.promptLabel = self.findChild(QtWidgets.QLabel, "promptLabel")
        self.imageLabel = DragAndDropLabel("assets/upload.jpg")
        self.imageLabel.triggered.connect(self.load_document)
        self.centralWidget().layout().addWidget(self.imageLabel)
        self.signWidget = SignWidget()
        self.signWidget.update.connect(self.show_sign)

        self.clearShortcut = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+L"), self)
        self.clearShortcut.activated.connect(self.ask_sign)

        self.show()

    def load_document(self, path: str):
        if path == "":
            path = QtWidgets.QFileDialog.getOpenFileName(self, 'Open File', "~", "PDF (*.pdf)")[0]
            if path == "":
                return
        if os.path.isfile(path):
            mtypes = mimetypes.guess_type(path)
            if mtypes and 'application/pdf' in mtypes:
                self.imageLabel.hide()
                self.promptLabel.hide()
                self.pdfViewer = PdfViewerEngine(path)
                # PdfViewer(path)
                self.centralWidget().layout().addWidget(self.pdfViewer)

    def ask_sign(self):
        self.signWidget.show()

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


class DragAndDropLabel(QtWidgets.QLabel):
    triggered = QtCore.pyqtSignal(str)

    def __init__(self, image_path: str):
        super(DragAndDropLabel, self).__init__()
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignHCenter)
        pixmap = QtGui.QPixmap(image_path)
        self.setPixmap(pixmap.scaledToWidth(500, Qt.SmoothTransformation))

    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        self.triggered.emit("")

    def dragEnterEvent(self, a0: QtGui.QDragEnterEvent) -> None:
        a0.acceptProposedAction()

    def dropEvent(self, a0: QtGui.QDropEvent) -> None:
        a0.acceptProposedAction()
        self.triggered.emit(a0.mimeData().text().lstrip("file:///"))


class PdfViewer(QtWidgets.QScrollArea):
    def __init__(self, path: str):
        super(PdfViewer, self).__init__()
        self.pdfPages = pdf2image.convert_from_path(path)


class PdfViewerEngine(QtWebEngineWidgets.QWebEngineView):
    def __init__(self, path: str):
        super(PdfViewerEngine, self).__init__()
        self.settings().setAttribute(QtWebEngineWidgets.QWebEngineSettings.PluginsEnabled, True)
        self.load(QtCore.QUrl.fromLocalFile(path))


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    app.exec()


if __name__ == "__main__":
    main()