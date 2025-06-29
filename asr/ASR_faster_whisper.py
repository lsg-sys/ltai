import threading
import wave
import pyaudio
from faster_whisper import WhisperModel
import webrtcvad
import queue
import signal
import time
import socket
import os

current_script_path = os.path.abspath(__file__)
current_directory = os.path.dirname(current_script_path)
# print("当前脚本路径:", current_script_path)
# print("当前脚本所在目录:", current_directory)


def load_keywords(relative_path):
    file_path = os.path.join(current_directory, relative_path)
    with open(file_path, 'r', encoding='utf-8') as file:
        keywords = [line.strip() for line in file if line.strip()] # 自动忽略空行
    return keywords

def load_the_int_val(relative_path):
    file_path = os.path.join(current_directory, relative_path)
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read().strip()
            if not content:
                print(f"[警告] 文件为空: {file_path}")
                return None  # 或者返回默认值，如 0
            else:
                return int(content)
    except FileNotFoundError:
        print(f"[错误] 文件未找到: {file_path}")
        return None
    except ValueError:
        print(f"[错误] 文件内容不是合法整数: {file_path}")
        return None

# 全局加载关键词
n_keywords = load_keywords('反向关键字.txt')
print(f"含有 {n_keywords} 的语句将被过滤")
p_keywords = load_keywords('正向关键字.txt')
print(f"不含有 {p_keywords} 的语句将被过滤" , )

min_text_limit = load_the_int_val('最小识别长度限制.txt')
print(f"识别长度小于 {min_text_limit} 的语句将被过滤")


class TransmitSocket():
    def __init__(self, host, port, listen_num):
        self.clients = []
        self.clients_lock = threading.Lock()  # 创建锁对象
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # 设置 socket选项 SO_REUSEADDR：允许重复使用本地地址和端口，避免重启服务时报错“Address already in use”。
        self.server_socket.bind((host, port))
        self.server_socket.listen(listen_num)
        print("[TransmitSocket] 服务器已启动，等待客户端连接...")

        self.stop_flag = False

        def accept_connections():
            print("[TransmitSocket] TCP 接口已启动，等待连接...")
            while not self.stop_flag:
                try:
                    self.server_socket.settimeout(1) # 设置 socket 超时时间为 1 秒，防止 accept() 永久阻塞。
                    client_socket, client_addr = self.server_socket.accept() # 接受客户端连接
                    print(f"[TransmitSocket] 客户端连接: {client_addr}")
                    with self.clients_lock: # 加锁，避免多线程访问时出现错误。
                        self.clients.append(client_socket)
                except socket.timeout:
                    pass
                except socket.error as e:
                    print(f"[TransmitSocket] 接受客户端连接时出错: {e}")
                
                # 检查客户端连接情况
                with self.clients_lock:
                    for client_socket in list(self.clients):
                        try:
                            client_socket.settimeout(0.3)
                            data = client_socket.recv(1024) # 接收数据
                        except socket.timeout:
                            pass
                        except socket.error as e:
                            print(f"[TransmitSocket] 错误：{e}")
                            print(f"[TransmitSocket] {client_socket.getpeername()} 断开连接")
                            client_socket.close()
                            self.clients.remove(client_socket)

            print("[TransmitSocket] accept_connections 线程已退出")

        self.accept_connect_th = threading.Thread(target=accept_connections, daemon=True) # daemon=True, 主程序退出时，子线程也退出
    
    def start(self):
        self.accept_connect_th.start()

    def stop(self):
        self.stop_flag = True

        # 等待接收客户端连接的线程结束
        self.accept_connect_th.join()

        with self.clients_lock:
            for client_socket in self.clients:
                try:
                    client_socket.close()  # 关闭所有客户端连接
                except socket.error as e:
                    print(f"[TransmitSocket] 关闭客户端连接时出错: {e}")
            self.clients.clear()  # 清空客户端列表
        self.server_socket.close()  # 关闭服务端 socket

    def send(self, data:str):
        with self.clients_lock:  # 加锁保护整个操作
            for client_socket in list(self.clients):  # 使用副本避免迭代问题
                try:
                    client_socket.sendall(data.encode('utf-8'))
                except socket.error as e:
                    print(f"[TransmitSocket] 发送数据时出错: {e}")
                    client_socket.close()
                    self.clients.remove(client_socket)  # 已经在锁内，无需再次加锁


class SemProducer():
    def __init__(self, max_size, speed_sec):
        self.sem = threading.BoundedSemaphore(max_size)
        self.speed_sec = speed_sec
        self.timer = None
        self.stop_flag = False

    def release_semaphore_periodically(self):

        if self.stop_flag:
            print("[SemProducer] 定时器已停止")
        else:
            with self.sem._cond:
                current_value = self.sem._value

            if current_value < 4:
                self.sem.release()
                print(f"[SemProducer] 释放一个信号量，当前可用: {current_value + 1}/4")
            else:
                print("[SemProducer] 信号量已满，不再释放")
                
            self.semaphore_timer = threading.Timer(
                self.speed_sec, self.release_semaphore_periodically
            )
            self.semaphore_timer.start()

    def acquire(self):
        return self.sem.acquire(blocking=False)
    
    def cancel_timer(self):
        self.stop_flag = True
        if self.semaphore_timer is not None:
            self.semaphore_timer.cancel()
            self.semaphore_timer = None
        print("[SemProducer] 定时器已取消")


# 音频参数
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000  # 支持 webrtcvad 的采样率
CHUNK_DURATION_MS = 30  # 每个音频块的时长（毫秒），支持 10、20、30
CHUNK = int(RATE * CHUNK_DURATION_MS / 1000)  # 计算对应样本数
RECORD_SECONDS = 10


