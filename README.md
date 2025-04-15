# **基于YOLOv10与华为Atlas 200的远程绝缘子检测系统**

​	本项目是YOLOv10s.pt预训练模型，经过绝缘子数据集训练得到绝缘子检测模型后。利用华为atc工具包转化为.om模型后，在图像数据预处理后，使用华为NPU提供的Api进行模型推理得到检测结果。并对结果进行nms处理和坐标信息后处理得到绝缘子错误信息。
​	系统本身由电脑本机(假设为服务器端)、开发板组成(边缘端)。电脑本机通过TCP报文向边缘设备发送检测信息，再由边缘设备检测后打包检测内容进入TCP报文信息并发送给本机来模拟电力应用中边缘设备与服务器间的交互。

​	本项目数据集来源：[基于YOLOv5网络的输配电线路故障检测_数据集-飞桨AI Studio星河社区 (baidu.com)](https://aistudio.baidu.com/datasetdetail/270697/0)

​	数据集项目Github地址：[Insulator_defect-nest_detection/ at main · lcd955/Insulator_defect-nest_detection (github.com)](https://github.com/lcd955/Insulator_defect-nest_detection/tree/main)

​	数据集百度网盘链接: https://pan.baidu.com/s/1nLjJ7KOoMmVEAeifSlx-zQ?pwd=keza 提取码: keza 

**项目结构**：

trained_weights:已训练好的模型权重

predict_phots.py:边缘设备检测程序

receive_error.py:本机接收程序

train_v10.py:训练文件

train_val_split.py:数据集划分程序

trans.py:.pt转.onnx程序

**项目效果:**

![img](photos/image1.png)