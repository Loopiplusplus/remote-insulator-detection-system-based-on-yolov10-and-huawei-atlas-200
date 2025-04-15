# 开发板端程序
import os
import json
import socket
import numpy as np
import cv2
import torch
from ais_bench.infer.interface import InferSession


class EdgeDetectionServer:
    def __init__(self, host='0.0.0.0', port=12345):
        self.host = host
        self.port = port
        # 加载OM模型，使用InferSession替代onnxruntime
        self.model_path = 'yolov10s_insulator.om'
        self.session = InferSession(0, self.model_path)  # 0表示设备ID
        self.DEFECT_CLASS_ID = 0
        self.CONFIDENCE_THRESHOLD = 0.5
        self.IOU_THRESHOLD = 0.45
        self.input_shape = [640, 640]

    def preprocess_image(self, img_path, target_size=640):
        # 读取图像
        img = cv2.imread(img_path)
        # 图像预处理
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (target_size, target_size))
        img = img.astype(np.float32) / 255.0
        img = np.transpose(img, (2, 0, 1))  # HWC转CHW
        img = np.ascontiguousarray(img, dtype=np.float16)  # 转换为float16类型
        img = np.expand_dims(img, axis=0)  # 添加batch维度
        return img, img.shape

    def nms(self, prediction, conf_thres=0.5, iou_thres=0.45):
        """非极大值抑制处理 - 自定义实现，不依赖torchvision"""
        # 转换为numpy数组处理
        if isinstance(prediction, torch.Tensor):
            prediction = prediction.numpy()

        # 获取置信度大于阈值的索引
        mask = prediction[..., 4] > conf_thres
        if not np.any(mask):
            return [None]

        # 筛选出高置信度的检测框
        x = prediction[mask]

        # 按置信度排序（降序）
        indices = np.argsort(-x[:, 4])
        x = x[indices]

        # 执行NMS
        keep = []
        while len(x) > 0:
            keep.append(x[0])
            if len(x) == 1:
                break

            # 计算IoU
            box1 = x[0, :4]
            boxes = x[1:, :4]

            # 计算交集区域
            xx1 = np.maximum(box1[0], boxes[:, 0])
            yy1 = np.maximum(box1[1], boxes[:, 1])
            xx2 = np.minimum(box1[2], boxes[:, 2])
            yy2 = np.minimum(box1[3], boxes[:, 3])

            w = np.maximum(0, xx2 - xx1)
            h = np.maximum(0, yy2 - yy1)
            inter = w * h

            # 计算并集区域
            area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
            area2 = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
            union = area1 + area2 - inter

            # 计算IoU
            iou = inter / (union + 1e-16)

            # 保留IoU小于阈值的框
            inds = np.where(iou <= iou_thres)[0]
            x = x[inds + 1]

        return [np.array(keep) if keep else None]

    def detect_defects(self, input_dir='testphoto/input'):
        fault_data = {
            'header': 'insulator_error',
            'count': 0,
            'defect_details': []
        }

        for filename in os.listdir(input_dir):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                img_path = os.path.join(input_dir, filename)
                try:
                    # 预处理图像
                    img, _ = self.preprocess_image(img_path)

                    # 运行推理
                    outputs = self.session.infer([img])[0]

                    # 非极大值抑制后处理
                    boxout = self.nms(outputs, conf_thres=self.CONFIDENCE_THRESHOLD, iou_thres=self.IOU_THRESHOLD)

                    if boxout[0] is not None:
                        pred_all = boxout[0]

                        # 收集当前图片的缺陷信息
                        defect_boxes = []
                        for det in pred_all:
                            if det[5] == self.DEFECT_CLASS_ID and det[4] >= self.CONFIDENCE_THRESHOLD:
                                # 获取原始图像尺寸用于坐标转换
                                original_img = cv2.imread(img_path)
                                orig_h, orig_w = original_img.shape[:2]

                                # 转换坐标到原始图像尺寸
                                x1 = int(det[0] * orig_w / 640)
                                y1 = int(det[1] * orig_h / 640)
                                x2 = int(det[2] * orig_w / 640)
                                y2 = int(det[3] * orig_h / 640)

                                defect_boxes.append({
                                    'bbox': [x1, y1, x2, y2],
                                    'confidence': float(det[4])
                                })

                        # 如果有检测到缺陷，添加到报告中
                        if defect_boxes:
                            fault_data['count'] += 1
                            fault_data['defect_details'].append({
                                'filename': filename,
                                'defect_count': len(defect_boxes),
                                'defects': defect_boxes
                            })
                            print(f"在图片 {filename} 中检测到 {len(defect_boxes)} 个缺陷")

                except Exception as e:
                    print(f"处理图像 {filename} 时出错: {str(e)}")
                    continue

        return fault_data

    def start_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.host, self.port))
            s.listen(1)
            print(f"边缘检测服务已启动，监听端口：{self.port}")

            while True:
                conn, addr = s.accept()
                with conn:
                    try:
                        # 接收触发信号
                        trigger = conn.recv(1024).decode('utf-8')
                        if trigger == 'START_DETECTION':
                            print("收到检测请求，开始检测...")
                            report = self.detect_defects()

                            # 检查报告大小
                            payload = json.dumps(report).encode('utf-8')
                            if len(payload) > 5 * 1024 * 1024:  # 限制5MB
                                raise ValueError("生成报告过大")

                            try:
                                # 分块发送数据
                                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as response_socket:
                                    response_socket.settimeout(5.0)
                                    print(f"尝试连接到 192.168.137.1...")
                                    response_socket.connect(('192.168.137.1', 12346))
                                    header = f"INSULATOR_REPORT:{len(payload)}|".encode()
                                    response_socket.sendall(header)
                                    response_socket.sendall(payload)
                                    print(f"检测完成，已发送报告（{len(payload)}字节）")
                            except ConnectionRefusedError:
                                print("警告：无法连接到接收服务器(192.168.137.1:12346)，请确保接收服务已启动")
                                # 将结果保存到本地文件作为备份
                                with open('detection_report.json', 'w', encoding='utf-8') as f:
                                    json.dump(report, f, ensure_ascii=False, indent=2)
                                print(f"检测报告已保存到本地文件: detection_report.json")
                            except Exception as e:
                                print(f"发送报告时出错: {str(e)}")
                                # 将结果保存到本地文件作为备份
                                with open('detection_report.json', 'w', encoding='utf-8') as f:
                                    json.dump(report, f, ensure_ascii=False, indent=2)
                                print(f"检测报告已保存到本地文件: detection_report.json")
                    except Exception as e:
                        print(f"处理异常：{str(e)}")


if __name__ == '__main__':
    server = EdgeDetectionServer()
    server.start_server()