# 创建音频队列和停止标志
audio_queue = queue.Queue()
stop_event = threading.Event()
record_th_is_initialized = threading.Event()
transcribe_th_is_initialized = threading.Event()

# 初始化 PyAudio 和 VAD
audio = pyaudio.PyAudio()
vad = webrtcvad.Vad(3)  # 灵敏度级别 1~3，数字越大越敏感


def is_speech(data):
    """使用 VAD 判断是否是语音"""
    return vad.is_speech(data, sample_rate=RATE)

# 录音线程函数
def record_audio():
    stream = audio.open(format=FORMAT, channels=CHANNELS,
                        rate=RATE, input=True,
                        frames_per_buffer=CHUNK)

    record_th_is_initialized.set()

    print("开始录音... ")

    while not stop_event.is_set():
        frames = []
        silent_frames = 0
        voice_started = False

        for _ in range(int(RECORD_SECONDS * RATE / CHUNK)):  # 每次最多录制 RECORD_SECONDS 秒
            if stop_event.is_set():
                break

            data = stream.read(CHUNK)
            if is_speech(data):
                voice_started = True
                frames.append(data)
                silent_frames = 0
            elif voice_started:
                frames.append(data)
                silent_frames += 1
            else:
                silent_frames += 1

            # 如果连续静音超过一定帧数，认为语音结束
            if voice_started and silent_frames > 20:
                break

        if len(frames) > 0:
            print("检测到语音，已发送到识别线程")
            audio_queue.put(b''.join(frames))




# 识别线程函数
def transcribe_audio(send_to_clients_func):
    
    # 模型配置
    print("模型加载中，请稍候...")
    model = WhisperModel(model_size_or_path = "model/faster-whisper-large-v3", 
                        #  model_size = "large-v3", 
                         device = "cuda", 
                        #  compute_type = "int8_float16"
                         compute_type = "float16",
                         local_files_only=True,       # 不尝试联网下载
                         download_root=None           # 防止缓存路径干扰
                        )
    print("模型加载完成")

    # 启动定时释放信号量的任务
    time_sem = SemProducer(max_size=4, speed_sec=15)
    time_sem.release_semaphore_periodically()
    
    transcribe_th_is_initialized.set()

    # 主识别循环
    while not stop_event.is_set():
        try:
            # print("等待音频数据...")
            audio_data = audio_queue.get(timeout=1)
            print("开始识别...")

            with wave.open("temp.wav", 'wb') as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(audio.get_sample_size(FORMAT))
                wf.setframerate(RATE)
                wf.writeframes(audio_data)

            segments, info = model.transcribe("temp.wav", beam_size=5, language="zh")
            # print("检测语言: %s (%.2f)" % (info.language, info.language_probability))

            result_text = ""
            for segment in segments:
                # line = "[%.2fs -> %.2fs] %s\n" % (segment.start, segment.end, segment.text)
                line = "%s\n" % (segment.text)
                result_text += line
                # print(line.strip())

            # 检查是否有关键词
            if result_text == "":
                print("过滤掉 空白内容")
            elif min_text_limit != None and len(result_text) < min_text_limit:
                print("过滤掉 过短内容：  ", result_text)
            elif any(keyword in result_text for keyword in n_keywords):
                print("过滤掉 含有反向关键字的内容：  ", result_text)
            elif len(p_keywords) != 0 and not any(keyword in result_text for keyword in n_keywords):
                print("过滤掉 不含有正向关键字的内容：  ", result_text)
            else:
                # 获取信号量许可
                if time_sem.acquire(): # 非阻塞获取信号量
                    # 将识别结果广播给所有连接的客户端
                    # 发送前，删除空格和回车
                    result_text = result_text.replace(" ", "\n")
                    print("广播：", result_text)
                    send_to_clients_func(result_text) 
                else:
                    print("发送频率过高，本次跳过")

        except queue.Empty:
            continue
    
    time_sem.cancel_timer()
    print("音频识别线程退出")


if __name__ == "__main__":


    trans_socket = TransmitSocket('127.0.0.1', 19222, 
                                  listen_num=2)
    # 启动 TCP 服务器
    trans_socket.start()

    # 启动线程
    transcription_thread = threading.Thread(target=transcribe_audio, 
                                            args=(lambda text: trans_socket.send(text),))
    transcription_thread.start()
    while not transcribe_th_is_initialized.is_set():
        time.sleep(0.5)

    recording_thread = threading.Thread(target=record_audio)
    recording_thread.start()
    while not record_th_is_initialized.is_set():
        time.sleep(0.5)

    # 捕获 Ctrl+C 信号
    def signal_handler(sig, frame):
        print("\n接收到退出信号，准备停止...")
        stop_event.set()

        recording_thread.join()
        transcription_thread.join()

        audio.terminate()

        # 停止 TCP 服务
        trans_socket.stop()
        
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    print("按 Ctrl+C 停止程序...")
    time.sleep(1)
    
    import socket
    PORT_WAIT = 33175
    while True:
        try:
            ready_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            ready_client.settimeout(5)
            ready_client.connect(('127.0.0.1', PORT_WAIT))

            # 等待响应 received ready 然后断开连接
            while True:
                ready_client.sendall(b"ready")
                ready_client.settimeout(1)
                data = ready_client.recv(1024)
                if data == b"received ready":
                    break
                else:
                    print(f"接收到数据 {data}")
                    time.sleep(1)

            ready_client.close()
            break
        except Exception as e:
            time.sleep(1)
            if stop_event.is_set():
                break
    print("服务启动完毕")


    # 等待线程结束, 主线程非阻塞才能接收信号
    while not stop_event.is_set():
        time.sleep(1)  # 主线程保持运行，等待信号触发

    print("ASR服务程序已停止。")

