import os
import random
import shutil

# 原数据集目录（相对目录）
root_dir = 'E:/Huaweitest/merged_insulator_data_new'
# 划分比例：训练集：验证集：测试集=8：1：1
train_ratio = 0.8
valid_ratio = 0.1
test_ratio = 0.1

# 拆分后数据集目录
split_dir = 'D:/yolov10/datasets/insulator_detect'
os.makedirs(os.path.join(split_dir, 'train/images'), exist_ok=True)
os.makedirs(os.path.join(split_dir, 'train/labels'), exist_ok=True)
os.makedirs(os.path.join(split_dir, 'valid/images'), exist_ok=True)
os.makedirs(os.path.join(split_dir, 'valid/labels'), exist_ok=True)
os.makedirs(os.path.join(split_dir, 'test/images'), exist_ok=True)
os.makedirs(os.path.join(split_dir, 'test/labels'), exist_ok=True)

# 获取图片文件列表
image_files = os.listdir(os.path.join(root_dir, 'images'))
label_files = os.listdir(os.path.join(root_dir, 'labels'))

# 随机打乱文件列表
combined_files = list(zip(image_files, label_files))#图片、标签转化为列表
random.shuffle(combined_files)#打乱
image_files_shuffled, label_files_shuffled = zip(*combined_files)#重新获取

# 根据比例计算划分的边界索引
train_bound = int(train_ratio * len(image_files_shuffled))#图片总数*训练集比例
valid_bound = int((train_ratio + valid_ratio) * len(image_files_shuffled))

# 将图片和标签文件移动到相应的目录
for i, (image_file, label_file) in enumerate(zip(image_files_shuffled, label_files_shuffled)):
    if i < train_bound:
        shutil.copy(os.path.join(root_dir, 'images', image_file), os.path.join(split_dir, 'train/images', image_file))
        shutil.copy(os.path.join(root_dir, 'labels', label_file), os.path.join(split_dir, 'train/labels', label_file))
    elif i < valid_bound:
        shutil.copy(os.path.join(root_dir, 'images', image_file), os.path.join(split_dir, 'valid/images', image_file))
        shutil.copy(os.path.join(root_dir, 'labels', label_file), os.path.join(split_dir, 'valid/labels', label_file))
    else:
        shutil.copy(os.path.join(root_dir, 'images', image_file), os.path.join(split_dir, 'test/images', image_file))
        shutil.copy(os.path.join(root_dir, 'labels', label_file), os.path.join(split_dir, 'test/labels', label_file))


