import os
import re
import gzip
import pickle
import base64
import importlib
import gradio as gr
import numpy as np
from PIL import Image
from typing import Optional, List
from datetime import datetime
from gradio import Checkbox, Dropdown, File, Textbox, Button, Gallery, JSON
import modules.scripts as scripts
from modules import script_callbacks
from modules.script_callbacks import ImageSaveParams
from modules.shared import opts, cmd_opts
from modules.images import read_info_from_image
from modules.processing import process_images, Processed
import modules.generation_parameters_copypaste as parameters_copypaste

save_flag = False
controlNetList = []
save_filetype = ""
overwrite_flag = ""
start_marker = b'###START_OF_CONTROLNET_FASTLOAD###'
end_marker = b'###END_OF_CONTROLNET_FASTLOAD###'
current_timestamp = lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]
print_err = lambda msg: print(f'{current_timestamp()} - ControlNetFastload - \033[91mERROR\033[0m - {msg}')
print_warn = lambda msg: print(f'{current_timestamp()} - ControlNetFastload - \033[93mWARNING\033[0m - {msg}')
print_info = lambda msg: print(f'{current_timestamp()} - ControlNetFastload - \033[92mINFO\033[0m - {msg}')


class ControlNetFastLoad(scripts.Script):
    """
    插件的主类, 继承自scripts.Script
    参见https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/Developing-extensions
    """

    def __init__(self):
        pass

    def title(self) -> str:
        return "ControlNet Fastload"

    def show(self, is_img2img: bool) -> bool:
        return scripts.AlwaysVisible

    def ui(self, is_img2img: bool) -> list[Checkbox | Dropdown | File | Textbox | Button | Gallery | JSON]:
        ui_list = []
        with (gr.Accordion("ControlNet Fastload v1.2.0.3", open=False, elem_id=self.elem_id(""))):
            with gr.Tab("Load data from file"):
                with gr.Row():
                    enabled = gr.Checkbox(value=False, label="Enable", elem_id=self.elem_id("cnfl_enabled"))
                    mode = gr.Dropdown(["Load Only", "Save Only", "Load & Save"], label="Mode",
                                       value="Load Only", elem_id=self.elem_id("cnfl_mode"))
                    ui_list.extend([enabled, mode])
                    # 在这里, load代表仅重写controlnet, save代表仅重写生成后的图片
                    # load&save仅能在controlnet全部未启用情况下使用, 其会加载传入controlnet, 重写controlnet, 重写生成后的图片
                with gr.Row():
                    # 出于引用关系, gr.Textbox放到这里
                    png_other_info = gr.Textbox(visible=False, elem_id="pnginfo_generation_info")
                    uploadFile = gr.File(type="file", label="Upload Image or .cni file",
                                         file_types=["image", ".cni"], elem_id=self.elem_id("cnfl_uploadImage"))
                    uploadFile.upload(
                        fn=uploadFileListen,
                        inputs=[uploadFile, enabled],
                        outputs=png_other_info
                    )
                    ui_list.extend([uploadFile, png_other_info])
                # 测试填充整个参数
                with gr.Row():
                    # 保持统一, 参见https://github.com/AUTOMATIC1111/stable-diffusion-webui/issues/11210
                    visible_ = opts.data.get("isEnabledManualSend")
                    visible_ = False if visible_ is None else visible_
                    send_to_txt2img = gr.Button(label="Send to txt2img", value="Send to txt2img",
                                                elem_id=self.elem_id("send_to_txt2img"),
                                                visible=((not is_img2img) and visible_))
                    send_to_img2img = gr.Button(label="Send to img2img", value="Send to img2img",
                                                elem_id=self.elem_id("send_to_img2img"),
                                                visible=(is_img2img and visible_))
                    parameters_copypaste.register_paste_params_button(parameters_copypaste.ParamBinding(
                        paste_button=send_to_txt2img, tabname="txt2img", source_text_component=png_other_info,
                        source_image_component=None,
                    ))
                    parameters_copypaste.register_paste_params_button(parameters_copypaste.ParamBinding(
                        paste_button=send_to_img2img, tabname="img2img", source_text_component=png_other_info,
                        source_image_component=None,
                    ))
                    ui_list.extend([send_to_txt2img, send_to_img2img])
            with gr.Tab("View saved data"):
                with gr.Row():
                    execute_view_tab = gr.Button(label="Execute", elem_id=self.elem_id("cnfl_execute_view_tab"))
                with gr.Row():
                    uploadFile_view_tab = gr.File(type="file", label="Upload Image or .cni file",
                                                  file_types=["image", ".cni"],
                                                  elem_id=self.elem_id("cnfl_uploadImage_view_tab"))
                with gr.Row():
                    img_view_tab = gr.Gallery(type="file", label="Image data view",
                                              elem_id=self.elem_id("cnfl_img_view_tab"), rows=2, columns=2,
                                              allow_preview=True, show_download_button=True, object_fit="contain",
                                              show_label=True)
                with gr.Row():
                    text_view_tab = gr.Json(label="Text data view",
                                            elem_id=self.elem_id("cnfl_text_view_tab"))
                ui_list.extend([execute_view_tab, uploadFile_view_tab, img_view_tab, text_view_tab])
                execute_view_tab.click(
                    fn=viewSaveDataExecute,
                    inputs=[uploadFile_view_tab],
                    outputs=[img_view_tab, text_view_tab]
                )
        return ui_list

    def before_process(self, p, *args) -> None:
        # con1 = importlib.import_module('scripts.global_state')
        api_module = importlib.import_module('extensions.sd-webui-controlnet-fastload.scripts.api')
        api_package = getattr(api_module, "api_package")
        if type(args[0]) is not bool:
            enabled, mode, uploadFile = True, args[0]['mode'], args[0]['filepath']
            saveControlnet, overwritePriority = "", args[0]['overwritePriority']
            api_package.api_instance.enabled = True
            api_package.api_instance.drawId[id(p)] = []
            api_package.api_instance.info()
        else:
            enabled, mode, uploadFile = args[:3]
            saveControlnet, overwritePriority = opts.saveControlnet, opts.overwritePriority
        if enabled:
            # Load start
            try:
                global controlNetList
                break_load = False
                controlNetModule = importlib.import_module('extensions.sd-webui-controlnet.scripts.external_code',
                                                           'external_code')
                # from scripts.controlnet_ui.controlnet_ui_group import ControlNetUiGroup, UiControlNetUnit
                # con = importlib.import_module('scripts.controlnet_ui.controlnet_ui_group')
                # 获取最原始的controlnetList
                controlNetList = controlNetModule.get_all_units_in_processing(p)
                controlNetListOriLen = len(controlNetList)
                controlNetListIsEmpty = not (any(itm.enabled for itm in controlNetList))
                # 上传文件是否为空, 若为空则不能加载文件
                if uploadFile is None and (mode == "Load Only" or mode == "Load & Save"):
                    print_warn("Script received no input; the loading process will be skipped.")
                    break_load = True
            except ImportError:
                print_warn("ControlNet not found; the script will not work.")
                # proc = process_images(p)
                # return proc
                return
            if (mode == "Load Only" or mode == "Load & Save") and not break_load:
                load_file_name_ = uploadFile if isinstance(uploadFile, str) else uploadFile.name
                # 更新controlnetList
                if controlNetListIsEmpty:
                    controlNetList = loadFromFile(load_file_name_)
                else:
                    if overwritePriority == "ControlNet Plugin First":
                        print_warn("The plugin is not empty and has priority; the script will not work.")
                    else:
                        print_warn("The plugin is not empty, but the script has priority;"
                                   " it will overwrite the existing Controlnet plugin data.")
                        controlNetList = loadFromFile(load_file_name_)
                if len(controlNetList) > controlNetListOriLen:
                    print_warn("The ControlNet count in the file exceeds the current setting;"
                               " this might cause an error.")
                # 重写controlnet
                controlNetModule.update_cn_script_in_processing(p, controlNetList)
            if mode == "Save Only" or mode == "Load & Save":
                global save_flag, save_filetype
                save_flag = True
                save_filetype = saveControlnet
                if api_package.api_instance.enabled:
                    api_package.api_instance.drawId[id(p)] = controlNetList

    def postprocess_image(self, p, pp, *args):
        # con = importlib.import_module('scripts.controlnet_ui.controlnet_ui_group')
        # con1 = importlib.import_module('scripts.global_state')
        if type(args[0]) is not bool and args[0]['mode'] != "Load Only":
            p.extra_generation_params['ControlNetID'] = id(p)


