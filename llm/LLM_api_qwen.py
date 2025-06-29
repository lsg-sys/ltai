import socket
import threading
import os
import sys
import queue
import signal
import time

from openai import OpenAI
import json

# 获取当前文件所在目录的上一级目录
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

import config_file

current_script_path = os.path.abspath(__file__)
current_directory = os.path.dirname(current_script_path)

def load_the_string(relative_path):
    file_path = os.path.join(current_directory, relative_path)
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read().strip()
        if not content:
            print(f"[警告] 文件为空: {file_path}")
            return None  # 或者返回默认值，如 0
        return content

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


# my_api_key = load_the_string("API_KEY.txt")
my_api_key = config_file.get_config_value("api_key")
sys_prompt = load_the_string("提示词.txt")
max_history_num = load_the_int_val("记忆的对话轮数.txt")


class TransmitSocket():
    def __init__(self, host, port, listen_num, handle_client_func, exit_the_handle_client_func):
        self.exit_the_handle_client = exit_the_handle_client_func

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
                            'thread': threading.Thread(target=handle_client_func, args=(client_socket,))
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


modelName = "qwen-max"

def get_response_stream(messages):
    try:
        client = OpenAI(
            # 若没有配置环境变量，请用阿里云百炼API Key将下行替换为：api_key="sk-xxx",
            api_key=my_api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        # 模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
        
        # 启用 stream=True 来获取流式响应
        response_stream = client.chat.completions.create(
            model=modelName,
            messages=messages,
            stream=True
        )
        return response_stream
    except Exception as e:
        print(f"[ERROR] 流式响应获取失败: {str(e)}")
        return iter([])  # 返回空迭代器避免后续报错

def get_response(messages):
    client = OpenAI(
        # 若没有配置环境变量，请用阿里云百炼API Key将下行替换为：api_key="sk-xxx",
        api_key=my_api_key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    # 模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
    completion = client.chat.completions.create(model=modelName, messages=messages)
    return completion


stop_handle_client_event = threading.Event()

def handle_client(client_socket):

    #  初始化聊天历史
    chat_history = [{"role": "system", "content": sys_prompt}]
    print(f"即将使用的模型是 {modelName} ，请输入您的问题:")

    while not stop_handle_client_event.is_set():
        #  接收客户端消息，发送任何异常都退出线程
        try:
            client_socket.settimeout(1)  # 设置一次性的超时 recv() 超时为 1 秒
            data = client_socket.recv(4096)
            if not data:
                print("[handle_client] Client has disconnected.")
                break
            input_text = data.decode('utf-8')
        except socket.timeout:
            continue  # 超时后继续循环
        except socket.error as e:
            print(f"[handle_client] ERROR 接收客户端消息失败: {e}")
            break
        
        chat_history.append({"role": "user", "content": input_text})
        print(f"\n[handle_client] RECEIVED 用户: {input_text}")  # 打印接收到的消息
        
        # 调用模型生成流式响应
        response_stream = get_response_stream(chat_history)
        model_output = ""
        print("[handle_client] RESPONSE 模型: ", end="", flush=True)

        for chunk in response_stream:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                model_output += content
                print(content, end="", flush=True)
                client_socket.sendall(content.encode('utf-8')) # 实时发送当前块内容给客户端
        client_socket.sendall("[END]".encode('utf-8')) # 告诉客户端回复已结束
        print()  # 最后换行

        # 将完整回复添加到聊天历史
        chat_history.append({"role": "assistant", "content": model_output})
        
        # 控制聊天历史长度
        if max_history_num == None or max_history_num <= 0:
            # 不需要聊天历史记忆能力, 移除系统消息外的所有消息
            while len(chat_history) > 1:
                chat_history.pop(1)
        elif len(chat_history) > 1 + max_history_num * 2: # 保留系统提示 + 最近 max_history_num 轮对话（用户+助手）
            next_chat_history = [chat_history.pop(0)]

            # 断言，chat_history剩下的长度是
            assert len(chat_history) % 2 == 0

            # 打包聊天历史
            Summarize_historical_dialogues = "[总结对话内容]"
            for i in range(0, len(chat_history), 2): # 偶数索引为用户消息，奇数索引为助手消息
                Summarize_historical_dialogues +=  f" {{user:{chat_history[i]}}} {{agent:{chat_history[i+1]}}}"
            # 调用模型生成总结
            next_chat_history.append({"role": "user", "content": Summarize_historical_dialogues})
            response  = get_response(next_chat_history).choices[0].message.content
            print(f"[SUMMARIZE]: {response}\n")
            next_chat_history.append({"role": "assistant", "content": response})
            next_chat_history[1]["content"] = "[总结对话内容] {...}" # 发送完成后删除冗余对话信息

            chat_history = next_chat_history

    print(f"[handle_client] 客户端处理线程 {client_socket.getpeername()[0]}:{client_socket.getpeername()[1]} 已停止")


if __name__ == "__main__":

    # 启动 TCP 服务器
    trans_socket = TransmitSocket('127.0.0.1', 57239, 
                                  listen_num = 1,
                                  handle_client_func=handle_client,
                                  exit_the_handle_client_func=lambda: stop_handle_client_event.set())
    # 开始接收客户端
    trans_socket.start()

    # 捕获 Ctrl+C 信号
    def signal_handler(sig, frame):
        print("\n接收到退出信号，准备停止...")
        # 停止 TCP 服务
        trans_socket.stop()
        print("退出信号处理结束")
        
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
            if stop_handle_client_event.is_set():
                break
    print("服务启动完毕")

    # 等待线程结束, 主线程非阻塞才能接收信号
    while not stop_handle_client_event.is_set():
        time.sleep(1)  # 主线程保持运行，等待信号触发

    print("LLM 服务程序已停止。")
