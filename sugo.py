import io
import shutil
import sys
import os
import mimetypes
import pdf2image
from PIL import Image
from pathlib import Path
from math import ceil
from PyQt5 import QtCore, QtGui, QtWidgets, uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QGraphicsSceneMouseEvent

MOUSE_THRESHOLD = 3


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        uic.loadUi("assets/main.ui", self)
        self.setAcceptDrops(True)
        self.settings = QtCore.QSettings("WEEE-Open", "SUGO")
        self.last_sing_positions = self.settings.value("lastSignPositions")
        self.pdfViewerWidget = None
        self.virtualFiles = []
        self.pdf_path = None

        """ Defining menu actions """
        self.actionNew = self.findChild(QtWidgets.QAction, "actionNew")
        self.actionQuit = self.findChild(QtWidgets.QAction, "actionQuit")

        """ Connecting menu actions """
        self.actionNew.triggered.connect(self.new_session)
        self.actionQuit.triggered.connect(self.close)

        self.promptLabel = self.findChild(QtWidgets.QLabel, "promptLabel")

        self.imageLabel = DragAndDropLabel("assets/upload.png")
        self.imageLabel.triggered.connect(self.load_document)

        self.signWidget = SignWidget()
        self.signWidget.update.connect(self.insert_signature)

        self.scrollArea = self.findChild(QtWidgets.QScrollArea, "scrollArea")

        """ Defining buttons """
        self.setSelectionsButton = self.findChild(
            QtWidgets.QPushButton, "setPointsButton"
        )
        self.confirmButton = self.findChild(QtWidgets.QPushButton, "confirmButton")
        self.saveButton = self.findChild(QtWidgets.QPushButton, "saveButton")

        """ Connecting buttons """
        self.setSelectionsButton.clicked.connect(self.set_sign_areas)
        self.confirmButton.clicked.connect(self.ask_sign)
        self.saveButton.clicked.connect(self.save_pdf)

        self.setup()

        self.show()

    def setup(self):
        self.centralWidget().layout().insertWidget(1, self.imageLabel)
        self.confirmButton.hide()
        self.saveButton.hide()
        self.setSelectionsButton.hide()
        self.scrollArea.hide()

    def load_document(self, path: str):
        if path == "":
            path = QtWidgets.QFileDialog.getOpenFileName(
                self, "Open File", "~", "PDF (*.pdf)"
            )[0]
            if path == "":
                return
        if os.path.isfile(path):
            self.pdf_path = path
            mtypes = mimetypes.guess_type(path)
            if mtypes and "application/pdf" in mtypes:
                self.imageLabel.hide()
                self.promptLabel.hide()
                self.pdfViewerWidget = PdfViewerWidget(
                    path, self.settings, self.last_sing_positions
                )
                self.scrollArea.setWidget(self.pdfViewerWidget)
                self.scrollArea.show()
                if self.last_sing_positions is not None:
                    self.confirmButton.show()
                self.setSelectionsButton.show()

    def set_sign_areas(self):
        self.pdfViewerWidget.trigger_selection()
        if self.setSelectionsButton.text() != "Confirm sign points":
            self.setSelectionsButton.setText("Confirm sign points")
            self.confirmButton.hide()
        else:
            self.setSelectionsButton.setText("Set sign points")
            self.confirmButton.show()

    def ask_sign(self):
        self.signWidget.show()

    def insert_signature(self, sign: QtGui.QPixmap):
        coords = self.pdfViewerWidget.save_last_sign_positions()
        self.settings.setValue("lastSignPositions", coords)
        self.pdfViewerWidget.print_signature(sign)
        self.confirmButton.hide()
        self.setSelectionsButton.hide()
        self.saveButton.show()

    def save_pdf(self):
        images = self.pdfViewerWidget.get_pages_images()
        files = []
        pages = []
        for idx, image in enumerate(images):
            image: QtGui.QImage
            buffer = QtCore.QBuffer()
            buffer.open(QtCore.QBuffer.ReadWrite)
            image.save(buffer, "PNG")
            files.append(Image.open(io.BytesIO(bytes(buffer.data()))))
            # asd.append(f"tmp/{idx}.png")
        # images = [Image.open(f) for f in files]
        for idx, image in enumerate(files):
            pages.append(image.convert("RGB"))
        path = Path(self.pdf_path)
        path = f"{path.parent}/" + path.stem + "_signed" + path.suffix
        pages[0].save(
            path, "PDF", resolution=100.0, save_all=True, append_images=pages[1:]
        )
        success_message_box(
            f"Successfully saved signed PDF!\n"
            f"Check the original PDF folder:\n {path}"
        )

    def new_session(self):
        self.imageLabel.show()
        self.promptLabel.show()
        self.scrollArea.hide()
        self.confirmButton.hide()
        self.setSelectionsButton.hide()
        self.saveButton.hide()
        self.pdfViewerWidget.deleteLater()

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        if self.pdfViewerWidget is None:
            return
        coords = self.pdfViewerWidget.save_last_sign_positions()
        if not coords:
            return
        self.settings.setValue("lastSignPositions", coords)


