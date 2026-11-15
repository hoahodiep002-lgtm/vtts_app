"""Entry point. Giu mong: chi khoi tao UI, logic nam o core/ reader/ music/."""
from kivy.lang import Builder
from kivymd.app import MDApp

from core.config import APP_DB_NAME
from core.db import Database


class VoiceReaderApp(MDApp):
    def build(self):
        self.db = Database(self.user_data_dir + "/" + APP_DB_NAME)
        # TODO: ScreenManager voi cac man hinh music / reader / settings / pro
        return Builder.load_file("ui/kv/main.kv")


if __name__ == "__main__":
    VoiceReaderApp().run()
