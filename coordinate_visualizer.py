import sys
import threading
import re
import serial
import serial.tools.list_ports  # 新增串口枚举
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QLabel, QComboBox, QFrame, QTextEdit, QGroupBox)
from PyQt5.QtGui import QPainter, QPen, QColor, QFont
from PyQt5.QtCore import Qt, pyqtSignal

class CoordinateVisualizer(QMainWindow):
    new_point_signal = pyqtSignal(float, float)
    status_update_signal = pyqtSignal(str, str)  # 状态区信号：串口、坐标/异常
    def __init__(self):
        super().__init__()
        self.points = []
        self.serial_thread = None
        self.serial_port = None
        self.baudrate = 115200
        self.ser = None
        self.initUI()
        self.new_point_signal.connect(self.add_point_from_serial)
        self.status_update_signal.connect(self.update_status)
        self.start_serial_thread()

    def get_available_ports(self):
        return [port.device for port in serial.tools.list_ports.comports()]

    def on_port_changed(self, port):
        self.serial_port = port
        self.error_label.setText("")  # 切换串口时清空错误
        self.status_update_signal.emit(f"串口: {port} 波特率: {self.baudrate}", "等待数据...")
        self.start_serial_thread()

    def on_baudrate_changed(self, baud):
        self.baudrate = int(baud)
        self.status_update_signal.emit(f"串口: {self.serial_port} 波特率: {self.baudrate}", "等待数据...")
        self.start_serial_thread()

    def start_serial_thread(self):
        if hasattr(self, 'ser') and self.ser:
            try:
                self.ser.close()
            except Exception:
                pass
        def serial_worker():
            while True:
                try:
                    if not self.serial_port:
                        return
                    self.ser = serial.Serial(self.serial_port, self.baudrate, timeout=1)
                    buffer = ''
                    while True:
                        data = self.ser.read(self.ser.in_waiting or 1).decode(errors='ignore')
                        if data:
                            buffer += data
                            for match in re.finditer(r'distance\[(\d+),(\d+)\]', buffer):
                                x, y = float(match.group(1)), float(match.group(2))
                                self.new_point_signal.emit(x, y)
                                self.status_update_signal.emit(f"串口: {self.serial_port} 波特率: {self.baudrate}", f"坐标: ({int(x)}, {int(y)})")
                            buffer = re.sub(r'distance\[(\d+),(\d+)\]', '', buffer)
                except Exception as e:
                    self.error_signal.emit(str(e))
                    import time
                    time.sleep(2)  # 等待2秒后重试
                else:
                    break
        self.serial_thread = threading.Thread(target=serial_worker, daemon=True)
        self.serial_thread.start()

    # 新增错误信号和处理
    from PyQt5.QtCore import pyqtSignal as _pyqtSignal
    error_signal = _pyqtSignal(str)
    def show_error(self, msg):
        self.error_label.setText(f"错误: {msg}")

    def add_point_from_serial(self, x, y):
        if 0 <= x <= 4000 and 0 <= y <= 4000:
            self.points = [(x, y)]
            self.canvas.points = self.points
            self.canvas.update()
        else:
            self.status_update_signal.emit(f"串口: {self.serial_port} 波特率: {self.baudrate}", f"警告: 坐标越界 ({x},{y})")

    def update_status(self, port_text, info_text):
        self.port_status.setText(port_text)
        self.info_status.setText(info_text)

    def initUI(self):
        self.setWindowTitle('CAR PLACE')
        self.setGeometry(100, 100, 900, 950)
        # 全局字体设置为思源黑体，找不到则用系统无衬线
        app_font = QFont("Source Han Sans SC", 12)
        QApplication.setFont(app_font)
        self.setStyleSheet("QMainWindow{background:#F5F5F5;}")
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(20)

        # 顶部：串口选择区
        top_frame = QFrame()
        top_frame.setFrameShape(QFrame.StyledPanel)
        top_frame.setStyleSheet("QFrame{background:#fff;border-bottom:1px solid #ECECEC;}")
        top_layout = QHBoxLayout(top_frame)
        top_layout.setContentsMargins(16, 8, 16, 8)
        top_layout.setSpacing(16)
        port_label = QLabel('串口选择:')
        port_label.setFont(QFont("Source Han Sans SC", 14))
        self.port_combo = QComboBox()
        self.port_combo.setFont(QFont("Source Han Sans SC", 13))
        self.port_combo.setStyleSheet("QComboBox{min-width:120px;}")
        ports = self.get_available_ports()
        self.port_combo.addItems(ports)
        if ports:
            self.serial_port = ports[0]
        self.port_combo.currentTextChanged.connect(self.on_port_changed)
        # 新增波特率选择
        baud_label = QLabel('波特率:')
        baud_label.setFont(QFont("Source Han Sans SC", 14))
        self.baud_combo = QComboBox()
        self.baud_combo.setFont(QFont("Source Han Sans SC", 13))
        self.baud_combo.setStyleSheet("QComboBox{min-width:100px;}")
        baudrates = ["9600", "19200", "38400", "57600", "115200", "230400", "460800", "921600"]
        self.baud_combo.addItems(baudrates)
        self.baud_combo.setCurrentText(str(self.baudrate))
        self.baud_combo.currentTextChanged.connect(self.on_baudrate_changed)
        top_layout.addWidget(port_label)
        top_layout.addWidget(self.port_combo)
        top_layout.addWidget(baud_label)
        top_layout.addWidget(self.baud_combo)
        # 新增错误信息标签
        self.error_label = QLabel("")
        self.error_label.setFont(QFont("Source Han Sans SC", 12))
        self.error_label.setStyleSheet('color:#FF5722;')
        top_layout.addWidget(self.error_label)
        top_layout.addStretch(1)
        main_layout.addWidget(top_frame, stretch=1)

        # 中部：主显示区
        mid_frame = QFrame()
        mid_frame.setObjectName('MainCanvas')
        mid_frame.setStyleSheet("""
            QFrame#MainCanvas {
                background: #fff;
                border: 1px solid #ECECEC;
                border-radius: 8px;
            }
        """)
        mid_layout = QVBoxLayout(mid_frame)
        mid_layout.setContentsMargins(0, 0, 0, 0)
        self.canvas = Canvas(self)
        mid_layout.addWidget(self.canvas)
        main_layout.addWidget(mid_frame, stretch=7)

        # 底部：状态区
        bottom_frame = QFrame()
        bottom_frame.setFrameShape(QFrame.StyledPanel)
        bottom_frame.setStyleSheet("QFrame{background:#fff;border-top:1px solid #ECECEC;}")
        bottom_layout = QHBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(16, 8, 16, 8)
        bottom_layout.setSpacing(24)
        self.port_status = QLabel('串口: 未连接')
        self.port_status.setFont(QFont("Source Han Sans SC", 13))
        self.info_status = QLabel('等待数据...')
        self.info_status.setFont(QFont("Source Han Sans SC", 13))
        self.info_status.setStyleSheet('color:#666;')
        bottom_layout.addWidget(self.port_status)
        bottom_layout.addWidget(self.info_status)
        bottom_layout.addStretch(1)
        main_layout.addWidget(bottom_frame, stretch=2)

        # 新增右侧控件区（错误信息输出+串口信息发送区）
        # 只在initUI中添加控件布局，功能实现可后续补充
        # 先移除原有的右侧控件区插入逻辑，改为主区和右区并排
        # 1. 取出主显示区和底部区
        main_layout = self.centralWidget().layout() if hasattr(self.centralWidget(), 'layout') else None
        if main_layout:
            # 取出主显示区和底部区
            mid_frame_item = main_layout.takeAt(1)
            bottom_frame_item = main_layout.takeAt(1)
            # 创建主区竖直布局
            main_vbox = QVBoxLayout()
            main_vbox.addWidget(mid_frame_item.widget())
            main_vbox.addWidget(bottom_frame_item.widget())
            main_vbox.setStretch(0, 7)
            main_vbox.setStretch(1, 2)
            # 创建右侧竖直布局
            right_panel = QVBoxLayout()
            self.error_output_box = QTextEdit()
            self.error_output_box.setReadOnly(True)
            self.error_output_box.setStyleSheet('background:#FFF8F0;color:#D32F2F;font-size:14px;border:1px solid #FFD6C8;border-radius:6px;')
            self.error_output_box.setFixedHeight(80)
            error_group = QGroupBox('错误信息输出')
            error_group.setLayout(QVBoxLayout())
            error_group.layout().addWidget(self.error_output_box)
            right_panel.addWidget(error_group)
            self.serial_send_box = QTextEdit()
            self.serial_send_box.setReadOnly(True)
            self.serial_send_box.setStyleSheet('background:#F5F5F5;color:#333;font-size:13px;border:1px solid #ECECEC;border-radius:6px;')
            self.serial_send_box.setFixedHeight(120)
            send_group = QGroupBox('串口信息发送区')
            send_group.setLayout(QVBoxLayout())
            send_group.layout().addWidget(self.serial_send_box)
            right_panel.addWidget(send_group)
            right_panel.addStretch(1)
            # 创建横向布局并加入主区和右区
            hbox = QHBoxLayout()
            hbox.addLayout(main_vbox, stretch=7)
            hbox.addLayout(right_panel, stretch=3)
            # 清空main_layout并加入hbox
            while main_layout.count():
                main_layout.takeAt(0)
            main_layout.addLayout(hbox)

        # 立即刷新串口状态
        if ports:
            self.status_update_signal.emit(f"串口: {ports[0]}", "等待数据...")
        else:
            self.status_update_signal.emit("串口: 未检测到串口", "请检查设备连接")

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

        # 地雷区参数
        outer_diameter = 1000
        inner_diameter = 260
        outer_radius = outer_diameter / 2
        inner_radius = inner_diameter / 2
        mine_centers = [(1000, 2000), (2000, 2000), (3000, 2000)]

        # 绘制地雷区（三个双圆环，均匀分布在x=500~3500区间中轴线上）
        for cx, cy in mine_centers:
            center_x = int(left + cx * scale)
            center_y = int(top + (4000 - cy) * scale)
            # 外环（警示区）
            painter.setPen(QPen(QColor(255, 140, 0, 180), 6))
            painter.setBrush(QColor(255, 200, 0, 60))
            painter.drawEllipse(center_x - int(outer_radius*scale), center_y - int(outer_radius*scale), int(outer_diameter*scale), int(outer_diameter*scale))
            # 内环（地雷区）
            painter.setPen(QPen(QColor(200, 0, 0, 220), 4))
            painter.setBrush(QColor(200, 0, 0, 120))
            painter.drawEllipse(center_x - int(inner_radius*scale), center_y - int(inner_radius*scale), int(inner_diameter*scale), int(inner_diameter*scale))
            painter.setBrush(Qt.NoBrush)

        # 绘制目标点（方框）和传感器点，颜色根据与地雷区关系动态变化
        for point in self.points:
            px, py = point
            # 目标框参数
            rect_w = 150 * scale
            rect_h = 80 * scale
            rect_x = left + (px - 75) * scale
            rect_y = top + (4000 - py - 40) * scale
            rect_cx = rect_x + rect_w / 2
            rect_cy = rect_y + rect_h / 2
            # 检查与地雷区关系
            status = 'safe'  # 默认安全
            for cx, cy in mine_centers:
                # 圆心像素坐标
                mine_cx = left + cx * scale
                mine_cy = top + (4000 - cy) * scale
                # 计算矩形与圆的最近距离
                dx = abs(mine_cx - rect_cx)
                dy = abs(mine_cy - rect_cy)
                closest_x = max(dx - rect_w/2, 0)
                closest_y = max(dy - rect_h/2, 0)
                dist = (closest_x**2 + closest_y**2) ** 0.5
                # 先判地雷
                if dist <= inner_radius * scale:
                    status = 'mine'
                    break
                # 再判地雷区
                elif dist <= outer_radius * scale:
                    status = 'warning'
            # 颜色选择
            if status == 'mine':
                box_pen = QPen(QColor(220, 0, 0), 4)
                box_brush = QColor(220, 0, 0, 60)
            elif status == 'warning':
                box_pen = QPen(QColor(255, 200, 0), 4)
                box_brush = QColor(255, 200, 0, 60)
            else:
                box_pen = QPen(QColor(0, 180, 0), 4)
                box_brush = QColor(0, 180, 0, 60)
            # 绘制目标框
            painter.setPen(box_pen)
            painter.setBrush(box_brush)
            painter.drawRect(int(rect_x), int(rect_y), int(rect_w), int(rect_h))
            # 传感器点（相对框左上角偏移120,40）
            sensor_x = rect_x + 120 * scale
            sensor_y = rect_y + 40 * scale
            painter.setBrush(QColor(0, 120, 255))
            painter.setPen(QPen(QColor(0, 120, 255), 2))
            painter.drawEllipse(int(sensor_x-6), int(sensor_y-6), 12, 12)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(Qt.red, 6))

        # 移除起点①和终点②的所有徽标，仅保留出生区域矩形
        # 不再绘制①②圆圈、数字、半透明数字等
        # 只保留出生区域矩形
        painter.setPen(QPen(QColor(0, 180, 255), 3, Qt.DashLine))
        painter.setBrush(QColor(0, 180, 255, 40))
        painter.drawRect(int(left), int(top), int(630*scale), int(420*scale))
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(255, 180, 0), 3, Qt.DashLine))
        painter.setBrush(QColor(255, 180, 0, 40))
        painter.drawRect(int(right-630*scale), int(bottom-420*scale), int(630*scale), int(420*scale))
        painter.setBrush(Qt.NoBrush)

        # 在1、2出生区域的矩形内部完全居中添加半透明大号数字1、2
        painter.setFont(QFont("Source Han Sans SC", int(80*scale), QFont.Bold))
        painter.setPen(QPen(QColor(0, 0, 0, 80), 1))
        # 1 区域内部居中
        one_rect_left = left
        one_rect_top = top
        one_rect_w = 630 * scale
        one_rect_h = 420 * scale
        painter.drawText(int(one_rect_left), int(one_rect_top), int(one_rect_w), int(one_rect_h), Qt.AlignCenter, "1")
        # 2 区域内部居中
        two_rect_left = right - 630 * scale
        two_rect_top = bottom - 420 * scale
        two_rect_w = 630 * scale
        two_rect_h = 420 * scale
        painter.drawText(int(two_rect_left), int(two_rect_top), int(two_rect_w), int(two_rect_h), Qt.AlignCenter, "2")

        # 绘制地雷区（三个双圆环，均匀分布在x=500~3500区间中轴线上）
        outer_diameter = 1000
        inner_diameter = 260
        outer_radius = outer_diameter / 2
        # 圆心分别为x=500+500=1000, 2000, 3500-500=3000
        mine_centers = [(1000, 2000), (2000, 2000), (3000, 2000)]
        for cx, cy in mine_centers:
            center_x = int(left + cx * scale)
            center_y = int(top + (4000 - cy) * scale)
            # 外环（警示区）
            painter.setPen(QPen(QColor(255, 140, 0, 180), 6))
            painter.setBrush(QColor(255, 200, 0, 60))
            painter.drawEllipse(center_x - int(outer_diameter/2*scale), center_y - int(outer_diameter/2*scale), int(outer_diameter*scale), int(outer_diameter*scale))
            # 内环（地雷区）
            painter.setPen(QPen(QColor(200, 0, 0, 220), 4))
            painter.setBrush(QColor(200, 0, 0, 120))
            painter.drawEllipse(center_x - int(inner_diameter/2*scale), center_y - int(inner_diameter/2*scale), int(inner_diameter*scale), int(inner_diameter*scale))
            painter.setBrush(Qt.NoBrush)

if __name__ == '__main__':
    try:
        app = QApplication(sys.argv)
        window = CoordinateVisualizer()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        print("[FATAL ERROR]", e)
        import traceback
        traceback.print_exc()
        input("按回车退出")
