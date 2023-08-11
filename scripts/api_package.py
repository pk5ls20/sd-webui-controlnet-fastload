from datetime import datetime


class ControlNetFastloadAPI:
    def __init__(self):
        self.enabled = False
        self.drawId = {}

    def info(self):
        print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]} - ControlNetFastload - \033[92mINFO\033[0m - '
              f'API is {self.enabled}, have {len(self.drawId)} drawId(s)')


api_instance = ControlNetFastloadAPI()
