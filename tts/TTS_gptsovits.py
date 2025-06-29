
import socket
import threading
import os
import sys
import queue
import signal
import time

from gptsovits_func import GptSoVits


parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)
import config_file
import path_location


class TransmitSocket():
    def __init__(self, host, port, listen_num, handle_client_func, handle_client_args, exit_the_handle_client_func):
        self.exit_the_handle_client = exit_the_handle_client_func
        self.client_args = handle_client_args

        self.clients = [] # {"client_socket": "client_address" : "thread"}
        self.clients_lock = threading.Lock()  # 创建锁对象
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # 设置 socket选项 SO_REUSEADDR：允许重复使用本地地址和端口，避免重启服务时报错“Address already in use”。
        self.server_socket.settimeout(1) # 设置 socket 超时时间为 1 秒，防止 accept() 永久阻塞。
        self.server_socket.bind((host, port))
        self.server_socket.listen(listen_num)
        print(f"[TransmitSocket] 服务器{(host, port)}已启动，等待客户端连接...")

        self.stop_flag = False
        def accept_connections():
            print("[TransmitSocket] TCP 接口已启动，等待连接...")
            while not self.stop_flag:
                #  等待客户端连接
                try:
                    client_socket, client_addr = self.server_socket.accept() # 接受客户端连接
                    print(f"[TransmitSocket] 客户端连接: {client_addr}")
                    with self.clients_lock: # 加锁，避免多线程访问时出现错误。
                        self.clients.append({
                            'socket': client_socket, 
                            'addr': client_addr, 
                            'thread': threading.Thread(target=handle_client_func, args=(client_socket,self.client_args,))
                        })
                        self.clients[-1]['thread'].start() # 启动线程处理客户端连接
                except socket.timeout:
                    pass
                except socket.error as e:
                    print(f"[TransmitSocket] 接受客户端连接时出错: {e}")

                # 检查以及连接的客户端的工作状态
                with self.clients_lock:
                    for client in self.clients:
                        if not client['thread'].is_alive():
                            client['socket'].close()
                            print(f"[TransmitSocket] 客户端 {client['addr']} 已从列表中移除")
                            self.clients.remove(client)

            print("[TransmitSocket] accept_connections 线程已退出")
        
        self.accept_connect_th = threading.Thread(target=accept_connections, daemon=True)
    
    def start(self):
        self.accept_connect_th.start() #启动接收客户端连接的线程

    def stop(self):
        self.stop_flag = True
        # 等待接收客户端连接的线程结束
        self.accept_connect_th.join()

        with self.clients_lock:
            # 让所有客户端连接自行退出
            self.exit_the_handle_client()
            #  等待所有客户端连接自行退出 （线程内能够直接退出，不受客户端状态影响）
            for client in self.clients:
                client['thread'].join()
                try:
                    client['socket'].close()  # 关闭所有客户端连接
                except socket.error as e:
                    print(f"[TransmitSocket] 关闭客户端连接时出错: {e}")
            self.clients.clear()  # 清空客户端列表
        self.server_socket.close()  # 关闭服务端 socket


# TTS合成线程，接收文本队列的内容，转换后发送到音频播放队列
tts_thread_stop_event = threading.Event()
def tts_thread(text_queue, tts_and_play_func):

    while not tts_thread_stop_event.is_set():
        try:
            text = text_queue.get(timeout=1)  # 从队列中获取文本
            print(f"[tts_thread] 准备合成语音: {text}")
            tts_and_play_func(text)
        except queue.Empty:
            pass
    
    print("tts_thread 线程已停止")


stop_handle_client_event = threading.Event()
def handle_client(client_socket, args: tuple):
    textQ : queue.Queue = args[0]
    
    while not stop_handle_client_event.is_set():
        try:
            client_socket.settimeout(1)
            data = client_socket.recv(4096)
            if not data:
                print("[handle_client] Client has disconnected.")
                break
            else:
                text = data.decode('utf-8')
                print(f"[handle_client] 接收到数据: {text}")
                textQ.put(text)
        except socket.timeout:
            pass

    print(f"[handle_client] 客户端处理线程 {client_socket.getpeername()} 已停止")

if __name__ == "__main__":

    gptSovits = GptSoVits()
    gptSovits.open()
    gpt_weights = config_file.get_config_value("gpt_weights_v2")
    gpt_weights_path = f"GPT_weights_v2/{gpt_weights}" # 服务器上的cwd是gptsovits目录
    gptSovits.set_gpt_weights(gpt_weights_path)
    sovits_weights = config_file.get_config_value("sovits_weights_v2")
    sovits_weights_path = f"SoVITS_weights_v2/{sovits_weights}" # 服务器上的cwd是gptsovits目录
    gptSovits.set_sovits_weights(sovits_weights_path)

    # 封装 tts 函数
    ref_audio_path      = config_file.get_config_value("tts_ref_audio_relative_path")
    ref_audio_text      = config_file.get_config_value("tts_ref_audio_text")
    the_speed_factor    = config_file.get_config_value("tts_speed_factor")
    def tts_and_play(text):
        gptSovits.stream_tts_and_play(text=text,
                                      ref_audio_path=ref_audio_path,
                                      prompt_text=ref_audio_text,
                                      speed_factor=the_speed_factor)


    text_queue = queue.Queue()
    # 创建并启动接收线程
    tts_th = threading.Thread(target=tts_thread, args=(text_queue, tts_and_play))
    tts_th.start()


    # 创建并启动接收线程
    tts_server = TransmitSocket('127.0.0.1', 42135, 
                                listen_num=1,
                                handle_client_func=handle_client,
                                handle_client_args=(text_queue,),
                                exit_the_handle_client_func= lambda : stop_handle_client_event.set())
    tts_server.start()

    # 设置停止事件
    stop_event = threading.Event()
    # 设置Ctrl+C中断处理
    def signal_handler(sig, frame):
        print("\n接收到退出信号，准备停止...")
        stop_event.set()
        # text_queue.put(None)  # 向队列发送结束信号

        # 停止 TCP 服务
        tts_server.stop()
        print("停止 TCP 服务已成功关闭")

        # 停止 TTS 线程
        tts_thread_stop_event.set()
        tts_th.join()
        print("接收线程已成功关闭")

        # 终止子进程
        gptSovits.close()

        print("退出信号处理结束")

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
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

    print("TTS 服务 程序已准备就绪，请开始输入...")

    try:
        # 主线程等待中断信号
        while not stop_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        # 当用户按下Ctrl+C时，会自动跳转到signal_handler
        pass
    
    print("TTS 服务 主程序已完全关闭")


