
if __name__ == '__main__':

    import os
    import config_file
    import path_location

    print("可用的SoVITS权重模型列表：")
    sovits_weights_v2_dir = path_location.join_gptsovits_dir("SoVITS_weights_v2")
    sovits_weights_v2_files = os.listdir(sovits_weights_v2_dir)

    # 如果没有sovits权重模型，则提示用户添加
    if len(sovits_weights_v2_files) == 0:
        print("没有可用的sovits权重模型，请先添加！（或训练新的sovits权重模型）")
    else:
        for i, file in enumerate(sovits_weights_v2_files):
            print(f"Index: {i}. {file}")
        
        index = int(input("请输入要使用的SoVITS权重模型索引(Index后的数字)："))
        if index >= 0 and index < len(sovits_weights_v2_files):
            sovits_weights_v2_file = sovits_weights_v2_files[index]
            print("已选择SoVITS权重模型：", sovits_weights_v2_file)
            config_file.set_config_value("sovits_weights_v2", sovits_weights_v2_file) # 只需填写文件名，不需要路径
        else:
            print("无效的索引，请重试。")


