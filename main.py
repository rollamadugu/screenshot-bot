"""
Screenshot Telegram Bot APK
Version: 5.0 - Shizuku/ADB Method
Commands: /startlive, /stoplive, /screenshot, /status
"""

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.storage.jsonstore import JsonStore
from kivy.utils import platform
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView

import threading
import requests
import os
import time
import subprocess
from datetime import datetime

if platform != 'android':
    Window.size = (400, 700)

if platform == 'android':
    from android.permissions import request_permissions, Permission
    from android.storage import primary_external_storage_path


class TelegramBot:
    """Telegram API handler"""
    
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.last_update_id = 0
    
    def send_message(self, text):
        try:
            url = f"{self.base_url}/sendMessage"
            data = {"chat_id": self.chat_id, "text": text}
            response = requests.post(url, data=data, timeout=30)
            return response.status_code == 200
        except Exception as e:
            print(f"Send error: {e}")
            return False
    
    def send_photo(self, photo_path, caption=""):
        try:
            url = f"{self.base_url}/sendPhoto"
            data = {"chat_id": self.chat_id, "caption": caption}
            with open(photo_path, 'rb') as photo:
                files = {"photo": photo}
                response = requests.post(url, data=data, files=files, timeout=60)
            return response.status_code == 200
        except Exception as e:
            print(f"Photo error: {e}")
            return False
    
    def get_updates(self):
        try:
            url = f"{self.base_url}/getUpdates"
            params = {"offset": self.last_update_id + 1, "timeout": 5}
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("ok") and data.get("result"):
                    return data["result"]
            return []
        except:
            return []
    
    def process_updates(self):
        updates = self.get_updates()
        commands = []
        
        for update in updates:
            self.last_update_id = update.get("update_id", self.last_update_id)
            message = update.get("message", {})
            text = message.get("text", "").lower().strip()
            chat_id = str(message.get("chat", {}).get("id", ""))
            
            if chat_id == str(self.chat_id):
                if text in ["/startlive", "/stoplive", "/screenshot", "/status", "/help"]:
                    commands.append(text[1:])
        
        return commands
    
    def test_connection(self):
        try:
            url = f"{self.base_url}/getMe"
            response = requests.get(url, timeout=10)
            return response.status_code == 200
        except:
            return False