class SignWidget(QtWidgets.QWidget):
    update = QtCore.pyqtSignal(QtGui.QPixmap, name="event")

    def __init__(self):
        super(SignWidget, self).__init__()
        uic.loadUi("assets/signwidget.ui", self)

        # Setup graphics view and scene
        self.graphicsView = self.findChild(QtWidgets.QGraphicsView, "graphicsView")
        self.scene = GraphicsScene(self, self.graphicsView.rect())
        self.graphicsView.setScene(self.scene)
        self.graphicsView.setStyleSheet("background: white;")

        # setup buttons
        self.confirmButton = self.findChild(QtWidgets.QPushButton, "confirmButton")
        self.confirmButton.clicked.connect(self.confirm_sign)
        self.cancelButton = self.findChild(QtWidgets.QPushButton, "cancelButton")
        self.cancelButton.clicked.connect(self.clear_and_close)

    def confirm_sign(self):
        bounding_rect = self.graphicsView.scene().itemsBoundingRect()
        self.graphicsView.scene().setSceneRect(bounding_rect)
        sign_pixmap = QtGui.QPixmap(bounding_rect.toRect().size())
        sign_pixmap.fill(Qt.transparent)
        pain = QtGui.QPainter(sign_pixmap)
        self.graphicsView.scene().render(
            pain, QtCore.QRectF(sign_pixmap.rect()), bounding_rect
        )
        pain.end()  # no more pain, lol
        self.update.emit(sign_pixmap)
        self.close()

    def clear_and_close(self):
        self.scene.clear()
        self.close()


class GraphicsScene(QtWidgets.QGraphicsScene):
    def __init__(self, parent: SignWidget, rect: QtCore.QRect):
        QtWidgets.QGraphicsScene.__init__(self, parent)
        self.setSceneRect(QtCore.QRectF(rect))

        self.lastMousePosition = None
        self.redBrush = QtGui.QBrush(Qt.red)
        self.blackPen = QtGui.QPen(Qt.black, 5.0)

        self.clearShortcut = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+D"), parent)
        self.clearShortcut.activated.connect(self.clear)

    def mousePressEvent(self, event: "QGraphicsSceneMouseEvent") -> None:
        self.lastMousePosition = event.scenePos()

    def mouseMoveEvent(self, event: "QGraphicsSceneMouseEvent") -> None:
        if self.lastMousePosition is None:
            return

        position = event.scenePos()
        if (position - self.lastMousePosition).manhattanLength() > MOUSE_THRESHOLD:
            self.addLine(QtCore.QLineF(self.lastMousePosition, position), self.blackPen)
            self.lastMousePosition = position

    def mouseReleaseEvent(self, event: "QGraphicsSceneMouseEvent") -> None:
        self.lastMousePosition = None


class DragAndDropLabel(QtWidgets.QLabel):
    triggered = QtCore.pyqtSignal(str)

    def __init__(self, image_path: str):
        super(DragAndDropLabel, self).__init__()
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
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
    def __init__(
        self, path: str, settings: QtCore.QSettings, last_sign_positions: list
    ):
        super(PdfViewerWidget, self).__init__()
        self.settings = settings
        self.mainLayout = QtWidgets.QVBoxLayout()
        self.pages = pdf2image.convert_from_path(path, 200)
        self.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)

        if not os.path.isdir("tmp"):
            os.mkdir("tmp")

        for idx, page in enumerate(self.pages):
            virtual_file = io.BytesIO()
            page.save(virtual_file, "PNG")
            virtual_file.seek(0)
            virtual_file = virtual_file.read()
            scene = PageGraphicsScene(self, virtual_file, idx, last_sign_positions)
            gview = PageGraphicsView(scene)
            self.mainLayout.addWidget(gview)

        self.setLayout(self.mainLayout)

    def trigger_selection(self):
        gviews = self.findChildren(PageGraphicsView)
        for gview in gviews:
            scene = gview.scene
            scene.trigger_selection()

    def print_signature(self, signature: QtGui.QPixmap):
        for gview in self.findChildren(PageGraphicsView):
            gview.scene.print_signature(signature)

    def get_pages_images(self):
        pages = []
        for gview in self.findChildren(PageGraphicsView):
            gview: PageGraphicsView
            image = QtGui.QImage(
                gview.scene.sceneRect().size().toSize(), QtGui.QImage.Format_ARGB32
            )
            image.fill(Qt.transparent)
            painter = QtGui.QPainter(image)
            gview.scene.render(painter)
            pages.append(image)
        return pages

    def save_last_sign_positions(self):
        gviews = self.findChildren(PageGraphicsView)
        coords = []
        for gview in gviews:
            coords += gview.scene.get_sign_positions()
        return coords


