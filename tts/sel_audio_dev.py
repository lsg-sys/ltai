

import pyaudio
def list_audio_devices():
    au = pyaudio.PyAudio()
    
    print("可用音频输出设备列表：")
    for i in range(au.get_device_count()):
        dev_info = au.get_device_info_by_index(i)
        if dev_info['maxOutputChannels'] > 0:
            print(f"Index: {i} \t| Channels: {dev_info['maxOutputChannels']} \t| Name: {dev_info['name']}")

    au.terminate()
    
if __name__ == '__main__':

    # 获取当前文件所在目录的上一级目录
    import sys
    import os
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(parent_dir)
    # print("[sel_audio_dev] cur_work_dir: ", os.getcwd())
    # print("[sel_audio_dev] sys.path: ", sys.path)

    import config_file


    list_audio_devices()
    au_dev_index = int(input("请输入要使用的音频设备索引(Index后的数字)："))
    
    # 写入文件
    # file_path = os.path.join(current_directory, "audio_dev_index.txt")
    # with open(file_path, "w", encoding="utf-8") as f:
    #     f.write(str(au_dev_index))

    config_file.set_config_value("audio_device_index", au_dev_index)