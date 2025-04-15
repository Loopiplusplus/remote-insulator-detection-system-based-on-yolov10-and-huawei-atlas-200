import sys
import socket
import json
from datetime import datetime
import os
import time  # 添加time模块
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, 
    QPushButton, QLabel, QTextEdit, QScrollArea, 
    QHBoxLayout, QGroupBox
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QFont

# 日志配置
LOG_DIR = "logs"
LOG_FILE = f"{LOG_DIR}/insulator_defects.log"

class DetectionThread(QThread):
    report_received = pyqtSignal(dict)
    status_updated = pyqtSignal(str)

    def __init__(self, port=12346):
        super().__init__()
        self.port = port
        self.running = True

    def run(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('0.0.0.0', self.port))
                s.listen(5)
                self.status_updated.emit(f"绝缘子检测服务监听中，端口：{self.port}")
    
                while self.running:
                    try:
                        # 设置accept的超时，这样可以定期检查self.running
                        s.settimeout(1.0)
                        try:
                            conn, addr = s.accept()
                        except socket.timeout:
                            continue  # 超时后检查self.running并重试
                        
                        with conn:
                            try:
                                # 增加接收超时设置
                                conn.settimeout(10.0)  # 增加超时时间
                                
                                # 安全接收数据
                                raw_data = b''
                                while True:
                                    try:
                                        chunk = conn.recv(4096)
                                        if not chunk:
                                            break
                                        raw_data += chunk
                                        # 增加数据长度检查防止溢出
                                        if len(raw_data) > 10 * 1024 * 1024:  # 限制10MB
                                            raise ValueError("接收数据过大")
                                    except socket.timeout:
                                        # 接收超时，可能是数据已经全部接收
                                        break
    
                                if b'INSULATOR_REPORT:' in raw_data:
                                    try:
                                        header, payload = raw_data.split(b'|', 1)
                                        length = int(header.split(b':')[1])
                                        
                                        if len(payload) == length:
                                            report = json.loads(payload.decode('utf-8'))
                                            if report.get('header') == 'insulator_error':
                                                self.report_received.emit(report)
                                                self.save_report(report)
                                    except (ValueError, json.JSONDecodeError) as e:
                                        self.status_updated.emit(f"数据解析错误: {str(e)}")
                            except Exception as e:
                                self.status_updated.emit(f"连接处理异常: {str(e)}")
                    except socket.timeout:
                        # accept超时，继续循环
                        continue
                    except Exception as e:
                        if self.running:  # 只有在线程仍在运行时才报告错误
                            self.status_updated.emit(f"服务异常: {str(e)}")
                            # 短暂休眠以避免错误循环过快
                            time.sleep(1)
        
        except Exception as e:
            self.status_updated.emit(f"严重错误: {str(e)}")

    def save_report(self, report):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = f"{LOG_DIR}/report_{timestamp}.json"
            
            os.makedirs(LOG_DIR, exist_ok=True)
            
            # 保存JSON报告
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            # 将详细信息追加到日志文件
            with open(LOG_FILE, 'a', encoding='utf-8') as log_f:
                log_f.write(f"\n====== 检测报告 {timestamp} ======\n")
                if report['count'] == 0:
                    log_f.write("未检测到缺陷绝缘子\n")
                else:
                    log_f.write(f"缺陷图片总数：{report['count']}\n")
                    for detail in report['defect_details']:
                        log_f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO - 文件：{detail['filename']}\n")
                        log_f.write(f"缺陷数量：{detail['defect_count']}\n")
                        for i, defect in enumerate(detail['defects']):
                            log_f.write(f"缺陷{i+1}：置信度 {defect['confidence']:.2f} 位置 {defect['bbox']}\n")
                    log_f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO - 报告已保存至 {report_file}\n")
            
            self.status_updated.emit(f"报告已保存至 {report_file}")
        except Exception as e:
            self.status_updated.emit(f"报告保存失败: {str(e)}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("绝缘子缺陷检测系统")
        self.setGeometry(100, 100, 800, 600)
        
        # 主布局
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        
        # 标题
        title = QLabel("绝缘子缺陷检测系统")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        # 控制面板
        control_group = QGroupBox("控制面板")
        control_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("开始检测")
        self.start_btn.setStyleSheet(
            "QPushButton {background-color: #4CAF50; color: white; padding: 10px;}"
            "QPushButton:hover {background-color: #45a049;}"
        )
        self.start_btn.clicked.connect(self.start_detection)
        control_layout.addWidget(self.start_btn)
        
        control_group.setLayout(control_layout)
        main_layout.addWidget(control_group)
        
        # 结果显示区域
        result_group = QGroupBox("检测结果")
        result_layout = QVBoxLayout()
        
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setStyleSheet("background-color: #f8f9fa;")
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.result_text)
        
        result_layout.addWidget(scroll)
        result_group.setLayout(result_layout)
        main_layout.addWidget(result_group)
        
        # 状态栏
        self.status_label = QLabel("准备就绪")
        self.status_label.setStyleSheet("color: #666; font-style: italic;")
        main_layout.addWidget(self.status_label)
        
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # 启动检测线程
        self.detection_thread = DetectionThread()
        self.detection_thread.report_received.connect(self.display_report)
        self.detection_thread.status_updated.connect(self.update_status)
        self.detection_thread.start()
        
        # 添加一个标志来跟踪检测状态
        self.detection_in_progress = False

    def start_detection(self):
        # 如果已经在检测中，则不执行新的检测
        if self.detection_in_progress:
            self.update_status("检测正在进行中，请稍候...")
            return
            
        try:
            self.detection_in_progress = True
            self.start_btn.setEnabled(False)  # 禁用按钮防止重复点击
            self.update_status("正在发送检测请求...")
            
            # 创建一个单独的线程来处理网络请求，避免阻塞UI
            class RequestThread(QThread):
                request_completed = pyqtSignal(bool, str)
                
                def run(self):
                    try:
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                            s.settimeout(5.0)  # 设置超时
                            s.connect(('192.168.137.2', 12345))
                            s.sendall('START_DETECTION'.encode('utf-8'))
                            self.request_completed.emit(True, "已发送检测请求，等待结果...")
                    except socket.timeout:
                        self.request_completed.emit(False, "发送检测请求超时，请检查网络连接")
                    except Exception as e:
                        self.request_completed.emit(False, f"发送检测请求失败: {str(e)}")
            
            # 创建并启动请求线程
            self.request_thread = RequestThread()
            self.request_thread.request_completed.connect(self.handle_request_result)
            self.request_thread.start()
            
        except Exception as e:
            self.update_status(f"启动检测请求失败: {str(e)}")
            self.detection_in_progress = False
            self.start_btn.setEnabled(True)  # 重新启用按钮
    
    def handle_request_result(self, success, message):
        # 处理请求线程的结果
        self.update_status(message)
        
        if not success:
            # 如果请求失败，重置状态
            self.detection_in_progress = False
            self.start_btn.setEnabled(True)
            
        # 确保线程被正确清理
        if hasattr(self, 'request_thread'):
            self.request_thread.deleteLater()

    def display_report(self, report):
        try:
            self.result_text.clear()
            
            if report['count'] == 0:
                self.result_text.append("未检测到缺陷绝缘子")
            else:
                self.result_text.append("====== 绝缘子缺陷报告 ======")
                self.result_text.append(f"缺陷图片总数：{report['count']}\n")
                
                for detail in report['defect_details']:
                    self.result_text.append(f"文件：{detail['filename']}")
                    self.result_text.append(f"缺陷数量：{detail['defect_count']}")
                    
                    for i, defect in enumerate(detail['defects']):
                        self.result_text.append(
                            f"缺陷{i+1}：置信度 {defect['confidence']:.2f} 位置 {defect['bbox']}"
                        )
                    self.result_text.append("")
            
            # 重置检测状态，允许再次检测
            self.detection_in_progress = False
            self.start_btn.setEnabled(True)  # 重新启用按钮
            self.update_status("检测完成")
        except Exception as e:
            self.update_status(f"显示报告异常: {str(e)}")
            self.detection_in_progress = False
            self.start_btn.setEnabled(True)  # 重新启用按钮

    def update_status(self, message):
        self.status_label.setText(message)
        
    def closeEvent(self, event):
        try:
            # 确保线程正确退出
            self.detection_thread.running = False
            self.detection_thread.quit()
            self.detection_thread.wait(1000)
            event.accept()
        except Exception as e:
            print(f"关闭窗口异常: {str(e)}")
            event.accept()

if __name__ == '__main__':
    try:
        app = QApplication(sys.argv)
        app.setStyle('Fusion')
        
        window = MainWindow()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"程序异常: {str(e)}")
        # 记录异常到日志文件
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(f"{LOG_DIR}/error.log", 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now()}] 程序异常: {str(e)}\n")