def uploadFileListen(pic: gr.File, enabled: bool) -> str:
    """
    从上传的图片/文件中提取出PNG_INFO后传回, 参考自from modules.extras import run_pnginfo
    :param pic: 上传的图片/文件, 以包装好的gr.File形式传入
    :param enabled: (主插件)是否启用, 未启用直接返回空字符串
    :return: str: read_info_from_image函数返回值, 返回给一个textbox
    """
    if not pic:
        return ""
    filetype_is_cni = lambda filename: os.path.splitext(pic.name)[1] == '.cni'
    if filetype_is_cni(pic.name) or not enabled:
        return ""
    fileInPil = Image.open(pic.name)
    gen_info, items = read_info_from_image(fileInPil)
    print(gen_info)
    return gen_info


def judgeControlnetDataFile(filepath: str, filepathWeb: str) -> str:
    """
    传入图片文件地址,判断controlnet数据存在于图片文件/.同名cni文件
    :param filepath: 图片文件地址
    :param filepathWeb: 图片文件地址(网页端)
    :return filepath(修改后): 含有controlnet数据文件地址
    """
    urlStart = re.search(r'^(.*?)/file=', filepathWeb).group(1)
    cnList = loadFromFile(filepath, False)
    cniFilePath = filepath[:-4] + ".cni"
    if len(cnList) > 0:
        return filepathWeb
    elif len(cnList) == 0 and os.path.exists(cniFilePath):
        cnList = loadFromFile(cniFilePath, False)
        return f"{urlStart}/file={filepath[:-4]}.cni" if len(cnList) > 0 else ""
    else:
        return ""


