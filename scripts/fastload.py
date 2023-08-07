import os
import gzip
import pickle
import importlib
import gradio as gr
from datetime import datetime
import modules.scripts as scripts
from modules import script_callbacks
from modules.processing import process_images

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


class Script(scripts.Script):
    def __init__(self):
        pass

    def title(self):
        return "ControlNet Fastload"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def ui(self, is_img2img):
        ui_list = []
        with (gr.Accordion("ControlNet Fastload", open=False)):
            with gr.Tab("Load data from file"):
                with gr.Row():
                    enabled = gr.Checkbox(value=False, label="Enable", elem_id=self.elem_id("cnfl_enabled"))
                    mode = gr.Dropdown(["Load Only", "Save Only", "Load & Save"], label="Mode",
                                       value="Load Only", elem_id=self.elem_id("cnfl_mode"))
                    ui_list.extend([enabled, mode])
                    # 在这里, load代表仅重写controlnet, save代表仅重写生成后的图片
                    # load&save仅能在controlnet全部未启用情况下使用, 其会加载传入controlnet, 重写controlnet, 重写生成后的图片
                with gr.Row():
                    with gr.Column():
                        saveControlnet = gr.Radio(["Embed photo", "Extra .cni file", "Both"],
                                                  label="Save Controlnet Data in ...",
                                                  info="Where to save Controlnet data?",
                                                  value="Extra .cni file", elem_id=self.elem_id("cnfl_saveControlnet"))
                    with gr.Column():
                        overwritePriority = gr.Radio(["Plugin first", "Script first"],
                                                     label="Overwrite priority",
                                                     info="If the ControlNet Plugin is enabled, which do you use first?",
                                                     value="Plugin first",
                                                     elem_id=self.elem_id("cnfl_overwritePriority"))
                    with gr.Column():
                        uploadFile = gr.File(type="file", label="Upload Image or .cni file",
                                             elem_id=self.elem_id("cnfl_uploadImage"))
                    ui_list.extend([saveControlnet, overwritePriority, uploadFile])
            with gr.Tab("View saved data"):
                with gr.Row():
                    execute_view_tab = gr.Button(label="Execute", elem_id=self.elem_id("cnfl_execute_view_tab"))
                with gr.Row():
                    uploadFile_view_tab = gr.File(type="file", label="Upload Image or .cni file",
                                                  elem_id=self.elem_id("cnfl_uploadImage_view_tab"))
                with gr.Row():
                    img_view_tab = gr.Gallery(type="file", label="Image data view",
                                              elem_id=self.elem_id("cnfl_img_view_tab")).style(rows=2, columns=2,
                                                                                               allow_preview=True,
                                                                                               show_download_button=True,
                                                                                               object_fit="contain",
                                                                                               height="auto", show_label=True)
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

    def before_process(self, p, *args):
        enabled, mode, saveControlnet, overwritePriority, uploadFile = args[:5]
        if enabled:
            # Load start
            try:
                global controlNetList
                break_load = False
                controlNetModule = importlib.import_module('extensions.sd-webui-controlnet.scripts.external_code',
                                                           'external_code')
                # 获取最原始的controlnetList
                controlNetList = controlNetModule.get_all_units_in_processing(p)
                controlNetListOriLen = len(controlNetList)
                controlNetListIsEmpty = not (any(itm.enabled for itm in controlNetList))
                # 上传文件是否为空, 若为空则不能加载文件
                if uploadFile is None and (mode == "Load Only" or mode == "Load & Save"):
                    print_warn("Script received no input; the loading process will be skipped.")
                    break_load = True
            except ImportError:
                print_warn("ControlNet module not found; the script will not work.")
                proc = process_images(p)
                return proc
            if (mode == "Load Only" or mode == "Load & Save") and not break_load:
                load_file_name_ = uploadFile if isinstance(uploadFile, str) else uploadFile.name
                # 更新controlnetList
                if controlNetListIsEmpty:
                    controlNetList = loadFromFile(load_file_name_)
                else:
                    if overwritePriority == "Plugin first":
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


def viewSaveDataExecute(file):
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
            tmp = vars(itm)
            if "image" in tmp and tmp["image"] is not None:
                image_arrays = [(img_array, f"Controlnet - {loop_count}") for img_array in tmp["image"].values()]
                previewPicture.extend(image_arrays)
                tmp.pop("image")
            previewInformation.append(tmp)
            loop_count += 1
        return previewPicture, previewInformation
    except Exception as e:
        print_err(e)
        return [], {"Error": "An unknown error occurred, see the console for details"}


def addToPicture(imagePath, datalist):
    serialized_data = gzip.compress(pickle.dumps(datalist))
    with open(imagePath, 'rb') as img_file:
        image_data = img_file.read()
    combined_data = image_data + start_marker + serialized_data + end_marker
    with open(imagePath, 'wb') as img_file:
        img_file.write(combined_data)


def loadFromFile(filepath):
    with open(filepath, 'rb') as fp:
        readyLoadData = fp.read()
    start_idx = readyLoadData.find(start_marker) + len(start_marker)
    end_idx = readyLoadData.find(end_marker)
    try:
        embedded_data = gzip.decompress(readyLoadData[start_idx:end_idx])
        # 判定存入的controlnet和现有的controlnet数量差异
        readyLoadList = pickle.loads(embedded_data)
        return readyLoadList
    except Exception as e:
        print_err(f"Error while loading hidden data from the image: {e}")
        return []


# 保存图片钩子
def afterSavePicture(img_save_param):
    # 在这里已经知道生成图像所在位置了,直接写入数据
    if save_flag:
        filepath = os.path.join(os.getcwd(), img_save_param.filename)
        filepath_pure, _ = os.path.splitext(filepath)
        if save_filetype == "Embed photo" or save_filetype == "Both":
            addToPicture(filepath, controlNetList)
        if save_filetype == "Extra .cni file" or save_filetype == "Both":
            with open(filepath_pure + ".cni", 'wb'):
                pass
            addToPicture(filepath_pure + ".cni", controlNetList)
        print_info(f"ControlNet data saved to {filepath}")


script_callbacks.on_image_saved(afterSavePicture)
