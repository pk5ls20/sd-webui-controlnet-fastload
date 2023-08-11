import base64
import io
from PIL import Image
import gradio as gr
import numpy as np
from fastapi import FastAPI, Body
from fastapi.exceptions import HTTPException
from scripts.fastload import viewSaveDataExecute, addToPicture
import scripts.api_package as api_package
import modules.script_callbacks as script_callbacks


def controlnet_api(_: gr.Blocks, app: FastAPI):
    @app.get("/controlnetFastload/version")
    async def version():
        return {"version": 1.1}

    @app.post("/controlnetFastload/fetch")
    async def fetch(
            returnFileType: str = Body("Extra .cni file", title='returnType'),
            extraPicBase64: str = Body("", title='extraPicBase64'),
            ControlNetID: int = Body(title='ControlNetID')
    ):
        try:
            result_dict = {}
            controlnetList_ = api_package.api_instance.drawId[ControlNetID]
            # 先考虑extraPicBase64=="", 此时一定返回.cni
            if extraPicBase64 == "":
                result_dict['.cni'] = addToPicture("", controlnetList_, "base64")
            # 在考虑extraPicBase64!="", 此时要看returnFileType
            else:
                if returnFileType == "Embed photo":
                    result_dict['photo'] = addToPicture(extraPicBase64, controlnetList_, "base64")
                if returnFileType == "Extra .cni file":
                    result_dict['.cni'] = addToPicture(extraPicBase64, controlnetList_, "base64")
                if returnFileType == "Both":
                    result_dict['photo'] = addToPicture(extraPicBase64, controlnetList_, "base64")
                    result_dict['.cni'] = addToPicture(extraPicBase64, controlnetList_, "base64")
        except KeyError as e:
            raise HTTPException(
                status_code=422, detail="Controlnet not found: " + str(e)
            )
        except Exception as e:
            raise HTTPException(
                status_code=422, detail="An error occurred: " + str(e)
            )
        return result_dict

    @app.post("/controlnetFastload/view")
    async def view(
            filepath: str = Body("", title='filepath'),
            except_type: str = Body("base64", title='except_type')
    ):
        base64_pic_list = []
        if filepath == "":
            raise HTTPException(
                status_code=422, detail="No file uploaded")
        try:
            pic_list, info_dict = viewSaveDataExecute(filepath)
            for pic in pic_list:
                if except_type == "base64":
                    pic_ = Image.fromarray(pic)
                    io_ = io.BytesIO()
                    pic_.save(io_, format="PNG")
                    base64_pic_list.append(base64.b64encode(io_.getvalue()))
                elif except_type == "nparray":
                    base64_pic_list.append(np.array2string(pic))
                else:
                    raise HTTPException(
                        status_code=422, detail="except_type should be base64 or nparray")
        except Exception as e:
            raise HTTPException(
                status_code=422, detail="An error occurred: " + str(e)
            )
        return {
            "pic_list": base64_pic_list,
            "info_list": info_dict
        }


script_callbacks.on_app_started(controlnet_api)
