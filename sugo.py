import io
import shutil
import sys
import os
import mimetypes
from math import ceil

from PyQt5 import QtCore, QtGui, QtWidgets, uic
from PyQt5.QtCore import Qt
import pdf2image


MOUSE_THRESHOLD = 3


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        uic.loadUi("assets/main.ui", self)
        self.setAcceptDrops(True)
        self.pdfViewerWidget = None
        self.virtualFiles = []

        self.promptLabel = self.findChild(QtWidgets.QLabel, "promptLabel")

        self.imageLabel = DragAndDropLabel("assets/upload.png")
        self.imageLabel.triggered.connect(self.load_document)
        self.centralWidget().layout().insertWidget(1, self.imageLabel)

        self.signWidget = SignWidget()
        self.signWidget.update.connect(self.show_sign)

        self.scrollArea = self.findChild(QtWidgets.QScrollArea, "scrollArea")
        self.scrollArea.hide()

        self.setSelectionsButton = self.findChild(QtWidgets.QPushButton, "setPointsButton")
        self.setSelectionsButton.clicked.connect(self.set_sign_areas)
        self.setSelectionsButton.hide()

        self.confirmButton = self.findChild(QtWidgets.QPushButton, "confirmButton")
        self.confirmButton.clicked.connect(self.save_pdf)
        self.confirmButton.hide()
        self.cancelButton = self.findChild(QtWidgets.QPushButton, "cancelButton")
        self.cancelButton.clicked.connect(self.reset)
        self.cancelButton.hide()

        self.clearShortcut = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+L"), self)
        self.clearShortcut.activated.connect(self.ask_sign)

        self.show()

    def set_sign_areas(self):
        self.pdfViewerWidget.trigger_selection()
        if self.setSelectionsButton.text() != "Confirm sign points":
            self.setSelectionsButton.setText("Confirm sign points")
        else:
            self.setSelectionsButton.setText("Set sign points")

    def save_pdf(self):
        pass

    def reset(self):
        pass

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
                self.pdfViewerWidget = PdfViewerWidget(path)
                self.scrollArea.setWidget(self.pdfViewerWidget)
                self.scrollArea.show()
                self.setSelectionsButton.show()

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
    def __init__(self, parent: SignWidget, rect: QtCore.QRect):
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
        self.setPixmap(pixmap.scaledToWidth(100, Qt.SmoothTransformation))

    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        self.triggered.emit("")

    def dragEnterEvent(self, a0: QtGui.QDragEnterEvent) -> None:
        a0.acceptProposedAction()

    def dropEvent(self, a0: QtGui.QDropEvent) -> None:
        a0.acceptProposedAction()
        self.triggered.emit(f'/{a0.mimeData().text().lstrip("file://")}')


class PdfViewerWidget(QtWidgets.QWidget):
    def __init__(self, path: str):
        super(PdfViewerWidget, self).__init__()
        self.mainLayout = QtWidgets.QVBoxLayout()
        self.pages = pdf2image.convert_from_path(path, 200)
        self.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)

        if not os.path.isdir("tmp"):
            os.mkdir("tmp")

        for idx, page in enumerate(self.pages):
            virtual_file = io.BytesIO()
            page.save(virtual_file, 'PNG')
            virtual_file.seek(0)
            virtual_file = virtual_file.read()
            scene = PageGraphicsScene(self, virtual_file, idx)
            gview = PageGraphicsView(scene)
            self.mainLayout.addWidget(gview)

        self.setLayout(self.mainLayout)

    def trigger_selection(self):
        gviews = self.findChildren(PageGraphicsView)
        for gview in gviews:
            scene = gview.scene
            scene.trigger_selection()


class PageGraphicsView(QtWidgets.QGraphicsView):
    def __init__(self, scene: QtWidgets.QGraphicsScene):
        super(PageGraphicsView, self).__init__()
        self.scene = scene

        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.setScene(self.scene)
        self.setMinimumHeight(ceil(self.scene.height()))


class PageGraphicsScene(QtWidgets.QGraphicsScene):
    def __init__(self, parent: QtWidgets.QWidget, image_bytes: bytes, page_number: int):
        super(PageGraphicsScene, self).__init__()
        self.parent = parent
        self.image = QtGui.QImage()
        self.page_number = page_number
        self.selectionFlag = False
        self.rubberBand = None
        self.mouse_origin = None
        self.mouse_end = None
        self.rect_fields = []

        self.image.loadFromData(image_bytes)
        pixmap = QtGui.QPixmap(self.image)
        pixmap = QtWidgets.QGraphicsPixmapItem(pixmap.scaledToWidth(self.parent.width(), Qt.SmoothTransformation))
        self.addItem(pixmap)

    def mousePressEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        # print(f"page: {self.page_number}, coord: {event.scenePos()}")
        if self.selectionFlag:
            self.mouse_origin = self.views()[0].mapFromScene(event.scenePos().toPoint())
            if self.rubberBand is None:
                self.rubberBand = QtWidgets.QRubberBand(QtWidgets.QRubberBand.Rectangle, self.views()[0])
            else:
                return
            self.rubberBand.setGeometry(QtCore.QRect(self.mouse_origin, QtCore.QSize()))
            self.rubberBand.show()

    def mouseMoveEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        if self.selectionFlag and self.rubberBand is not None:
            self.mouse_end = self.views()[0].mapFromScene(event.scenePos().toPoint())
            self.rubberBand.setGeometry(self.improved_rect(self.mouse_origin, self.mouse_end).toRect())

    def mouseReleaseEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        if self.selectionFlag and self.rubberBand is not None:
            self.rubberBand.hide()
            self.rubberBand = None
            origin = self.views()[0].mapToScene(self.mouse_origin)
            end = self.views()[0].mapToScene(self.mouse_end)
            self.rect_fields.append([self.page_number,
                                     self.addRect(self.improved_rect(origin, end),
                                                  brush=QtGui.QBrush(QtGui.QColor(0x0, 0x98, 0x3A, 120)))
                                     ])

    @staticmethod
    def improved_rect(p1: QtCore.QPointF, p2: QtCore.QPointF):
        x_min = min(p1.x(), p2.x())
        x_max = max(p1.x(), p2.x())
        y_min = min(p1.y(), p2.y())
        y_max = max(p1.y(), p2.y())
        return QtCore.QRectF(QtCore.QPointF(x_min, y_min), QtCore.QPointF(x_max, y_max))
    
    def trigger_selection(self):
        if self.selectionFlag:
            self.selectionFlag = False
        else:
            self.selectionFlag = True
            for item in self.items():
                if isinstance(item, QtWidgets.QGraphicsRectItem):
                    self.removeItem(item)
            self.rect_fields.clear()


def main():
    if os.path.isdir("tmp"):
        shutil.rmtree("tmp")
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    app.exec()


if __name__ == "__main__":
    main()