# 功能介绍

这是一个AI聊天机器人， 由 ASR（语音识别模型） + LLM（大语言模型） + TTS（文本转语音模型） 组成。
其中，ASR是运行在本地的 faster_whisper 模型，LLM是云端的 千问3 模型，TTS是运行在本地的 GPT-SoVITS 模型。

需要的硬件资源有： >=8G显存的NVIDIA显卡、麦克风、扬声器（最好是耳机，可以避免回声）。

# 安装
要运行这个项目， 还需要python运行环境、千问3的API密钥、faster_whisper的模型、GPT-SoVITS的模型。
具体安装方法请参考`使用说明书.txt`。

**安装显卡加速库**  
先安装显卡驱动，然后安装CUDA，最后安装CUDNN；（具体操作请查看`gpu加速库安装步骤.txt`文件）

**安装python运行环境**
点此下载[python运行环境]()

**安装TTS所需的 gpt-sovit模型**  
点此下载[gpt-sovit整合包](https://huggingface.co/lj1995/GPT-SoVITS-windows-package/resolve/main/GPT-SoVITS-v3lora-20250228.7z?download=true)。也可前往`https://github.com/RVC-Boss/GPT-SoVITS`下载， 并放在`gptsovits`文件夹内。

**获取LLM所需的API密钥**  
到阿里云百练`https://bailian.console.aliyun.com`, 注册账号，获取APIKEY。

**下载ASR所需的模型**  
到魔搭社区下载语音识别模型， `https://www.modelscope.cn/models/keepitsimple/faster-whisper-large-v3/files`, 然后放到`model/faster-whisper-large-v3`


# 使用
双击`app.bat`运行`命令行菜单`，设置好必要的参数后即可运行聊天机器人。  

`命令行菜单`会在`gptsovits/xxx/GPT_weights_v2`和`gptsovits/xxx/SoVITS_weights_v2`内搜索可以的模型，如果在设置参数时提示没有可用的模型，则请先训练模型。

### 训练新语音模型 （使用 gptsovits的webui）

1) 启动网页操作界面，到`./gptsovits/xxx`目录下，双击运行`go-webui.bat`

2) 切分音频，假设音频集不需要去除背景音，口齿清晰； 在"0-前置数据集获取工具" --> "0b-语音切分工具" --> "音频自动切分输入路径，
	可文件可文件夹" 输入你的音频文件夹路径, 然后点"开启语音切分"
		
3) 语音识别，"0c-语音识别工具" --> "输入文件夹路径"，输入你的音频文件夹路径, 然后点"开启语音识别"

4) 语音文本校对，"0d-语音文本校对标注工具" 然后点 "开启音频标准WebUI"

5) 填写[1-GPT-SoVITS-TTS/1A-训练集格式化工具/实验模型名]，[1Aabc-训练集格式化工具]，单击一键3连

6) [1-GPT-SoVITS-TTS/1B-微调训练/1Ba-SoVITS 训练] 开启SoVITS训练，等待[SoVITS训练进程输出信息]输出"SoVITS训练已完成"

7) [1-GPT-SoVITS-TTS/1B-微调训练/1Bb-GPT 训练] 开启GPT训练，等待[GPT训练进程输出信息]输出"GPT训练已完成"，训练完成后的模型会放在gptsovits目录下的`GPT_weights_v2`和`SoVITS_weights_v2`内。

8) 选择[1-GPT-SoVITS-TTS/1C-推理]; 选择两个模型；单击开启TTS推理WebUI

9) 选择两个模型；上传主参考音频，输入主参考音频的文本；输入需要合成的文本，单击开始合成，试听效果。


### 调整角色的说话方式

修改`llm/提示词.txt`文件即可

