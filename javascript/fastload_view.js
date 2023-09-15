const delay = (timeout = 0) => new Promise((resolve) => setTimeout(resolve, timeout));
const appDoc = gradioApp();

const sendMsg = (isDebug, send_) => {
    return isDebug === "True"
        ? console.log(`Log ${send_}`)
        : alert(`Send to ${send_}`);
}

async function checkAccessToken(accessTokenInput, accessTokenRightSHA512) {
    const encoder = new TextEncoder();
    const data = encoder.encode(accessTokenInput);
    const hashArrayBuffer = await crypto.subtle.digest('SHA-512', data);
    const hash = Array.from(new Uint8Array(hashArrayBuffer))
        .map(b => b.toString(16).padStart(2, '0'))
        .join('');
    if (hash === accessTokenRightSHA512) {
        sendMsg("False", "You have access permission now!");
    } else {
        sendMsg("False", "You have no access permission!");
    }
    return [accessTokenInput, accessTokenRightSHA512]
}

//selectPicAddress, selectPicControlnetAddress, sendControlnetPriority, sendControlnetTxt2img, info
async function sendToAny2img(picAddress, controlnetAddress, priority, way, isDebug) {
    way = (way === "Send to Controlnet-txt2img") ? "txt2img" : "img2img";
    let fastloadElemId = (way === "txt2img") ? "script_txt2img_controlnet_fastload_" : "script_img2img_controlnet_fastload_";
    // priority === auto, 当controlnetAddress不为空发送到fastload, 否则controlnet
    let send_, status;
    (way === "txt2img") ? window.switch_to_txt2img() : window.switch_to_img2img();
    await delay(200);
    if (priority === "Auto") {
        if (controlnetAddress === "") {
            send_ = "Controlnet";
            status = await sendToControlnet(way, picAddress);
        } else {
            send_ = "Controlnet Fastload";
            status = await sendToControlnetFastload(way, controlnetAddress, fastloadElemId);
        }
        sendMsg(isDebug, status[1]);
    } else if (priority === "Controlnet First") {
        status = await sendToControlnet(way, picAddress);
        // 这是啥意思来着?
        if (controlnetAddress !== "") sendMsg(isDebug, `Send to Controlnet, But there are fastload data in there...`);
        sendMsg(isDebug, status[1]);
    } else {
        status = await sendToControlnetFastload(way, controlnetAddress, fastloadElemId);
        sendMsg(isDebug, status[1]);
    }
}

async function sendToControlnet(way, url_) {
    try {
        await delay(100);
        const cn = appDoc.querySelector(`#${way}_controlnet`);
        const wrap = cn.querySelector('.label-wrap');
        if (!wrap.className.includes('open')) {
            wrap.click();
            await delay(100);
        }
        wrap.scrollIntoView();
        const response = await fetch(url_);
        const imageBlob = await response.blob();
        const imageFile = new File([imageBlob], 'image.jpg', {
            type: imageBlob.type,
            lastModified: Date.now()
        });
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(imageFile);
        const pasteEvent = new ClipboardEvent('paste', {
            clipboardData: dataTransfer,
            bubbles: true
        });
        wrap.dispatchEvent(pasteEvent);
        return [true, "Send to Controlnet successfully"];
    } catch (err) {
        return [false, err]
    }
}

async function sendToControlnetFastload(way, url_, fastloadElemId) {
    try {
        await delay(200);
        if (url_ === "")  return [false, "The selected picture lacks Fastload data. Operation aborted."];
        const cn = appDoc.querySelector(`#${fastloadElemId}`);
        const wrap = cn.querySelector('.label-wrap');
        if (!wrap.className.includes('open')) {
            wrap.click();
            await delay(100);
        }
        wrap.scrollIntoView();
        const baseElement = document.getElementById(`${fastloadElemId}cnfl_uploadImage`);
        const clearButton = baseElement.querySelector('button[aria-label="Clear"]');
        if (clearButton) {
            clearButton.click();
        }
        await delay(100);
        const target = baseElement.querySelector('div:nth-child(3)');
        const imageFile = await urlToImageFile(url_);
        triggerEvent(target, 'dragenter');
        await delay(50);
        triggerEvent(target, 'dragover');
        await delay(50);
        triggerEvent(target, 'drop', createDropEvent(imageFile));
        await delay(50);
        const fastloadEnable = document.getElementById('script_txt2img_controlnet_fastload_cnfl_enabled');
        const fastloadEnableCheckBox = fastloadEnable.querySelector('input[type="checkbox"]');
        if (!fastloadEnableCheckBox.checked) {
            fastloadEnableCheckBox.click();
        }
        return [true, "Send to Controlnet Fastload successfully"];
    } catch (err) {
        return [false, err]
    }
}

function triggerEvent(target, type, customEvent = null) {
    let event = customEvent ? customEvent : new Event(type, {bubbles: true});
    target.dispatchEvent(event);
}

function createDropEvent(file) {
    const dataTransfer = new DataTransfer();
    dataTransfer.items.add(file);
    return new DragEvent('drop', {
        dataTransfer: dataTransfer,
        bubbles: true
    });
}

async function urlToImageFile(imgUrl) {
    const urlObj = new URL(imgUrl);
    const path = urlObj.href.split('=')[1];  // 提取文件路径
    const filename = path.split('/').pop();
    const response = await fetch(imgUrl);
    const imageBlob = await response.blob();
    return new File([imageBlob], filename, {
        type: imageBlob.type,
        lastModified: Date.now()
    });
}

function changeStyle() {
    const fastloadTabElemId = "controlnet_fastload_tab_";
    const sendTxt2imgButton = document.getElementById(`${fastloadTabElemId}send_txt2img`);
    const sendImg2imgButton = document.getElementById(`${fastloadTabElemId}send_img2img`);
    const sendTxt2imgFastloadButton = document.getElementById(`${fastloadTabElemId}send_controlnet_txt2img`);
    if (sendTxt2imgButton && sendTxt2imgFastloadButton) {
        let width = sendTxt2imgFastloadButton.offsetWidth + 'px';
        let height = sendTxt2imgFastloadButton.offsetHeight + 'px';
        sendTxt2imgButton.style.width = width;
        sendTxt2imgButton.style.height = height;
        sendImg2imgButton.style.width = width;
        sendImg2imgButton.style.height = height;
    }
}

onUiTabChange(changeStyle);