class PageGraphicsView(QtWidgets.QGraphicsView):
    def __init__(self, scene: QtWidgets.QGraphicsScene):
        super(PageGraphicsView, self).__init__()
        self.scene = scene

        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.setScene(self.scene)
        self.setMinimumHeight(ceil(self.scene.height()))


class PageGraphicsScene(QtWidgets.QGraphicsScene):
    def __init__(
        self,
        parent: QtWidgets.QWidget,
        image_bytes: bytes,
        page_number: int,
        last_sign_positions: list,
    ):
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
        pixmap = QtWidgets.QGraphicsPixmapItem(
            pixmap.scaledToWidth(self.parent.width(), Qt.SmoothTransformation)
        )
        self.addItem(pixmap)
        if last_sign_positions is None:
            return
        for position in last_sign_positions:
            page = position[0]
            rect_points = position[1]
            if page == self.page_number:
                first_point = QtCore.QPointF(rect_points[0], rect_points[1])
                last_point = QtCore.QPointF(rect_points[2], rect_points[3])
                self.addRect(
                    self.improved_rect(first_point, last_point),
                    brush=QtGui.QBrush(QtGui.QColor(0x0, 0x98, 0x3A, 120)),
                )

    def mousePressEvent(self, event: "QGraphicsSceneMouseEvent") -> None:
        # print(f"page: {self.page_number}, coord: {event.scenePos()}")
        if self.selectionFlag:
            self.mouse_origin = self.views()[0].mapFromScene(event.scenePos().toPoint())
            if self.rubberBand is None:
                self.rubberBand = QtWidgets.QRubberBand(
                    QtWidgets.QRubberBand.Rectangle, self.views()[0]
                )
            else:
                return
            self.rubberBand.setGeometry(QtCore.QRect(self.mouse_origin, QtCore.QSize()))
            self.rubberBand.show()

    def mouseMoveEvent(self, event: "QGraphicsSceneMouseEvent") -> None:
        if self.selectionFlag and self.rubberBand is not None:
            self.mouse_end = self.views()[0].mapFromScene(event.scenePos().toPoint())
            self.rubberBand.setGeometry(
                self.improved_rect(self.mouse_origin, self.mouse_end).toRect()
            )

    def mouseReleaseEvent(self, event: "QGraphicsSceneMouseEvent") -> None:
        if self.selectionFlag and self.rubberBand is not None:
            self.rubberBand.hide()
            self.rubberBand = None
            origin = self.views()[0].mapToScene(self.mouse_origin)
            end = self.views()[0].mapToScene(self.mouse_end)
            self.rect_fields.append(
                [
                    self.page_number,
                    self.addRect(
                        self.improved_rect(origin, end),
                        brush=QtGui.QBrush(QtGui.QColor(0x0, 0x98, 0x3A, 120)),
                    ),
                ]
            )

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

    def print_signature(self, signature: QtGui.QPixmap):
        for item in self.items():
            if isinstance(item, QtWidgets.QGraphicsRectItem):
                item: QtWidgets.QGraphicsRectItem
                coords = item.rect().getCoords()
                image = self.addPixmap(
                    signature.scaledToWidth(
                        item.rect().toRect().width(), Qt.SmoothTransformation
                    )
                )
                rect_height = coords[3] - coords[1]
                sign_height = image.boundingRect().toRect().height()
                y = coords[1] - (sign_height // 2) + (rect_height // 2)
                image.setPos(coords[0], y)
                self.removeItem(item)

    def get_sign_positions(self):
        coords = []
        for item in self.items():
            if isinstance(item, QtWidgets.QGraphicsRectItem):
                item: QtWidgets.QGraphicsRectItem
                coords.append([self.page_number, item.rect().getCoords()])
        return coords


def success_message_box(message: str):
    dialog = QtWidgets.QMessageBox()
    dialog.setIconPixmap(
        QtGui.QPixmap("assets/success.png").scaledToWidth(50, Qt.SmoothTransformation)
    )
    dialog.setText(message)
    dialog.setStandardButtons(QtWidgets.QMessageBox.Ok)
    dialog.exec_()


def main():
    if os.path.isdir("tmp"):
        shutil.rmtree("tmp")
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    app.exec()


if __name__ == "__main__":
    main()
