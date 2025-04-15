#coding:utf-8
from ultralytics import YOLOv10
# 模型配置文件
model_yaml_path = "ultralytics/cfg/models/v10/yolov10s.yaml"
#数据集配置文件
data_yaml_path = 'D:/yolov10/datasets/insulator_detect/data.yaml'
#预训练模型
pre_model_name = 'D:/yolov10/yolov10s.pt'

if __name__ == '__main__':
    #加载预训练模型
    model = YOLOv10(model_yaml_path).load(pre_model_name)
    #训练模型
    results = model.train(data=data_yaml_path,
                          epochs=200,
                          batch=12,
                          name='insulator_detect')

