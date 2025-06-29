import json
import os
import path_location


# 加载配置文件
path_config_file = path_location.get_path('config_file')

# 检查配置文件内的必要参数是否已经设置
def check_config_file():
    result = True

    with open(path_config_file, "r", encoding="utf-8") as f:
        jf = json.load(f)
    
    nessary_keys = {
        "gpt_weights_v2":               "not_set",
        "sovits_weights_v2":            "not_set",
        "tts_ref_audio_relative_path":  "not_set",
        "tts_ref_audio_text":           "not_set",
        "api_key":                      "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    }

    for key, val in nessary_keys.items():
        if jf[key] == val:
            # print(f"{key} is default, please set it. ")
            print(f"{key} 未设置，请先到 参数设置 设定。")
            result = False
    
    return result


def set_config_value(key, value):
    with open(path_config_file, "r", encoding="utf-8") as f:
        jf = json.load(f)
    jf[key] = value
    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(jf, f, indent=4)
    print(f"{key} has been set to {value}")

def get_config_value(key):
    with open(path_config_file, "r", encoding="utf-8") as f:
        jf = json.load(f)
    if key in jf: 
        return jf[key] 
    else:
        return None
