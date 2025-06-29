import socket
import threading
import time

# 服务器地址和端口
HOST = '127.0.0.1'
PORT = 19222

if __name__ == '__main__':
    asr_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    asr_client.connect((HOST, PORT))

    stop_flag = False
    while not stop_flag:
        user_input = input("请输入exit退出，或输入任意内容等待消息 ")
        if  user_input == "exit":
            stop_flag = True
        else:
            print("等待数据...")
            try:
                data = asr_client.recv(4096)
                if not data:
                    print("[handle_client] Client has disconnected.")
                else:
                    print("[handle_client] Received:", data.decode('utf-8'))
            except:
                print("[handle_client] Error receiving data from client.")

