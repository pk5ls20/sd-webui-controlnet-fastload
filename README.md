# sd-webui-controlnet-fastload
An extension for `stable-diffusion-webui`.    
[中文文档](README_zh_CN.md)   
## Features
- Save parameters in the [Controlnet plugin](https://github.com/Mikubill/sd-webui-controlnet).
- Embed Controlnet parameters directly into the image or save in a separate file for sharing.
- Quickly load parameters from an image or file embedded with Controlnet parameters to txt2img or img2img.

## Preview
![preview_1.png](preview_1.png)
![preview_2.png](preview_2.png)

## Usage
### UI
Choose "ControlNet Fastload" from the "Script" checkbox. Once selected, the script activates.

### API

#### via `/sdapi/v1/txt2img` or `/sdapi/v1/img2img`
To utilize, append the `script_name` and `script_args` parameters. Refer to [this commit](https://github.com/mix1009/sdwebuiapi/commit/fe269dc2d4f8a98e96c63c8a7d3b5f039625bc18) for comprehensive details. 

When providing `script_args`, ensure you:
- Adhere to the correct sequence.
- Only pass in the actual values.

The five parameters for `script_args` are:
- enabled: (bool)
- mode: (str options: "Load & Save", "Load only", "Save only")
- saveControlnet: (str options: "Embed photo", "Extra .cni file", "Both")
- overwritePriority: (str, "Plugin first")
- uploadFile: (str, {Your filepath})

Here's a brief example in Python:

```python
import io
import base64
import requests
from PIL import Image

path = 'api_test1.png'
prompt = '1girl'
# Change here to your local URL
url = "http://localhost:7860/sdapi/v1/txt2img"

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

#### via `/controlnetFastload/load`
Parameters include:
- filepath: (str, {Your filepath})
- except_type: (str options: "base64", "nparray")

For additional information, visit: {your local url}/docs#/default/load_controlnetFastload_load_post
