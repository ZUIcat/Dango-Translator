from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from system_hotkey import SystemHotkey
import qtawesome
import os
import time
import pyperclip
import requests

import utils.config
import utils.range
import utils.thread
import utils.translater
import utils.http
import utils.range
import utils.message
import utils.lock

import translator.sound
import translator.all

import ui.switch
import ui.range


LOGO_PATH = "./config/icon/logo.ico"
PIXMAP_PATH = "./config/icon/pixmap.png"
PIXMAP2_PATH = "./config/icon/pixmap2.png"


# 翻译界面
class Translation(QMainWindow) :

    # 范围快捷键信号
    range_hotkey_sign = pyqtSignal(bool)
    # 自动翻译模式信号
    auto_open_sign = pyqtSignal(bool)
    # 隐藏范围框快捷键
    hide_range_sign = pyqtSignal(bool)

    def __init__(self, object) :

        super(Translation, self).__init__()

        self.translater_yaml_map = {
            "youdao": "youdao",
            "baidu": "baiduweb",
            "tencent": "tencentweb",
            "caiyun": "caiyun",
            "google": "google",
            "deepl": "deepl"
        }
        self.object = object
        self.logger = object.logger
        self.getInitConfig()
        self.ui()

        # 开启朗读模块
        self.sound = translator.sound.Sound(self.object)
        utils.thread.createThread(self.sound.openWebdriver)
        # 开启翻译模块
        self.createWebdriverThread()
        # 自动翻译信号
        self.auto_open_sign.connect(lambda: utils.thread.createThread(self.startTranslater))


    def ui(self) :

        # 窗口尺寸
        self.resize(int(800*self.rate), int(130*self.rate))

        # 窗口无标题栏、窗口置顶、窗口透明
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 窗口图标
        icon = QIcon()
        icon.addPixmap(QPixmap(LOGO_PATH), QIcon.Normal, QIcon.On)
        self.setWindowIcon(icon)

        # 鼠标样式
        pixmap = QPixmap(PIXMAP_PATH)
        pixmap = pixmap.scaled(int(20 * self.rate),
                               int(20 * self.rate),
                               Qt.KeepAspectRatio,
                               Qt.SmoothTransformation)
        cursor = QCursor(pixmap, 0, 0)
        self.setCursor(cursor)

        # 鼠标选中状态图标
        select_pixmap = QPixmap(PIXMAP2_PATH)
        select_pixmap = select_pixmap.scaled(int(20 * self.rate),
                                             int(20 * self.rate),
                                             Qt.KeepAspectRatio,
                                             Qt.SmoothTransformation)
        select_pixmap = QCursor(select_pixmap, 0, 0)

        # 工具栏标签
        label = QLabel(self)
        self.customSetGeometry(label, 0, 0, 800, 30)
        label.setStyleSheet("background-color: rgba(62, 62, 62, 0.01)")

        # 翻译框字体
        self.font = QFont()
        self.font.setFamily(self.font_type)
        self.font.setPointSize(self.font_size)

        # 翻译框
        self.translate_text = QTextBrowser(self)
        self.customSetGeometry(self.translate_text, 0, 30, 1500, 110)
        self.translate_text.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.translate_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.translate_text.setFont(self.font)
        self.translate_text.setStyleSheet("border-width: 0;\
                                           border-style: outset;\
                                           border-top: 0px solid #e8f3f9;\
                                           color: white;\
                                           font-weight: bold;\
                                           background-color: rgba(62, 62, 62, %s)"
                                           %(self.horizontal/100))

        # 翻译框加入描边文字
        self.format = QTextCharFormat()
        # 翻译界面显示通知信息
        thread = utils.thread.createShowTranslateTextQThread(self.object)
        thread.signal.connect(self.showTranslateText)
        utils.thread.runQThread(thread)

        # 重叠提示消息框
        self.temp_text = QTextBrowser(self)
        self.customSetGeometry(self.temp_text, 0, 30, 1500, 110)
        self.temp_text.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.temp_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.temp_text.setFont(self.font)
        self.temp_text.setStyleSheet("border-width: 0;\
                                     border-style: outset;\
                                     border-top: 0px solid #e8f3f9;\
                                     color: white;\
                                     font-weight: bold;\
                                     background-color: rgba(62, 62, 62, %s)"
                                     %(self.horizontal/100))
        self.format.setTextOutline(QPen(QColor(self.font_color_1), 0.7, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        self.temp_text.mergeCurrentCharFormat(self.format)
        self.temp_text.append("翻译框和范围区域重叠, 请挪开翻译框!!!")
        self.temp_text.hide()

        # 翻译框根据内容自适应大小
        self.document = self.translate_text.document()
        self.document.contentsChanged.connect(self.textAreaChanged)

        # 此Label用于当鼠标进入界面时给出颜色反应
        self.drag_label = QLabel(self)
        self.drag_label.setObjectName("drag_label")
        self.customSetGeometry(self.drag_label, 0, 0, 4000, 2000)

        # 翻译按钮
        self.start_button = QPushButton(qtawesome.icon("fa.play", color=self.icon_color), "", self)
        self.customSetIconSize(self.start_button, 20, 20)
        self.customSetGeometry(self.start_button, 173, 5, 20, 20)
        self.start_button.setToolTip("<b>翻译键 Translate</b><br>点击后翻译（手动模式）")
        self.start_button.setStyleSheet("background: transparent;")
        self.start_button.clicked.connect(lambda: utils.thread.createThread(self.startTranslater))
        self.start_button.setCursor(select_pixmap)
        self.start_button.hide()

        # 设置按钮
        self.settin_button = QPushButton(qtawesome.icon("fa.cog", color=self.icon_color), "", self)
        self.customSetIconSize(self.settin_button, 20, 20)
        self.customSetGeometry(self.settin_button, 213, 5, 20, 20)
        self.settin_button.setToolTip("<b>设置键 Settin</b><br>翻译器的详细设置")
        self.settin_button.setStyleSheet("background: transparent;")
        self.settin_button.setCursor(select_pixmap)
        self.settin_button.hide()

        # 范围按钮
        self.range_button = QPushButton(qtawesome.icon("fa.crop", color=self.icon_color), "", self)
        self.customSetIconSize(self.range_button, 20, 20)
        self.customSetGeometry(self.range_button, 253, 5, 20, 20)
        self.range_button.setToolTip("<b>范围 Range</b><br>框选要翻译的区域<br>需从左上到右下拖动")
        self.range_button.setStyleSheet("background: transparent;")
        self.range_button.setCursor(select_pixmap)
        self.range_button.clicked.connect(self.clickRange)
        self.range_button.hide()

        # 复制按钮
        self.copy_button = QPushButton(qtawesome.icon("fa.copy", color=self.icon_color), "", self)
        self.customSetIconSize(self.copy_button, 20, 20)
        self.customSetGeometry(self.copy_button, 293, 5, 20, 20)
        self.copy_button.setToolTip("<b>复制 Copy</b><br>将当前识别到的文本<br>复制至剪贴板")
        self.copy_button.setStyleSheet("background: transparent;")
        self.copy_button.setCursor(select_pixmap)
        self.copy_button.clicked.connect(lambda: pyperclip.copy(self.original))
        self.copy_button.hide()

        # 屏蔽词按钮
        self.filter_word_button = QPushButton(qtawesome.icon("fa.ban", color=self.icon_color), "", self)
        self.customSetIconSize(self.filter_word_button, 20, 20)
        self.customSetGeometry(self.filter_word_button, 333, 5, 20, 20)
        self.filter_word_button.setToolTip("<b>屏蔽字符 Filter</b><br>将特定翻译错误的词<br>屏蔽不显示")
        self.filter_word_button.setStyleSheet("background: transparent;")
        self.filter_word_button.setCursor(select_pixmap)
        self.filter_word_button.clicked.connect(self.clickFilter)
        self.filter_word_button.hide()

        # 翻译模式按钮
        self.switch_button = ui.switch.SwitchButton(self, sign=self.translate_mode, startX=(50-20)*self.rate)
        self.customSetGeometry(self.switch_button, 373, 5, 50, 20)
        self.switch_button.setToolTip("<b>模式 Mode</b><br>手动翻译/自动翻译")
        self.switch_button.checkedChanged.connect(self.changeTranslateMode)
        self.switch_button.setCursor(select_pixmap)
        self.switch_button.hide()

        # 朗读原文按钮
        self.play_voice_button = QPushButton(qtawesome.icon("fa.music", color=self.icon_color), "", self)
        self.customSetIconSize(self.play_voice_button, 20, 20)
        self.customSetGeometry(self.play_voice_button, 443, 5, 20, 20)
        self.play_voice_button.setToolTip("<b>朗读原文 Play Voice</b><br>朗读识别到的原文")
        self.play_voice_button.setStyleSheet("background: transparent;")
        self.play_voice_button.clicked.connect(lambda: utils.thread.createThread(self.sound.playSound, self.original))
        self.play_voice_button.setCursor(select_pixmap)
        self.play_voice_button.hide()

        # 充电按钮
        self.battery_button = QPushButton(qtawesome.icon("fa.battery-half", color=self.icon_color), "", self)
        self.customSetIconSize(self.battery_button, 24, 20)
        self.customSetGeometry(self.battery_button, 483, 5, 24, 20)
        self.battery_button.setToolTip("<b>充电入口 Support author</b><br>我要给团子充电支持!")
        self.battery_button.setStyleSheet("background: transparent;")
        self.battery_button.setCursor(select_pixmap)
        self.battery_button.hide()

        # 锁按钮
        self.lock_button = QPushButton(qtawesome.icon("fa.lock", color=self.icon_color), "", self)
        self.customSetIconSize(self.lock_button, 20, 20)
        self.customSetGeometry(self.lock_button, 527, 5, 20, 20)
        self.lock_button.setToolTip("<b>锁定翻译界面 Lock</b>")
        self.lock_button.setStyleSheet("background: transparent;")
        self.lock_button.setCursor(select_pixmap)
        self.lock_button.clicked.connect(self.lock)
        self.lock_button.hide()

        # 最小化按钮
        self.minimize_button = QPushButton(qtawesome.icon("fa.minus", color=self.icon_color), "", self)
        self.customSetIconSize(self.minimize_button, 20, 20)
        self.customSetGeometry(self.minimize_button, 567, 5, 20, 20)
        self.minimize_button.setToolTip("<b>最小化 Minimize</b>")
        self.minimize_button.setStyleSheet("background: transparent;")
        self.minimize_button.setCursor(select_pixmap)
        self.minimize_button.clicked.connect(self.showMinimized)
        self.minimize_button.hide()

        # 退出按钮
        self.quit_button = QPushButton(qtawesome.icon("fa.times", color=self.icon_color), "", self)
        self.customSetIconSize(self.quit_button, 20, 20)
        self.customSetGeometry(self.quit_button, 607, 5, 20, 20)
        self.quit_button.setToolTip("<b>退出程序 Quit</b>")
        self.quit_button.setStyleSheet("background: transparent;")
        self.quit_button.setCursor(select_pixmap)
        self.quit_button.clicked.connect(self.showAppquitMessageBox)
        self.quit_button.hide()

        # 右下角用于拉伸界面的控件
        self.statusbar = QStatusBar(self)
        self.setStatusBar(self.statusbar)
        self.statusbar.setStyleSheet("font: 10pt %s;"
                                     "color: %s;"
                                     "background-color: rgba(62, 62, 62, 0.1)"
                                     %(self.font_type, self.icon_color))
        if not self.statusbar_sign :
            self.statusbar.hide()

        # 注册翻译快捷键
        self.translate_hotkey = SystemHotkey()
        if self.object.config["showHotKey1"] == "True" :
            self.translate_hotkey.register((self.translate_hotkey_value1, self.translate_hotkey_value2),
                                           callback=lambda x: utils.thread.createThread(self.startTranslater))

        # 注册范围快捷键
        self.range_hotkey = SystemHotkey()
        if self.object.config["showHotKey2"] == "True" :
            self.range_hotkey.register((self.range_hotkey_value1, self.range_hotkey_value2),
                                       callback=lambda x: self.range_hotkey_sign.emit(True))
        self.range_hotkey_sign.connect(self.clickRange)

        # 注册隐藏范围框快捷键
        self.hide_range_hotkey = SystemHotkey()
        if self.object.config["showHotKey3"] :
            self.hide_range_hotkey.register((self.hide_range_hotkey_value1, self.hide_range_hotkey_value2),
                                             callback=lambda x: self.hide_range_sign.emit(True))


    # 窗口显示信号
    def showEvent(self, e) :

        # 如果处于自动模式下则暂停
        if self.translate_mode :
            self.stop_sign = False


    # 窗口隐藏信号
    def hideEvent(self, e) :

        # 如果处于自动模式下则暂停
        if self.translate_mode :
            self.stop_sign = True


    # 初始化配置
    def getInitConfig(self):

        # 界面字体
        self.font_type = "华康方圆体W7"
        # 界面字体大小
        self.font_size = 15
        # 图标按键颜色
        self.icon_color = "white"
        # 字体颜色蓝色
        self.font_color_1 = "#1E90FF"
        self.font_color_2 = "#FF69B4"
        # 界面缩放比例
        self.rate = self.object.yaml["screen_scale_rate"]
        # 界面透明度
        self.horizontal = self.object.config["horizontal"]
        if self.horizontal == 0 :
            self.horizontal = 1
        # 当前登录的用户
        self.user = self.object.yaml["user"]
        # 界面锁
        self.lock_sign = False
        # 翻译模式
        self.translate_mode = False
        # 自动翻译暂停标志
        self.stop_sign = False
        # 原文
        self.original = ""
        # 翻译线程1启动成功标志
        self.webdriver_1_sign = False
        # 翻译线程2启动成功标志
        self.webdriver_2_sign = False
        # 翻译线程1翻译类型
        self.webdriver_type1 = ""
        # 翻译线程2翻译类型
        self.webdriver_type2 = ""
        # 翻译线程3翻译类型
        self.webdriver_type3 = ""
        # 状态栏是否隐藏标志
        self.statusbar_sign = self.object.config["showStatusbarUse"]
        # 各翻译源线程状态标志
        self.thread_state = 0
        # 自动翻译线程存在标志
        self.auto_trans_exist = False
        # 长连接对象, 用于在线OCR
        self.object.session = requests.Session()
        # 按键转换映射关系
        hotkey_map = {
            "ctrl": "control",
            "win": "super"
        }
        # 翻译快捷键
        self.translate_hotkey_value1 = hotkey_map.get(self.object.config["translateHotkeyValue1"],
                                                      self.object.config["translateHotkeyValue1"])
        self.translate_hotkey_value2 = hotkey_map.get(self.object.config["translateHotkeyValue2"],
                                                      self.object.config["translateHotkeyValue2"])
        # 范围快捷键
        self.range_hotkey_value1 = hotkey_map.get(self.object.config["rangeHotkeyValue1"],
                                                  self.object.config["rangeHotkeyValue1"])
        self.range_hotkey_value2 = hotkey_map.get(self.object.config["rangeHotkeyValue2"],
                                                  self.object.config["rangeHotkeyValue2"])
        # 范围快捷键
        self.hide_range_hotkey_value1 = hotkey_map.get(self.object.config["hideRangeHotkeyValue1"],
                                                       self.object.config["hideRangeHotkeyValue1"])
        self.hide_range_hotkey_value2 = hotkey_map.get(self.object.config["hideRangeHotkeyValue2"],
                                                       self.object.config["hideRangeHotkeyValue2"])
        # 竖排翻译贴字
        self.object.ocr_result = None


    # 根据分辨率定义控件位置尺寸
    def customSetGeometry(self, object, x, y, w, h):

        object.setGeometry(QRect(int(x * self.rate),
                                 int(y * self.rate), int(w * self.rate),
                                 int(h * self.rate)))


    # 根据分辨率定义图标位置尺寸
    def customSetIconSize(self, object, w, h):

        object.setIconSize(QSize(int(w*self.rate),
                                 int(h*self.rate)))


    # 鼠标移动事件
    def mouseMoveEvent(self, e: QMouseEvent) :

        if self.lock_sign == True :
            return

        try:
            self._endPos = e.pos() - self._startPos
            self.move(self.pos() + self._endPos)
        except Exception:
            pass

        # 判断是否和范围框碰撞
        self.checkOverlap()


    # 鼠标按下事件
    def mousePressEvent(self, e: QMouseEvent) :

        if self.lock_sign == True :
            return

        try:
            if e.button() == Qt.LeftButton :
                self._isTracking = True
                self._startPos = QPoint(e.x(), e.y())
        except Exception:
            pass


    # 鼠标松开事件
    def mouseReleaseEvent(self, e: QMouseEvent) :

        if self.lock_sign == True :
            return

        try:
            if e.button() == Qt.LeftButton :
                self._isTracking = False
                self._startPos = None
                self._endPos = None
        except Exception:
            pass


    # 鼠标进入控件事件
    def enterEvent(self, QEvent) :

        if self.lock_sign == True :
            self.lock_button.show()
            self.lock_button.setStyleSheet("background-color:rgba(62, 62, 62, 0.1);")
            return

        # 显示所有顶部工具栏控件
        self.switch_button.show()
        self.start_button.show()
        self.settin_button.show()
        self.range_button.show()
        self.copy_button.show()
        self.quit_button.show()
        self.minimize_button.show()
        self.battery_button.show()
        self.play_voice_button.show()
        self.lock_button.show()
        self.filter_word_button.show()
        self.setStyleSheet("QLabel#drag_label {background-color:rgba(62, 62, 62, 0.1)}")
        if self.statusbar_sign :
            self.statusbar.show()


    # 鼠标离开控件事件
    def leaveEvent(self, QEvent) :

        if self.lock_sign == False and self.statusbar_sign :
            self.statusbar.show()

        width = round((self.width() - 454*self.rate) / 2)
        height = self.height() - 30*self.rate

        # 重置所有控件的位置和大小
        self.start_button.setGeometry(QRect(width, 5 * self.rate, 20 * self.rate, 20 * self.rate))
        self.settin_button.setGeometry(QRect(width + 40 * self.rate, 5 * self.rate, 20 * self.rate, 20 * self.rate))
        self.range_button.setGeometry(QRect(width + 80 * self.rate, 5 * self.rate, 20 * self.rate, 20 * self.rate))
        self.copy_button.setGeometry(QRect(width + 120 * self.rate, 5 * self.rate, 20 * self.rate, 20 * self.rate))
        self.filter_word_button.setGeometry(QRect(width + 160 * self.rate, 5 * self.rate, 20 * self.rate, 20 * self.rate))
        self.switch_button.setGeometry(QRect(width + 200 * self.rate, 5 * self.rate, 50 * self.rate, 20 * self.rate))
        self.play_voice_button.setGeometry(QRect(width + 270 * self.rate, 5 * self.rate, 20 * self.rate, 20 * self.rate))
        self.battery_button.setGeometry(QRect(width + 314 * self.rate, 5 * self.rate, 24 * self.rate, 20 * self.rate))
        self.lock_button.setGeometry(QRect(width + 358 * self.rate, 5 * self.rate, 24 * self.rate, 20 * self.rate))
        self.minimize_button.setGeometry(QRect(width + 398 * self.rate, 5 * self.rate, 20 * self.rate, 20 * self.rate))
        self.quit_button.setGeometry(QRect(width + 438 * self.rate, 5 * self.rate, 20 * self.rate, 20 * self.rate))
        self.translate_text.setGeometry(0, 30 * self.rate, self.width(), height * self.rate)

        # 隐藏所有顶部工具栏控件
        self.switch_button.hide()
        self.start_button.hide()
        self.settin_button.hide()
        self.range_button.hide()
        self.copy_button.hide()
        self.quit_button.hide()
        self.minimize_button.hide()
        self.battery_button.hide()
        self.play_voice_button.hide()
        self.lock_button.hide()
        self.filter_word_button.hide()

        self.setStyleSheet("QLabel#drag_label {background-color:none}")
        self.textAreaChanged()


    # 翻译框初始消息
    def showTranslateText(self, result) :

        if result :
            for content in result.split(r"\n") :
                self.format.setTextOutline(QPen(QColor(self.font_color_1), 0.7, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                self.translate_text.mergeCurrentCharFormat(self.format)
                self.translate_text.append(content)
        else :
            self.format.setTextOutline(QPen(QColor(self.font_color_1), 0.7, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            self.translate_text.mergeCurrentCharFormat(self.format)
            self.translate_text.append("欢迎你 ~ %s 么么哒 ~" % self.user)
            self.format.setTextOutline(QPen(QColor(self.font_color_2), 0.7, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            self.translate_text.mergeCurrentCharFormat(self.format)
            self.translate_text.append("b站关注 团子翻译器 查看动态可了解翻译器最新情况 ~")
            self.format.setTextOutline(QPen(QColor(self.font_color_1), 0.7, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            self.translate_text.mergeCurrentCharFormat(self.format)
            self.translate_text.append("团子一个人开发不易，这个软件真的花了很大很大的精力 _(:з」∠)_")
            self.format.setTextOutline(QPen(QColor(self.font_color_2), 0.7, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            self.translate_text.mergeCurrentCharFormat(self.format)
            self.translate_text.append("喜欢的话能不能点击上方的电池图标支持一下团子，真心感谢你❤")



    # 当翻译内容改变时界面自适应窗口大小
    def textAreaChanged(self) :

        newHeight = self.document.size().height()
        if self.statusbar_sign :
            newHeight += self.statusbar.height()

        width = self.width()
        self.resize(width, newHeight + 30*self.rate)
        self.translate_text.setGeometry(0, 30*self.rate, width, newHeight)

        # 判断是否和范围框碰撞
        try :
            self.checkOverlap()
        except Exception :
            pass


    # 锁定界面
    def lock(self) :

        # 上锁
        if not self.lock_sign :
            self.lock_button.setIcon(qtawesome.icon("fa.unlock", color=self.icon_color))
            self.drag_label.hide()
            self.lock_sign = True

            if self.horizontal == 1 :
                self.horizontal = 0
        # 解锁
        else:
            self.lock_button.setIcon(qtawesome.icon("fa.lock", color=self.icon_color))
            self.lock_button.setStyleSheet("background: transparent;")
            self.drag_label.show()
            self.lock_sign = False

            if self.horizontal == 0 :
                self.horizontal = 1

        self.translate_text.setStyleSheet("border-width:0;\
                                          border-style:outset;\
                                          border-top:0px solid #e8f3f9;\
                                          color:white;\
                                          font-weight: bold;\
                                          background-color:rgba(62, 62, 62, %s)"
                                          %(self.horizontal/100))

        self.temp_text.setStyleSheet("border-width:0;\
                                      border-style:outset;\
                                      border-top:0px solid #e8f3f9;\
                                      color:white;\
                                      font-weight: bold;\
                                      background-color:rgba(62, 62, 62, %s)"
                                      %(self.horizontal/100))


    # 改变翻译模式
    def changeTranslateMode(self, checked) :

        if checked :
            self.translate_mode = True
            self.auto_open_sign.emit(True)
        else:
            self.translate_mode = False


    # 按下翻译键
    def startTranslater(self) :

        # 如果已处在自动翻译模式下则直接退出
        if self.auto_trans_exist :
            return

        thread = utils.translater.Translater(self.object)
        thread.clear_text_sign.connect(self.clearText)
        thread.hide_range_ui_sign.connect(self.object.range_ui.hideUI)
        thread.start()
        thread.wait()


    # 收到翻译信息清屏
    def clearText(self) :

        # 记录翻译开始时间
        self.object.translation_ui.start_time = time.time()

        # 翻译界面清屏
        self.translate_text.clear()

        # 设定翻译时的字体类型和大小
        self.font.setFamily(self.object.config["fontType"])
        self.font.setPointSize(self.object.config["fontSize"])
        self.translate_text.setFont(self.font)


    # 注销快捷键
    def unregisterHotKey(self) :

        if self.object.config["showHotKey1"] == "True" :
            self.translate_hotkey.unregister((self.translate_hotkey_value1, self.translate_hotkey_value2))

        if self.object.config["showHotKey2"] == "True" :
            self.range_hotkey.unregister((self.range_hotkey_value1, self.range_hotkey_value2))

        if self.object.config["showHotKey3"] :
            self.hide_range_hotkey.unregister((self.hide_range_hotkey_value1, self.hide_range_hotkey_value2))


    # 将翻译结果打印
    def display_text(self, result, trans_type) :

        # 公共翻译一
        if trans_type == "webdriver_1" :
            color = self.object.config["fontColor"][self.translater_yaml_map[self.webdriver1.web_type]]
            trans_type = self.webdriver1.web_type
        # 公共翻译二
        elif trans_type == "webdriver_2" :
            color = self.object.config["fontColor"][self.translater_yaml_map[self.webdriver2.web_type]]
            trans_type = self.webdriver2.web_type
        # 公共翻译三
        elif trans_type == "webdriver_3":
            color = self.object.config["fontColor"][self.translater_yaml_map[self.webdriver3.web_type]]
            trans_type = self.webdriver3.web_type
        # 私人百度
        elif trans_type == "baidu_private" :
            color = self.object.config["fontColor"]["baidu"]
        # 私人腾讯
        elif trans_type == "tencent_private" :
            color = self.object.config["fontColor"]["tencent"]
        # 私人彩云
        elif trans_type == "caiyun_private" :
            color = self.object.config["fontColor"]["caiyunPrivate"]
        # 原文
        elif trans_type == "original" :
            color = self.object.config.get("fontColor", {}).get("original", self.font_color_1)
        else :
            return

        # 根据屏蔽词过滤
        for val in self.object.config["Filter"] :
            if not val[0] :
                continue
            result = result.replace(val[0], val[1])

        # 显示在文本框上
        if self.object.config["showColorType"] == "False" :
            self.format.setTextOutline(QPen(QColor(color), 0.7, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            self.translate_text.mergeCurrentCharFormat(self.format)
            self.translate_text.append(result)
        else :
            result = result.replace("\n", "<br>")
            self.translate_text.append("<font color=%s>%s</font>"%(color, result))
        QApplication.processEvents()

        # 保存译文
        utils.config.saveTransHisTory(result, trans_type)

        # 线程结束，减少线程数
        self.thread_state -= 1
        if self.thread_state < 0 :
            self.thread_state = 0

        if self.thread_state == 0 :
            try :
                self.statusbar.showMessage("翻译结束, 耗时: {:.2f} s".format(time.time()-self.start_time+self.ocr_time))
            except Exception :
                self.statusbar.showMessage("翻译结束, 耗时: {:.2f} s".format(time.time()-self.start_time))
            self.ocr_time = 0


    # 检测范围区域和翻译区域是否有重叠
    def checkOverlap(self) :

        # 翻译框坐标
        rect = self.geometry()
        X1 = rect.left()
        Y1 = rect.top()+(self.height()-self.translate_text.height())
        X2 = rect.left() + rect.width()
        Y2 = rect.top() + rect.height()

        # 范围框坐标
        rect = self.object.range_ui.geometry()
        x1 = rect.left()
        y1 = rect.top()
        x2 = rect.left() + rect.width()
        y2 = rect.top() + rect.height()

        rr1 = utils.range.Rectangular(X1, Y1, X2 - X1, Y2 - Y1)
        rr2 = utils.range.Rectangular(x1, y1, x2 - x1, y2 - y1)

        if rr2.collision(rr1) :
            self.customSetGeometry(self.temp_text, 0, 30, self.translate_text.width(), self.translate_text.height())
            self.translate_text.hide()
            self.temp_text.show()
        else :
            self.temp_text.hide()
            self.translate_text.show()


    # 加载翻译引擎1
    def openWebdriver1(self) :

        # 翻译模块1
        self.webdriver1 = translator.all.Webdriver(self.object)
        # 连接消息提示框
        self.webdriver1.message_sign.connect(self.showStatusbar)
        # 加载翻译引擎
        self.webdriver1.openWebdriver()
        # 开启翻译页面
        if self.webdriver_type1 :
            utils.thread.createThread(self.webdriver1.openWeb, self.webdriver_type1)


    # 加载翻译引擎2
    def openWebdriver2(self) :

        # 翻译模块2
        self.webdriver2 = translator.all.Webdriver(self.object)
        # 连接消息提示框
        self.webdriver2.message_sign.connect(self.showStatusbar)
        # 加载翻译引擎
        self.webdriver2.openWebdriver()
        # 开启翻译页面
        if self.webdriver_type2 :
            utils.thread.createThread(self.webdriver2.openWeb, self.webdriver_type2)

    # 加载翻译引擎3
    def openWebdriver3(self):

        # 翻译模块3
        self.webdriver3 = translator.all.Webdriver(self.object)
        # 连接消息提示框
        self.webdriver3.message_sign.connect(self.showStatusbar)
        # 加载翻译引擎
        self.webdriver3.openWebdriver()
        # 开启翻译页面
        if self.webdriver_type3 :
            utils.thread.createThread(self.webdriver3.openWeb, self.webdriver_type3)


    # 开启翻译模块
    def createWebdriverThread(self) :

        self.statusbar.showMessage("翻译模块启动中, 请等待完成后再操作...")

        # 筛选翻译源类型
        translater_list = ["youdaoUse", "baiduwebUse", "tencentwebUse", "deeplUse", "googleUse", "caiyunUse"]
        for val in translater_list :
            if self.object.config[val] == "False" :
                continue
            if not self.webdriver_type1 :
                # 翻译模块一的翻译源类型
                self.webdriver_type1 = val.replace("Use", "").replace("web", "")
            elif not self.webdriver_type2 :
                # 翻译模块二的翻译源类型
                self.webdriver_type2 = val.replace("Use", "").replace("web", "")
            else :
                self.webdriver_type3 = val.replace("Use", "").replace("web", "")

        utils.thread.createThread(self.openWebdriver1)
        utils.thread.createThread(self.openWebdriver2)
        utils.thread.createThread(self.openWebdriver3)


    # 状态栏显示消息信号槽
    def showStatusbar(self, message) :

        self.statusbar.showMessage(message)


    # 按下屏蔽词键后做的事情
    def clickFilter(self) :

        self.hide()
        self.object.filter_ui.show()


    # 按下范围框选键
    def clickRange(self):

        # 如果处于自动模式下则暂停
        if self.translate_mode :
            self.stop_sign = True

        self.object.screen_shot_ui = ui.range.WScreenShot(self.object)
        self.object.screen_shot_ui.show()
        self.show()


    # 关闭selenuim的driver引擎
    def killDriVer(self) :

        utils.thread.createThreadDaemonFalse(os.popen, "taskkill /im chromedriver.exe /F")
        utils.thread.createThreadDaemonFalse(os.popen, "taskkill /im geckodriver.exe /F")
        utils.thread.createThreadDaemonFalse(os.popen, "taskkill /im msedgedriver.exe /F")


    # 退出提示框
    def showAppquitMessageBox(self) :

        utils.message.quitAppMessageBox("退出程序", "真的要关闭团子吗?QAQ      ", self.object)


    # 退出程序
    def quit(self) :

        # 界面关闭
        self.hide()
        self.object.range_ui.close()
        # 删除进程锁
        utils.lock.deleteLock()
        # 注销快捷键
        utils.thread.createThreadDaemonFalse(self.unregisterHotKey)
        # 关闭引擎模块
        utils.thread.createThreadDaemonFalse(self.sound.close)
        utils.thread.createThreadDaemonFalse(self.webdriver1.close)
        utils.thread.createThreadDaemonFalse(self.webdriver2.close)
        utils.thread.createThreadDaemonFalse(self.webdriver3.close)
        # 关闭selenium的driver引擎
        self.killDriVer()
        # 退出程序前保存设置
        utils.thread.createThreadDaemonFalse(utils.config.postSaveSettin, self.object)

        self.close()