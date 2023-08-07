import base64
import io
from PIL import Image
import gradio as gr
import numpy as np
from fastapi import FastAPI, Body
from fastapi.exceptions import HTTPException
from scripts.fastload import viewSaveDataExecute


def controlnet_api(_: gr.Blocks, app: FastAPI):
    @app.get("/controlnetFastload/version")
    async def version():
        return {"version": 1}

    @app.post("/controlnetFastload/load")
    async def load(
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
                status_code=422, detail="An error occured: " + str(e)
            )
        return {
            "pic_list": base64_pic_list,
            "info_list": info_dict
        }


try:
    import modules.script_callbacks as script_callbacks

    script_callbacks.on_app_started(controlnet_api)
except:
    pass
