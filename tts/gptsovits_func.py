import sys
import os

# 获取当前文件所在目录的上一级目录
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

import config_file
import path_location

import time
import subprocess
import shlex
import requests

import pyaudio
import wave
from io import BytesIO

import threading
from threading import Thread
import socket

current_script_path = os.path.abspath(__file__)
current_directory = os.path.dirname(current_script_path)


# API 地址
base_url = "http://127.0.0.1:9880"
# 文本转语音接口
tts_endpoint = f"{base_url}/tts"

class GptSoVits:
    def __init__(self):
        self.server_process = None
        self.audio = pyaudio.PyAudio()

        # 从配置文件中读取 音频设备索引 并 打印提示信息
        self.sel_audio_device_index = config_file.get_config_value("audio_device_index")
        if self.sel_audio_device_index < 0:
            print("未指定音频设备，使用默认设备。")
        else:
            print(f"使用音频设备：{self.audio.get_device_info_by_index(self.sel_audio_device_index)['name']}")

        # self.subProcessStdoutTh_stop_event = threading.Event()
        # def read_stdout_th():
        #     while not self.subProcessStdoutTh_stop_event.is_set():
        #         try:
        #             if self.server_process is None:
        #                 break
        #             else:
        #                 line = self.server_process.stdout.readline().decode("utf-8")
        #                 if line.split():
        #                     print(line)
        #         except Exception as e:
        #             print(e)
        #     print("子进程 stdout 读取线程已关闭")
        # self.subProcessStdoutTh = Thread(target=read_stdout_th, daemon=True)

    def open(self):
        # 用subprocess启动 gptsovits的api服务
        py_interpreter = path_location.get_path('gpt_sovits_python_interpreter')
        gptsovits_api_server = path_location.get_path('gpt_sovits_pai_server')
        gptsovits_api_server_cwd = path_location.get_path('gpt_sovits_dir')
        self.server_process = subprocess.Popen([py_interpreter, gptsovits_api_server], 
                                               cwd = gptsovits_api_server_cwd,
                                                # stdout = subprocess.PIPE, 
                                                stdout=None,
                                                # stdout=None,  # 直接输出到控制台
                                                stderr=None,)
        print("启动GPT-Sovits服务, 请等待...")
            
        # 创建客户端，并尝试连接本地服务（42135），然后等待其发送 b"ready"
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        while True:
            try:
                client.settimeout(5)
                client.connect(('localhost', 42136))

                if client.recv(1024) == b"ready":
                    print("[gptsovits_func] received ready")
                    # 发送 received ready 然后断开连接
                    client.send(b"received ready")
                    client.close()
                    break
            except Exception as e:
                print("等待GPT-Sovits服务启动...")
                time.sleep(1)
                continue
        # print("开启 GPT-Sovits服务 打印信息接收线程")
        # self.subProcessStdoutTh.start()
        for i in range(5):
            time.sleep(1)
            print(f"GPT-Sovits服务 初始化 {i+1}/5")
        print("GPT-Sovits服务启动成功!!!")


    def close(self):

        self.audio.terminate()
        self.sel_audio_device_index = None

        # self.subProcessStdoutTh_stop_event.set()

        self.server_process.terminate()
        try:
            self.server_process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.server_process.kill()
        
        self.server_process = None
        # self.subProcessStdoutTh.join(timeout=3)
        print("关闭GPT-Sovits服务 打印信息接收线程")
        print("GPT-Sovits服务已终止")

    # 切换 GPT 模型
    def set_gpt_weights(self, weights_path):
        url = f"{base_url}/set_gpt_weights"
        params = {"weights_path": weights_path}
        response = requests.get(url, params=params)
        if response.status_code == 200:
            print("GPT 模型切换成功")
        else:
            print("GPT 模型切换失败:", response.json())

    # 切换 SoVITS 模型
    def set_sovits_weights(self, weights_path):
        url = f"{base_url}/set_sovits_weights"
        params = {"weights_path": weights_path}
        response = requests.get(url, params=params)
        if response.status_code == 200:
            print("SoVITS 模型切换成功")
        else:
            print("SoVITS 模型切换失败:", response.json())

    def stream_tts_and_play(self, text, ref_audio_path, prompt_text, speed_factor=1.0):
        response = requests.get(tts_endpoint, 
                                stream=True,
                                params={"text": text,
                                        "text_lang": "zh",
                                        "ref_audio_path": ref_audio_path,  # 替换为你自己的参考音频路径
                                        "prompt_text": prompt_text,
                                        "prompt_lang": "zh",
                                        "text_split_method": "cut5",
                                        "batch_size": 1,
                                        "media_type": "wav",       # 必须为 wav 或 raw 才能流式播放
                                        "streaming_mode": True,
                                        "speed_factor": speed_factor})
        if response.status_code != 200:
            print("请求失败:", response.json())
            return

        stream = None
        header_received = False
        CHUNK = 4096  # 每次读取的音频块大小
        for chunk in response.iter_content(chunk_size=CHUNK):
            if not chunk:
                continue

            if not header_received:
                print("开始播放")

                # 先读取前 44 字节的 WAV header
                buffer = BytesIO()
                buffer.write(chunk)
                if buffer.tell() >= 44:  # 确保至少有 WAV header
                    buffer.seek(0)
                    wf = wave.open(buffer, 'rb')
                    if self.sel_audio_device_index < 0: # 使用默认设备
                        stream = self.audio.open(format=pyaudio.get_format_from_width(wf.getsampwidth()),
                                                channels=wf.getnchannels(),
                                                rate=wf.getframerate(),
                                                output=True)
                    else:
                        stream = self.audio.open(format=pyaudio.get_format_from_width(wf.getsampwidth()),
                                                channels=wf.getnchannels(),
                                                rate=wf.getframerate(),
                                                output=True,
                                                output_device_index=self.sel_audio_device_index)

                    # 读取剩余的 buffer 数据
                    remaining = buffer.getvalue()[44:]
                    if remaining:
                        stream.write(remaining)
                    header_received = True
            else:
                stream.write(chunk)

        # 关闭播放
        if stream:
            stream.stop_stream()
            stream.close()
        print("播放完成")

    def tts_to_wav(text, output_path, ref_audio_path, prompt_text, speed_factor=1.0):

        # 发送 GET 请求
        response = requests.get(tts_endpoint, params={
                                "text": text,
                                "text_lang": "zh",
                                "ref_audio_path": ref_audio_path,  # 替换为你自己的参考音频路径
                                "prompt_text": prompt_text,
                                "prompt_lang": "zh",
                                "text_split_method": "cut5",
                                "batch_size": 1,
                                "media_type": "wav",       # 必须为 wav 或 raw 才能流式播放
                                "streaming_mode": False,
                                "speed_factor": speed_factor
                            })
        # 判断响应是否成功
        if response.status_code == 200:
            # 保存返回的音频文件
            with open(output_path, "wb") as f:
                f.write(response.content)
            print(f"音频已保存至 {output_path}")
        else:
            print("请求失败:", response.json())