class ScreenshotHandler:
    """Screenshot using Shizuku/ADB method"""
    
    def __init__(self):
        self.save_path = self._get_save_path()
        self._ensure_directory()
    
    def _get_save_path(self):
        if platform == 'android':
            try:
                return os.path.join(primary_external_storage_path(), 'ScreenshotBot')
            except:
                return '/sdcard/ScreenshotBot'
        return os.path.join(os.path.expanduser('~'), 'ScreenshotBot')
    
    def _ensure_directory(self):
        try:
            if not os.path.exists(self.save_path):
                os.makedirs(self.save_path)
        except:
            pass
    
    def capture(self):
        """Take screenshot using multiple methods"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'screenshot_{timestamp}.png'
            filepath = os.path.join(self.save_path, filename)
            
            if platform == 'android':
                return self._capture_android(filepath)
            else:
                return self._capture_pc(filepath)
        except Exception as e:
            print(f"Capture error: {e}")
            return None
    
    def _capture_android(self, filepath):
        """Android screenshot using Shizuku/shell method"""
        
        methods = [
            # Method 1: Direct screencap via Shizuku
            f'screencap -p {filepath}',
            # Method 2: Via sh
            f'sh -c "screencap -p {filepath}"',
            # Method 3: Full path
            f'/system/bin/screencap -p {filepath}',
        ]
        
        for i, cmd in enumerate(methods):
            try:
                # Try using subprocess
                result = subprocess.run(
                    cmd.split() if i == 0 else ['sh', '-c', cmd],
                    capture_output=True,
                    timeout=10
                )
                
                if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                    print(f"Method {i+1} worked!")
                    return filepath
                    
            except Exception as e:
                print(f"Method {i+1} failed: {e}")
                continue
        
        # Method 4: Using os.system
        try:
            os.system(f'screencap -p {filepath}')
            if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                return filepath
        except:
            pass
        
        # Method 5: Try via app_process (Shizuku method)
        try:
            cmd = f'app_process -Djava.class.path=/system/framework/screencap.jar /system/bin com.android.commands.screencap.Screencap -p {filepath}'
            os.system(cmd)
            if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                return filepath
        except:
            pass
        
        return None
    
    def _capture_pc(self, filepath):
        try:
            import pyautogui
            screenshot = pyautogui.screenshot()
            screenshot.save(filepath)
            return filepath
        except:
            return None


class SettingsPopup(Popup):
    """Settings popup"""
    
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.title = "Settings"
        self.size_hint = (0.9, 0.85)
        
        layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(8))
        
        # Token
        layout.add_widget(Label(text="Bot Token:", size_hint_y=None, height=dp(25)))
        self.token_input = TextInput(
            text=app.store.get('settings')['token'] if app.store.exists('settings') else '',
            multiline=False,
            size_hint_y=None,
            height=dp(40)
        )
        layout.add_widget(self.token_input)
        
        # Chat ID
        layout.add_widget(Label(text="Chat ID:", size_hint_y=None, height=dp(25)))
        self.chat_input = TextInput(
            text=app.store.get('settings')['chat_id'] if app.store.exists('settings') else '',
            multiline=False,
            size_hint_y=None,
            height=dp(40)
        )
        layout.add_widget(self.chat_input)
        
        # Interval
        layout.add_widget(Label(text="Interval (seconds):", size_hint_y=None, height=dp(25)))
        self.interval_input = TextInput(
            text=str(app.store.get('settings')['interval']) if app.store.exists('settings') else '30',
            multiline=False,
            size_hint_y=None,
            height=dp(40),
            input_filter='int'
        )
        layout.add_widget(self.interval_input)
        
        # Auto-start
        auto_layout = BoxLayout(size_hint_y=None, height=dp(40))
        auto_layout.add_widget(Label(text="Auto-start on boot:"))
        self.auto_start_btn = Button(
            text="ON" if (app.store.exists('settings') and app.store.get('settings').get('auto_start', False)) else "OFF",
            size_hint_x=0.3,
            background_color=(0.2, 0.8, 0.2, 1) if (app.store.exists('settings') and app.store.get('settings').get('auto_start', False)) else (0.8, 0.2, 0.2, 1)
        )
        self.auto_start_btn.bind(on_press=self.toggle_auto_start)
        auto_layout.add_widget(self.auto_start_btn)
        layout.add_widget(auto_layout)
        
        # Buttons
        btn_layout = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(10))
        
        test_btn = Button(text="Test", background_color=(0.2, 0.6, 1, 1))
        test_btn.bind(on_press=self.test_connection)
        btn_layout.add_widget(test_btn)
        
        save_btn = Button(text="Save", background_color=(0.2, 0.8, 0.2, 1))
        save_btn.bind(on_press=self.save_settings)
        btn_layout.add_widget(save_btn)
        
        layout.add_widget(btn_layout)
        
        self.status_label = Label(text="", size_hint_y=None, height=dp(25))
        layout.add_widget(self.status_label)
        
        # Shizuku status
        shizuku_label = Label(
            text="Make sure Shizuku is running!\nOpen Shizuku app to check.",
            size_hint_y=None,
            height=dp(50),
            font_size=dp(11),
            color=(1, 0.8, 0, 1)
        )
        layout.add_widget(shizuku_label)
        
        # Commands
        help_label = Label(
            text="Commands:\n/startlive /stoplive /screenshot /status /help",
            size_hint_y=None,
            height=dp(40),
            font_size=dp(10)
        )
        layout.add_widget(help_label)
        
        self.content = layout
    
    def toggle_auto_start(self, instance):
        if instance.text == "OFF":
            instance.text = "ON"
            instance.background_color = (0.2, 0.8, 0.2, 1)
        else:
            instance.text = "OFF"
            instance.background_color = (0.8, 0.2, 0.2, 1)
    
    def test_connection(self, instance):
        self.status_label.text = "Testing..."
        
        def test():
            bot = TelegramBot(self.token_input.text.strip(), self.chat_input.text.strip())
            if bot.test_connection():
                Clock.schedule_once(lambda dt: setattr(self.status_label, 'text', 'Connected!'))
            else:
                Clock.schedule_once(lambda dt: setattr(self.status_label, 'text', 'Failed!'))
        
        threading.Thread(target=test).start()
    
    def save_settings(self, instance):
        try:
            interval = int(self.interval_input.text) if self.interval_input.text else 30
            auto_start = self.auto_start_btn.text == "ON"
            
            self.app.store.put('settings',
                token=self.token_input.text.strip(),
                chat_id=self.chat_input.text.strip(),
                interval=interval,
                auto_start=auto_start
            )
            self.app.load_settings()
            self.status_label.text = "Saved!"
            Clock.schedule_once(lambda dt: self.dismiss(), 1)
        except Exception as e:
            self.status_label.text = f"Error: {e}"


class MainScreen(BoxLayout):
    """Main screen"""
    
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.orientation = 'vertical'
        self.padding = dp(15)
        self.spacing = dp(8)
        
        # Title
        self.add_widget(Label(
            text="Screenshot Bot v5",
            font_size=dp(26),
            size_hint_y=None,
            height=dp(50),
            bold=True
        ))
        
        # Shizuku reminder
        self.shizuku_label = Label(
            text="⚠️ Make sure Shizuku is running!",
            font_size=dp(12),
            size_hint_y=None,
            height=dp(25),
            color=(1, 0.8, 0, 1)
        )
        self.add_widget(self.shizuku_label)
        
        # Status
        self.status_label = Label(
            text="STOPPED",
            font_size=dp(22),
            size_hint_y=None,
            height=dp(35),
            color=(1, 0.3, 0.3, 1)
        )
        self.add_widget(self.status_label)
        
        self.info_label = Label(
            text="Configure settings to start",
            font_size=dp(12),
            size_hint_y=None,
            height=dp(25)
        )
        self.add_widget(self.info_label)
        
        # START button
        self.start_btn = Button(
            text="START SERVICE",
            size_hint_y=None,
            height=dp(55),
            font_size=dp(18),
            background_color=(0.2, 0.8, 0.2, 1)
        )
        self.start_btn.bind(on_press=self.toggle_service)
        self.add_widget(self.start_btn)
        
        # Screenshot button
        self.screenshot_btn = Button(
            text="Take Screenshot Now",
            size_hint_y=None,
            height=dp(45),
            background_color=(0.3, 0.5, 0.9, 1)
        )
        self.screenshot_btn.bind(on_press=self.take_manual_screenshot)
        self.add_widget(self.screenshot_btn)
        
        # Test screenshot button
        test_btn = Button(
            text="Test Screenshot (Local)",
            size_hint_y=None,
            height=dp(40),
            background_color=(0.6, 0.4, 0.8, 1)
        )
        test_btn.bind(on_press=self.test_screenshot)
        self.add_widget(test_btn)
        
        # Settings button
        settings_btn = Button(
            text="Settings",
            size_hint_y=None,
            height=dp(45),
            background_color=(0.5, 0.5, 0.5, 1)
        )
        settings_btn.bind(on_press=self.open_settings)
        self.add_widget(settings_btn)
        
        # Log
        self.add_widget(Label(text="Activity Log:", size_hint_y=None, height=dp(20)))
        
        scroll = ScrollView(size_hint=(1, 1))
        self.log_text = Label(
            text="App ready. Make sure Shizuku is running!\n",
            size_hint_y=None,
            halign='left',
            valign='top',
            text_size=(Window.width - dp(30), None),
            font_size=dp(11)
        )
        self.log_text.bind(texture_size=lambda *x: setattr(self.log_text, 'height', self.log_text.texture_size[1]))
        scroll.add_widget(self.log_text)
        self.add_widget(scroll)
        
        # State
        self.is_running = False
        self.is_live_mode = False
        
        # Auto-start check
        Clock.schedule_once(self.check_auto_start, 2)
    
    def check_auto_start(self, dt):
        if self.app.store.exists('settings'):
            settings = self.app.store.get('settings')
            if settings.get('auto_start', False) and self.app.bot:
                self.add_log("Auto-starting service...")
                self.start_service()
    
    def add_log(self, msg):
        t = datetime.now().strftime('%H:%M:%S')
        self.log_text.text += f"[{t}] {msg}\n"
    
    def test_screenshot(self, instance):
        """Test if screenshot works locally"""
        self.add_log("Testing screenshot...")
        
        def test():
            filepath = self.app.screenshot_handler.capture()
            if filepath and os.path.exists(filepath):
                size = os.path.getsize(filepath)
                Clock.schedule_once(lambda dt: self.add_log(f"SUCCESS! Screenshot saved ({size} bytes)"))
                Clock.schedule_once(lambda dt: self.add_log(f"Path: {filepath}"))
                Clock.schedule_once(lambda dt: setattr(self.shizuku_label, 'text', '✅ Screenshot working!'))
                Clock.schedule_once(lambda dt: setattr(self.shizuku_label, 'color', (0.2, 0.8, 0.2, 1)))
            else:
                Clock.schedule_once(lambda dt: self.add_log("FAILED! Screenshot not captured"))
                Clock.schedule_once(lambda dt: self.add_log("Make sure Shizuku is running!"))
        
        threading.Thread(target=test).start()
    
    def toggle_service(self, instance):
        if self.is_running:
            self.stop_service()
        else:
            self.start_service()
    
    def start_service(self):
        if not self.app.bot:
            self.add_log("Configure settings first!")
            return
        
        self.is_running = True
        self.status_label.text = "LISTENING"
        self.status_label.color = (0.2, 0.8, 0.2, 1)
        self.start_btn.text = "STOP SERVICE"
        self.start_btn.background_color = (0.9, 0.2, 0.2, 1)
        self.info_label.text = "Waiting for Telegram commands..."
        self.add_log("Service started!")
        
        self.app.bot.send_message(
            "🟢 Bot ONLINE!\n\n"
            "Commands:\n"
            "/startlive - Start screenshots\n"
            "/stoplive - Stop screenshots\n"
            "/screenshot - Take one\n"
            "/status - Check status\n"
            "/help - Show help"
        )
        
        threading.Thread(target=self.command_loop, daemon=True).start()
    
    def stop_service(self):
        self.is_running = False
        self.is_live_mode = False
        self.status_label.text = "STOPPED"
        self.status_label.color = (1, 0.3, 0.3, 1)
        self.start_btn.text = "START SERVICE"
        self.start_btn.background_color = (0.2, 0.8, 0.2, 1)
        self.info_label.text = "Service stopped"
        self.add_log("Service stopped")
        
        if self.app.bot:
            self.app.bot.send_message("🔴 Bot OFFLINE!")
    
    def command_loop(self):
        while self.is_running:
            try:
                commands = self.app.bot.process_updates()
                for cmd in commands:
                    self.handle_command(cmd)
                time.sleep(2)
            except Exception as e:
                Clock.schedule_once(lambda dt, e=e: self.add_log(f"Error: {e}"))
                time.sleep(5)
    
    def handle_command(self, cmd):
        if cmd == "startlive":
            if not self.is_live_mode:
                self.is_live_mode = True
                Clock.schedule_once(lambda dt: setattr(self.status_label, 'text', 'LIVE MODE'))
                Clock.schedule_once(lambda dt: setattr(self.status_label, 'color', (1, 0.8, 0, 1)))
                Clock.schedule_once(lambda dt: self.add_log("LIVE MODE started"))
                self.app.bot.send_message(f"📸 Live mode ON!\nInterval: {self.app.interval}s")
                threading.Thread(target=self.live_loop, daemon=True).start()
            else:
                self.app.bot.send_message("Already in live mode!")
        
        elif cmd == "stoplive":
            if self.is_live_mode:
                self.is_live_mode = False
                Clock.schedule_once(lambda dt: setattr(self.status_label, 'text', 'LISTENING'))
                Clock.schedule_once(lambda dt: setattr(self.status_label, 'color', (0.2, 0.8, 0.2, 1)))
                Clock.schedule_once(lambda dt: self.add_log("LIVE MODE stopped"))
                self.app.bot.send_message("📸 Live mode OFF!")
            else:
                self.app.bot.send_message("Live mode not running!")
        
        elif cmd == "screenshot":
            Clock.schedule_once(lambda dt: self.add_log("Screenshot requested"))
            self.app.bot.send_message("📷 Taking screenshot...")
            threading.Thread(target=self.take_and_send).start()
        
        elif cmd == "status":
            status = "LIVE MODE" if self.is_live_mode else "LISTENING" if self.is_running else "STOPPED"
            self.app.bot.send_message(f"📊 Status: {status}\n⏱ Interval: {self.app.interval}s")
        
        elif cmd == "help":
            self.app.bot.send_message(
                "📖 Commands:\n\n"
                "/startlive - Start live screenshots\n"
                "/stoplive - Stop live screenshots\n"
                "/screenshot - Take single screenshot\n"
                "/status - Check bot status\n"
                "/help - Show this help"
            )
    
    def live_loop(self):
        while self.is_live_mode and self.is_running:
            self.take_and_send()
            time.sleep(self.app.interval)
    
    def take_and_send(self):
        try:
            Clock.schedule_once(lambda dt: self.add_log("Capturing..."))
            
            filepath = self.app.screenshot_handler.capture()
            
            if filepath and os.path.exists(filepath):
                Clock.schedule_once(lambda dt: self.add_log("Sending..."))
                
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                success = self.app.bot.send_photo(filepath, f"📸 Screenshot\n🕐 {timestamp}")
                
                if success:
                    Clock.schedule_once(lambda dt: self.add_log("Sent successfully!"))
                else:
                    Clock.schedule_once(lambda dt: self.add_log("Send failed!"))
                
                try:
                    os.remove(filepath)
                except:
                    pass
            else:
                Clock.schedule_once(lambda dt: self.add_log("Capture failed! Check Shizuku"))
                self.app.bot.send_message("❌ Screenshot capture failed!\nMake sure Shizuku is running.")
        except Exception as e:
            Clock.schedule_once(lambda dt, e=e: self.add_log(f"Error: {e}"))
    
    def take_manual_screenshot(self, instance):
        if not self.app.bot:
            self.add_log("Configure settings first!")
            return
        self.add_log("Manual screenshot...")
        threading.Thread(target=self.take_and_send).start()
    
    def open_settings(self, instance):
        SettingsPopup(self.app).open()


class ScreenshotBotApp(App):
    """Main App"""
    
    def build(self):
        self.title = "Screenshot Bot"
        
        if platform == 'android':
            request_permissions([
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.READ_EXTERNAL_STORAGE,
                Permission.INTERNET,
                Permission.RECEIVE_BOOT_COMPLETED,
                Permission.FOREGROUND_SERVICE,
                Permission.WAKE_LOCK
            ])
        
        self.store = JsonStore('screenshotbot.json')
        self.bot = None
        self.interval = 30
        self.screenshot_handler = ScreenshotHandler()
        
        self.load_settings()
        
        return MainScreen(self)
    
    def load_settings(self):
        try:
            if self.store.exists('settings'):
                s = self.store.get('settings')
                token = s.get('token', '')
                chat_id = s.get('chat_id', '')
                self.interval = s.get('interval', 30)
                
                if token and chat_id:
                    self.bot = TelegramBot(token, chat_id)
        except Exception as e:
            print(f"Load error: {e}")
    
    def on_pause(self):
        return True
    
    def on_resume(self):
        pass


if __name__ == '__main__':
    ScreenshotBotApp().run()
