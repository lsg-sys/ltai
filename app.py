import subprocess
import shlex
import os
import socket
import signal
import threading
import time
import tempfile

# 服务器地址和端口
HOST = '127.0.0.1'
PORT_TTS = 42135
PORT_LLM = 57239
PORT_ASR = 19222
PORT_WAIT = 33175



class SubPorcServer():
    server_count = 0
    ready_socket_server = None

    def __init__(self, name, setup_cmd, ):

        if SubPorcServer.server_count == 0:
            # 创建一个socket用于接收子进程的就绪信号
            SubPorcServer.ready_socket_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            SubPorcServer.ready_socket_server.bind((HOST, PORT_WAIT))
            SubPorcServer.ready_socket_server.listen(1)
            print("[SubPorcServer] 开启用于接收子进程的就绪信号的服务器")

        self.name = name

        continue_flag = False
        

        # 创建子进程
        self.porc = subprocess.Popen(shlex.split(setup_cmd),
                                   stdout=None,
                                   stderr=None,)
            
        # 等待服务启动完成
        print(f"[SubPorcServer] 正在启动 {self.name} 服务, 请稍候...")
        # 无限等待等待子进程服务连接 ready_socket_server，并发送启动完成信号
        while True:
            try:
                SubPorcServer.ready_socket_server.settimeout(1)
                client, addr = SubPorcServer.ready_socket_server.accept()
                print(f"[SubPorcServer] {self.name} 接收到了连接 {addr}")
                while True:
                    client.settimeout(1)
                    data = client.recv(1024)
                    if data == b"ready":
                        client.sendall(b"received ready")
                        print(f"[SubPorcServer] {self.name} 服务启动完成")
                        break
                    else:
                        print(f"[SubPorcServer] 接收到数据 {data}")
                        time.sleep(1)
                client.close()
                break
            except:
                time.sleep(1)
        SubPorcServer.server_count += 1


    def stop(self):
        # 停止接收线程 关闭服务进程
        self.porc.terminate()
        try:
            self.porc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.porc.kill()
        self.porc = None
        print(f"[SubPorcServer] 关闭{self.name}服务进程")

        SubPorcServer.server_count -= 1
        if SubPorcServer.server_count == 0:  # 所有服务进程已停止
            print("[SubPorcServer] 关闭用于接收子进程的就绪信号的服务器")
            SubPorcServer.ready_socket_server.close()


def main(is_not_stop_func):
    try:
        tts_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tts_client.connect((HOST, PORT_TTS))
    except Exception as e:
        print(f"[app] 无法连接到 TTS 服务器: {e}")
        return -1

    def tts(input_text):
        tts_client.sendall(input_text.encode('utf-8'))

    try:
        llm_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        llm_client.connect((HOST, PORT_LLM))
    except Exception as e:
        print(f"[app] 无法连接到 LLM 服务器: {e}")
        tts_client.close()
        return -1
    def llm(input_text_b):
        llm_client.sendall(input_text_b)

        buffer = ""  # 缓冲区用于拼接数据
        while True:
            print("[app] [llm] 等待数据...")
            llm_data = llm_client.recv(4096)
            if not llm_data:
                print("[app] [llm] error: 服务端断开连接")
                break
            
            buffer += llm_data.decode('utf-8')
            # 如果遇到 [END]，停止接收并处理剩余文本
            if "[END]" in buffer:
                final_text, _, buffer = buffer.partition("[END]")
                if final_text:
                    print(f"[app] [TTS] 最终回复内容: {final_text}")
                print("[app] 遇到 [END]\n")
                break

            # 将当前缓冲区中所有内容作为部分文本传给 TTS（可选：添加标点判断避免中途打断）
            if buffer:
                # print(f"[app] [TTS] 接收到部分内容: {buffer}")
                # 检查str是否包含标点符号，若有，则从标点处截取
                # punctuation = ('。', '.', '，', ',', '？', '?', '！', '!')
                # punctuation = ('。', '.', '？', '?', '！', '!')
                punctuation = ('。', '.', '？', '?', '！', '!')
                for p in punctuation:
                    # idx = buffer.find(p)
                    idx = buffer.rfind(p) # 从末尾开始查找
                    if idx != -1:
                        print("[app] [llm] 检测到句尾符号，开始合成")
                        tts(buffer[:idx + 1])
                        buffer = buffer[idx + 1:]  # 更新 buffer 为剩余内容
                        break
    
    try:
        asr_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        asr_client.connect((HOST, PORT_ASR))
    except Exception as e:
        print(f"[app] 无法连接到 ASR 服务器: {e}")
        tts_client.close()
        llm_client.close()
        return -1

    for i in range(10):
        print("[app] 初始化完成")

    while is_not_stop_func():
        time.sleep(0.1)
        try:
            asr_data = asr_client.recv(4096)
            if not asr_data:
                print("[app] [asr] Client has disconnected.")
            else:
                print("[app] [asr] Received:", asr_data.decode('utf-8'))
                llm(asr_data)
        except:
            print("[app] [asr] Error receiving data from client.")
    
    asr_client.close()
    llm_client.close()
    tts_client.close()

    return 0

    


if __name__ == '__main__':

    
    import path_location

    # 子进程默认使用的Python解释器
    py_interpreter = path_location.get_path_python_interpreter()
    py_interpreter = py_interpreter.replace("\\", "/") # 替换路径风格为POSIX


    tts_server_path = path_location.get_path("tts_server").replace("\\", "/")
    tts = SubPorcServer("TTS", f"{py_interpreter} {tts_server_path}")
    llm_server_path = path_location.get_path("llm_server").replace("\\", "/")
    llm = SubPorcServer("LLM", f"{py_interpreter} {llm_server_path}")
    asr_server_path = path_location.get_path("asr_server").replace("\\", "/")
    asr = SubPorcServer("ASR", f"{py_interpreter} {asr_server_path}")
    
    # 设置停止事件
    stop_event = threading.Event()
    # 设置Ctrl+C中断处理
    def signal_handler(sig, frame):
        print("\n[app] 接收到退出信号，准备停止...")
        stop_event.set()

        asr.stop()
        llm.stop()
        tts.stop()

        print("[app] 退出信号处理结束")

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    print("[app] 按Ctrl+C退出程序")

    try:
        # 主线程等待中断信号
        if main(lambda : not stop_event.is_set()) < 0:
            print("[app] main 异常退出")
            signal_handler(None, None)
    except KeyboardInterrupt:
        # 当用户按下Ctrl+C时，会自动跳转到signal_handler
        pass
    except Exception as e:
        print(f"[app] 主程序异常: {e}")
        signal_handler(None, None)
    
    print("[app] 主程序已完全关闭")
