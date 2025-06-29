import os
import json

if __name__ == '__main__':

    # 获取当前脚本的绝对路径
    current_script_path     = os.path.abspath(__file__)
    current_directory       = os.path.dirname(current_script_path)

    # 列出`gptsovits`目录下的所有目录，并更新第一个目录为gptsovits的文件夹
    sovits_dir = os.path.join(current_directory, 'gptsovits')
    for entry in os.listdir(sovits_dir):
        full_path = os.path.join(sovits_dir, entry)
        # 如果是一个目录，则打印其名字
        if os.path.isdir(full_path):
            sovits_dir = full_path
            break

    # 生成path_location.json文件, 把当前dir写入json文件
    json_file_path  = os.path.join(current_directory, 'path_location.json')
    json_data = {
        "base_dir":             current_directory,
        "json_file":            json_file_path,
        "config_file":          os.path.join(current_directory, 'config.json'),
        "gpt_sovits_dir":       sovits_dir,
        "gpt_sovits_python_interpreter":    os.path.join(sovits_dir, "runtime\\python.exe"),
        "gpt_sovits_pai_server":            os.path.join(sovits_dir, "my_api_v2.py"),
        "python_interpreter":   os.path.join(current_directory, 'env\\ltai\\python.exe'), # 使用windows风格的路径
        "sel_audio_dev":        os.path.join(current_directory, "tts\\sel_audio_dev.py"),
        "asr_server":           os.path.join(current_directory, "asr\\ASR_faster_whisper.py"),
        "llm_server":           os.path.join(current_directory, "llm\\LLM_api_qwen.py"),
        "tts_server":           os.path.join(current_directory, "tts\\TTS_gptsovits.py"),
    }
    with open(json_file_path, 'w') as json_file:
        json.dump(json_data, json_file, indent=4)

    # 生成config.json文件
    cfg_file_path = os.path.join(current_directory, 'config.json')
    defult_config = {
        # 知道默认值的配置项
        "audio_device_index":           -1,
        "tts_speed_factor":             1.0,
        # 不知道默认值的配置项
        "gpt_weights_v2":               "not_set",
        "sovits_weights_v2":            "not_set",
        "tts_ref_audio_relative_path":  "not_set",
        "tts_ref_audio_text":           "not_set",
        "api_key":                      "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    }
    # 检查文件是否存在
    if not os.path.exists(cfg_file_path):
        with open(cfg_file_path, "w") as f:
            json.dump(defult_config, f, indent=4)
    else:
        # 检查必要的key是否存在，若不存在则添加
        with open(cfg_file_path, "r") as f:
            cfg_jf = json.load(f)
        for key in defult_config.keys():
            if key not in cfg_jf.keys():
                def_val = defult_config[key]
                print(f"{key} 没有找到，已添加为默认值 {def_val}")
                cfg_jf[key] = def_val
        with open(cfg_file_path, "w") as f:
            json.dump(cfg_jf, f, indent=4)
    # 后续会在 config_file.py 的 check_config_file 作进一步的检查

    # cmd 文件生成
    with open(os.path.join(current_directory, 'cmd_app'), 'w') as cmd_file:
        # cmd_file.write(f'"{json_data["python_interpreter"]}" "{json_data["base_dir"]}\\app.py"')
        cmd_file.write(f'"{json_data["python_interpreter"]}" "{json_data["base_dir"]}\\cmd_menu.py"')


def get_path_python_interpreter():
    with open("path_location.json", "r", encoding="utf-8") as f:
        j = json.load(f)
        path = j['python_interpreter']
    return path

def join_base_dir(relative_path):
    with open("path_location.json", "r", encoding="utf-8") as f:
        j = json.load(f)
        path = j['base_dir']
    return os.path.join(path, relative_path)

def join_gptsovits_dir(relative_path):
    with open("path_location.json", "r", encoding="utf-8") as f:
        j = json.load(f)
        path = j['gpt_sovits_dir']
    return os.path.join(path, relative_path)


def get_path(key):
    with open("path_location.json", "r", encoding="utf-8") as f:
        j = json.load(f)
        path = j[key]
    return path
