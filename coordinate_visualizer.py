import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox)
from PyQt5.QtGui import QPainter, QPen, QColor
from PyQt5.QtCore import Qt

class CoordinateVisualizer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.points = []  # 存储所有坐标点
        self.initUI()

    def initUI(self):
        self.setWindowTitle('坐标可视化系统')
        self.setGeometry(100, 100, 800, 900)  # 窗口大小

        # 创建中心部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # 创建输入区域
        input_widget = QWidget()
        input_layout = QHBoxLayout(input_widget)

        # X坐标输入
        input_layout.addWidget(QLabel('X坐标 (mm):'))
        self.x_input = QLineEdit()
        input_layout.addWidget(self.x_input)

        # Y坐标输入
        input_layout.addWidget(QLabel('Y坐标 (mm):'))
        self.y_input = QLineEdit()
        input_layout.addWidget(self.y_input)

        # 添加按钮
        add_button = QPushButton('添加坐标点')
        add_button.clicked.connect(self.add_point)
        input_layout.addWidget(add_button)

        # 清除按钮
        clear_button = QPushButton('清除所有点')
        clear_button.clicked.connect(self.clear_points)
        input_layout.addWidget(clear_button)

        layout.addWidget(input_widget)

        # 创建绘图区域
        self.canvas = Canvas(self)
        layout.addWidget(self.canvas)

    def add_point(self):
        try:
            x = float(self.x_input.text())
            y = float(self.y_input.text())
            
            # 检查坐标是否在有效范围内
            if 0 <= x <= 4000 and 0 <= y <= 4000:
                self.points.append((x, y))
                self.canvas.points = self.points
                self.canvas.update()
                self.x_input.clear()
                self.y_input.clear()
            else:
                QMessageBox.warning(self, '错误', '坐标必须在0-4000mm范围内！')
        except ValueError:
            QMessageBox.warning(self, '错误', '请输入有效的数字！')

    def clear_points(self):
        self.points.clear()
        self.canvas.points = []
        self.canvas.update()

class Canvas(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.points = []
        self.grid_size = 100  # 网格大小（mm）
        self.margin = 50      # 画布边距
        self.setMinimumSize(900, 900)  # 设置更大最小大小

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 计算缩放比例（考虑边距）
        draw_width = self.width() - 2 * self.margin
        draw_height = self.height() - 2 * self.margin
        scale = min(draw_width, draw_height) / 4000
        grid_length = int(4000 * scale)
        left = self.margin
        top = self.margin
        right = left + grid_length
        bottom = top + grid_length

        # 绘制网格
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        for i in range(0, 4001, self.grid_size):
            x = int(left + i * scale)
            painter.drawLine(x, top, x, bottom)
            y = int(top + i * scale)
            painter.drawLine(left, y, right, y)

        # 绘制坐标轴
        axis_pen = QPen(Qt.black, 3)
        painter.setPen(axis_pen)
        painter.drawLine(left, bottom, right, bottom)  # X轴
        painter.drawLine(left, top, left, bottom)      # Y轴

        # 绘制坐标轴刻度和数字
        font = painter.font()
        font.setPointSize(12)
        painter.setFont(font)
        painter.setPen(QPen(Qt.black, 2))
        # X轴刻度
        for i in range(0, 4001, 1000):
            x = int(left + i * scale)
            y = bottom
            painter.drawLine(x, y-7, x, y+7)
            # 4000刻度往左缩20像素，0刻度往右缩10像素
            if i == 0:
                painter.drawText(x-5, y+25, 30, 20, Qt.AlignLeft, str(i))  # 上移10像素
            elif i == 4000:
                painter.drawText(x-25, y+25, 30, 20, Qt.AlignRight, str(i))  # 上移10像素
            else:
                painter.drawText(x-15, y+25, 30, 20, Qt.AlignCenter, str(i))  # 上移10像素
        # Y轴刻度
        for i in range(0, 4001, 1000):
            x = left
            y = int(top + (4000 - i) * scale)
            painter.drawLine(x-7, y, x+7, y)
            # 4000刻度往下缩10像素，0刻度往上缩10像素
            if i == 0:
                painter.drawText(x-55, y-10, 40, 20, Qt.AlignRight|Qt.AlignVCenter, str(i))
            elif i == 4000:
                painter.drawText(x-55, y+5, 40, 20, Qt.AlignRight|Qt.AlignVCenter, str(i))
            else:
                painter.drawText(x-55, y-10, 40, 20, Qt.AlignRight|Qt.AlignVCenter, str(i))
        # XY标识远离刻度
        painter.setPen(QPen(Qt.blue, 2))
        painter.setFont(font)
        painter.drawText(right+15, bottom+10, 30, 20, Qt.AlignLeft|Qt.AlignVCenter, "X")
        painter.drawText(left-30, top-20, 20, 20, Qt.AlignLeft|Qt.AlignVCenter, "Y")

        # 绘制坐标点
        painter.setPen(QPen(Qt.red, 6))
        for point in self.points:
            x = int(left + point[0] * scale)
            y = int(top + (4000 - point[1]) * scale)
            painter.drawPoint(x, y)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = CoordinateVisualizer()
    window.show()
    sys.exit(app.exec_())
