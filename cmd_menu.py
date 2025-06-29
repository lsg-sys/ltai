import subprocess
import json
import os
import shutil

import path_location
import config_file

import pyaudio

# current_script_path = os.path.abspath(__file__)
# current_directory = os.path.dirname(current_script_path)
# os.chdir(current_directory)

# 子进程默认使用的Python解释器
py_interpreter = path_location.get_path_python_interpreter()

def exit_func():
    print("程序已退出。")
    exit()

def copy_my_api_file_to_tts():
    # 复制my_api_v2.py到gptsovits目录下；若已经存在则覆盖
    src_file_path = path_location.join_base_dir("my_api_v2.py")
    dst_file_path = path_location.join_gptsovits_dir("my_api_v2.py")
    # 确保目标目录存在
    os.makedirs(os.path.dirname(dst_file_path), exist_ok=True)
    # 复制文件（若已存在则覆盖）
    shutil.copy2(src_file_path, dst_file_path)

def start_chat_bot():
    if True == config_file.check_config_file():
        copy_my_api_file_to_tts()
        subprocess.run([py_interpreter, "app.py"])

def start_asr():
    subprocess.run([py_interpreter, path_location.get_path("asr_server")])

def start_llm():
    if True == config_file.check_config_file():
        subprocess.run([py_interpreter, path_location.get_path("llm_server")])

def start_tts():
    if True == config_file.check_config_file():
        copy_my_api_file_to_tts()
        subprocess.run([py_interpreter, path_location.get_path("tts_server")])

def change_audio_device():
    sel_audio_dev = path_location.get_path("sel_audio_dev")
    subprocess.run([py_interpreter, sel_audio_dev])

def change_audio_device_dynamic_name(original_name) -> str:
    dev_index = config_file.get_config_value("audio_device_index")
    if dev_index < 0:
        return original_name + "        当前选择了： 默认扬声器设备"
    else:
        audio = pyaudio.PyAudio()
        dev_name = audio.get_device_info_by_index(dev_index)["name"]
        audio.terminate()
        return original_name + "        当前选择了： " + dev_name

def change_gpt_weights_v2():
    subprocess.run(["python", "sel_gpt_weights_v2.py"])
    
def change_gpt_weights_dynamic_name(original_name) -> str:
    file_name = config_file.get_config_value("gpt_weights_v2")
    return original_name + "        当前选择了： " + file_name

def change_sovits_weights_v2():
    subprocess.run(["python", "sel_sovits_weights_v2.py"])
    
def change_sovits_weights_dynamic_name(original_name) -> str:
    file_name = config_file.get_config_value("sovits_weights_v2")
    return original_name + "        当前选择了： " + file_name

def change_tts_ref_audio_path():
    ref_file_path = input("请输入参考音频文件的路径：")
    if not os.path.exists(ref_file_path):
        print("文件不存在")
        return
    else:
        config_file.set_config_value("tts_ref_audio_relative_path", ref_file_path)

def change_tts_ref_audio_path_dynamic_name(original_name) -> str:
    ref_file_name = config_file.get_config_value("tts_ref_audio_relative_path")
    return original_name + "        当前选择了： " + ref_file_name

def change_tts_ref_audio_text():
    ref_text = input("请输入参考音频的文字：")
    if ref_text == "":
        print("已取消")
    else:
        config_file.set_config_value("tts_ref_audio_text", ref_text)
        

def change_tts_ref_audio_text_dynamic_name(original_name) -> str:
    ref_text = config_file.get_config_value("tts_ref_audio_text")
    return original_name + "        当前选择了： " + ref_text

def change_api_key():
    ref_text = input("请输入API_KEY：")
    if ref_text == "":
        print("已取消")
    else:
        config_file.set_config_value("api_key", ref_text)
        

def change_api_key_dynamic_name(original_name) -> str:
    ref_text = config_file.get_config_value("api_key")
    return original_name + "        当前的KEY是： " + ref_text



# 菜单的数据结构规则
# - 元素格式: [选项名称，obj，（可选，动态名称获取函数）]
# - obj元素解释: (list-->cmd， func-->call，str-->control)
cmd_menu_list = [
    ["退出程序",        exit_func],
    ["启动聊天机器人",  start_chat_bot],
    ["参数设置", [
        ["返回", "return"],
        ["输出的扬声器设备", change_audio_device, change_audio_device_dynamic_name],
        ["GPT权重模型", change_gpt_weights_v2, change_gpt_weights_dynamic_name],
        ["SoVITS权重模型", change_sovits_weights_v2, change_sovits_weights_dynamic_name],
        ["参考音频", change_tts_ref_audio_path, change_tts_ref_audio_path_dynamic_name],
        ["参考音频对应的文本", change_tts_ref_audio_text, change_tts_ref_audio_text_dynamic_name],
        ["API_KEY", change_api_key, change_api_key_dynamic_name],
    ]],
    ["调试", [
        ["返回", "return"],
        ["启动 自动语音识别（ASR）", start_asr],
        ["启动 大语音模型（LLM）", start_llm],
        ["启动 文本转语音（TTS）", start_tts],
    ]],
]

def run_cmd_menu(menu_list, menu_path):
    while True:
        # 打印分割线, 菜单路径
        print("\n\n")
        print(f"当前位置： {menu_path} ")
        print("*===================================================*")
        # 打印菜单选项
        for i, item in enumerate(menu_list):
            # 检查是否为动态名称
            if 2 < len(item):
                print(f"{i}. {item[2](item[0])}")
            else:
                print(f"{i}. {item[0]}")
        # 处理用户输入
        user_input = input("\n请输入命令编号: ")
        print("+---------------------------+")
        # 检查用户输入是否为数字且小于菜单项数量
        if user_input.isdigit() and int(user_input) < len(menu_list):
            obj = menu_list[int(user_input)][1] # 获取选项对应的对象
            # 根据选项的类型执行相应的操作
            if type(obj) == list:
                cur_item_name = menu_list[int(user_input)][0]
                run_cmd_menu(obj, f"{menu_path} > {cur_item_name}")
            elif type(obj) == str:
                if obj == "return":
                    break
                else:
                    print(f"[ERROR] 程序内参数设定错误，{menu_list} 索引{int(user_input)}未设定其字符串 {obj} 的行为。")
            elif callable(obj):
                obj()
            else:
                print(f"[ERROR] 程序内参数设定错误，{menu_list} 索引{int(user_input)}为未知对象类型。")
        else:
            print("无效的命令编号")


run_cmd_menu(cmd_menu_list, "主菜单")

    