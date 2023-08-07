# sd-webui-controlnet-fastload
一个用于 `stable-diffusion-webui` 的扩展。    
[English Documentation](README.md)
## 功能
- 可以保存[Controlnet插件](https://github.com/Mikubill/sd-webui-controlnet)的参数
- 将Controlnet参数直接嵌入到图像中或保存在单独的文件中,以便分享
- 从嵌入Controlnet参数的图片或文件快速加载参数到txt2img或img2img中

## 预览
![preview_1.png](preview_1.png)
![preview_2.png](preview_2.png)

## 使用方法
### 用户界面
从"Script"中选择"ControlNet Fastload", 选好后就能用

### API

#### 通过 `/sdapi/v1/txt2img` 或 `/sdapi/v1/img2img`
通过在`/sdapi/v1/txt2img`或`/sdapi/v1/img2img`中的参数加入`script_name`和`script_args` 实现, 详情参考[这里](https://github.com/mix1009/sdwebuiapi/commit/fe269dc2d4f8a98e96c63c8a7d3b5f039625bc18)
传入 `script_args` 时，请按照**先后顺序+仅传值**的原则传入
`script_args` 的五个参数：
- enabled: (bool)
- mode: (str: "Load & Save", "Load only", "Save only")
- saveControlnet: (str: "Embed photo", "Extra .cni file", "Both")
- overwritePriority: (str, "Plugin first")
- uploadFile: (str, {传入图片/文件路径})

以下是一个简短的Python示例：
```python
import io
import base64
import requests
from PIL import Image

path = 'api_test1.png'
prompt = '1girl'
# 这里改成你的本地地址
url = "http://localhost:1145/sdapi/v1/txt2img" 

body = {
    "prompt": prompt,
    "negative_prompt": "",
    "batch_size": 1,
    "steps": 20,
    "cfg_scale": 7,
    "script_name": "ControlNet Fastload",
    "script_args": [True, "Load & Save", "Both", "Script first", "D:\\stable-diffusion-webui\\outputs\\txt2img-images\\2023-08-07\\00007-285657811.cni"]
}

response = requests.post(url=url, json=body)
output = response.json()
result = output['images'][0]
image = Image.open(io.BytesIO(base64.b64decode(result.split(",", 1)[1])))
image.show()
```
#### 通过 `/controlnetFastload/load`

参数包括：
- filepath: (str, {您的文件路径})   
- except_type: (str: "base64", "nparray")   

详情参见：{sd-webui-本地网址}/docs#/default/load_controlnetFastload_load_post