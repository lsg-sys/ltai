import socket
import threading
import time

# 服务器地址和端口
HOST = '127.0.0.1'
PORT = 57239

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

        buffer = ""  # 缓冲区用于拼接数据
        while True:
            print("等待数据...")
            data = llm_client.recv(4096).decode('utf-8')
            if not data:
                print("[ERROR] LLM 服务端断开连接")
                stop_flag = True
                break
            
            buffer += data
            # 如果遇到 [END]，停止接收并处理剩余文本
            if "[END]" in buffer:
                final_text, _, buffer = buffer.partition("[END]")
                if final_text:
                    print(f"[TTS] 最终回复内容: {final_text}")
                print("遇到 [END]\n")
                break

            # 将当前缓冲区中所有内容作为部分文本传给 TTS（可选：添加标点判断避免中途打断）
            if buffer:
                # print(f"[TTS] 接收到部分内容: {buffer}")
                # 检查str是否包含标点符号，若有，则从标点处截取
                # punctuation = ('。', '.', '，', ',', '？', '?', '！', '!')
                punctuation = ('。', '.', '？', '?', '！', '!')
                for p in punctuation:
                    # idx = buffer.find(p)
                    idx = buffer.rfind(p) # 从末尾开始查找
                    if idx != -1:
                        print(f"[TTS] 检测到句尾符号，开始合成: {buffer[:idx + 1]}")
                        buffer = buffer[idx + 1:]  # 更新 buffer 为剩余内容
                        break
    llm_client.close()