def test():

    tts = GptSoVits()

    tts.open()

    # 切换为你自己的 GPT 权重路径
    gpt_weights_path = "GPT_weights_v2/Ceobe-e15.ckpt" # 服务器上的路径
    tts.set_gpt_weights(gpt_weights_path)

    # 切换为你自己的 SoVITS 权重路径
    sovits_weights_path = "SoVITS_weights_v2/Ceobe_e8_s136.pth" # 服务器上的路径
    tts.set_sovits_weights(sovits_weights_path)

    # 调用文本转语音接口
    # tts_to_wav( text="你好，这是一个测试语音合成的示例。",
    #             output_path="./output.wav", # 本地上的路径
    #             ref_audio_path="myData/Ceobe/ref/Elite promotion 1.wav", # 服务器上的路径
    #             prompt_text="这个小小的纽扣是送给我的吗？我别起来啦，好看吗？",
    #             speed_factor=1.2)

    tts.stream_tts_and_play( text="你好，这是一个测试语音合成的示例。将以流式合成并立即播放",
                        ref_audio_path="myData/Ceobe/ref/Elite promotion 1.wav", # 服务器上的路径
                        prompt_text="这个小小的纽扣是送给我的吗？我别起来啦，好看吗？",
                        speed_factor=1.2)

    tts.close()

if __name__ == "__main__":
    test()