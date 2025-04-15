from ultralytics import YOLOv10

def main():
    # 指定输入和输出路径
    weights_path = 'D:/yolov10/runs/detect/insulator_detect2/weights/best.pt'
    output_path = 'test.onnx'
    
    # 加载模型
    model = YOLOv10(weights_path)
    
    # 导出为ONNX格式
    success = model.export(format='onnx', opset=12)
    
    if success:
        print(f"模型已成功转换为ONNX格式，保存在: {output_path}")
    else:
        print("模型转换失败")

if __name__ == '__main__':
    main()