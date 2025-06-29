import socket
import threading
import time

# 服务器地址和端口
HOST = '127.0.0.1'
PORT = 42135

if __name__ == '__main__':
    llm_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    llm_client.connect((HOST, PORT))

    stop_flag = False
    while not stop_flag:
        user_input = input("请输入要处理的文本: ")
        if  user_input == "exit":
            stop_flag = True
            continue
        
        print("正在处理...")
        llm_client.sendall(user_input.encode('utf-8'))

    llm_client.close()