def viewSaveDataExecute(file: gr.File or str) -> tuple:
    """
    查看本插件存储在图片/.cni中的数据
    :param file: 上传的图片/文件, 以包装好的gr.File/str形式传入
    :return: tuple: (list, list)  参见下面和ui渲染部分, 这个tuple喂给两个ui组件
    """
    try:
        if file is None:
            print_warn("You did not upload an image or file.")
            return [], {"Error": "You did not upload an image or file."}
        file_name_ = file if isinstance(file, str) else file.name
        tmpControlNetList = loadFromFile(file_name_)
        previewPicture = []
        previewInformation = []
        loop_count = 0
        for itm in tmpControlNetList:
            tmp = itm if isinstance(itm, dict) else vars(itm)
            if "image" in tmp and tmp["image"] is not None:
                if isinstance(tmp["image"], np.ndarray):
                    image_arrays = [(tmp["image"], f"Controlnet - {loop_count}")]
                else:
                    image_arrays = [(img_array, f"Controlnet - {loop_count}") for img_array in tmp["image"].values()]
                previewPicture.extend(image_arrays)
                tmp.pop("image")
            previewInformation.append(tmp)
            loop_count += 1
        return previewPicture, previewInformation
    except Exception as e:
        print_err(e)
        return [], {"Error": "An unknown error occurred, see the console for details"}


def addToPicture(image: str, datalist: list, imageType: str) -> bytes | None:
    """
    将ControlnetList经过gzip压缩后序列化存入图片中
    :param image: 和type挂钩
    :param datalist: ControlnetList
    :param imageType: "filepath" / "base64"
    """
    if imageType == "filepath" and (not os.path.exists(image)):
        print_err(f"File {image} does not exist.")
        return
    serialized_data = gzip.compress(pickle.dumps(datalist))
    if imageType == "filepath":
        with open(image, 'rb') as img_file:
            image_data = img_file.read()
    else:
        image_data = base64.b64decode(image)
    combined_data = image_data + start_marker + serialized_data + end_marker
    if imageType == "filepath":
        with open(image, 'wb') as img_file:
            img_file.write(combined_data)
    else:
        return base64.b64encode(combined_data)


def loadFromFile(filepath: str, enableWarn: Optional[bool] = None) -> list:
    """
    从图片中读取ControlnetList
    :param filepath: 图片路径
    :param enableWarn 是否报错
    """
    if not os.path.exists(filepath):
        print_err(f"File {filepath} does not exist.") if enableWarn is None else None
        return [{"Error": f"File {filepath} does not exist."}]
    with open(filepath, 'rb') as fp:
        readyLoadData = fp.read()
    start_idx = readyLoadData.find(start_marker) + len(start_marker)
    end_idx = readyLoadData.find(end_marker)
    try:
        embedded_data = gzip.decompress(readyLoadData[start_idx:end_idx])
        # 判定存入的controlnet和现有的controlnet数量差异
        readyLoadList = pickle.loads(embedded_data)
        return readyLoadList
    except gzip.BadGzipFile:
        print_err(f"{filepath} does not contain valid Controlnet Fastload data.") if enableWarn is None else None
        return [{"Error": f"{filepath} does not contain valid Controlnet Fastload data."}]
    except Exception as e:
        print_err(f"Error while loading Controlnet Fastload data from the image: {e}") if enableWarn is None else None
        return [{"Error": f"Error while loading Controlnet Fastload data from the image: {e}"}]


# 保存图片钩子
def afterSavePicture(img_save_param: ImageSaveParams) -> None:
    """
    保存图片后的钩子函数, 用于将ControlnetList写入图片中
    注意这个函数并不能被api调用
    :param img_save_param: 参见script_callbacks.py
    """
    # 在这里已经知道生成图像所在位置了,直接写入数据
    if save_flag:
        filepath = os.path.join(os.getcwd(), img_save_param.filename)
        filepath_pure, _ = os.path.splitext(filepath)
        if save_filetype == "Embed photo" or save_filetype == "Both":
            addToPicture(filepath, controlNetList, "filepath")
        if save_filetype == "Extra .cni file" or save_filetype == "Both":
            with open(filepath_pure + ".cni", 'wb'):
                pass
            addToPicture(filepath_pure + ".cni", controlNetList, "filepath")
        print_info(f"ControlNet data saved to {filepath}")


script_callbacks.on_image_saved(afterSavePicture)
