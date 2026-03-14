"""
Screenshot Telegram Bot APK
Version: 2.0
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
from datetime import datetime

# Set window size for testing on PC
if platform != 'android':
    Window.size = (400, 700)

# Android specific imports
if platform == 'android':
    from android.permissions import request_permissions, Permission
    from android.storage import primary_external_storage_path


class TelegramBot:
    """Handle Telegram API communication"""
    
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.last_update_id = 0
    
    def send_message(self, text):
        """Send text message to Telegram"""
        try:
            url = f"{self.base_url}/sendMessage"
            data = {"chat_id": self.chat_id, "text": text}
            response = requests.post(url, data=data, timeout=30)
            return response.status_code == 200
        except Exception as e:
            print(f"Send message error: {e}")
            return False
    
    def send_photo(self, photo_path, caption=""):
        """Send photo to Telegram"""
        try:
            url = f"{self.base_url}/sendPhoto"
            data = {"chat_id": self.chat_id, "caption": caption}
            with open(photo_path, 'rb') as photo:
                files = {"photo": photo}
                response = requests.post(url, data=data, files=files, timeout=60)
            return response.status_code == 200
        except Exception as e:
            print(f"Send photo error: {e}")
            return False
    
    def get_updates(self):
        """Get new messages from Telegram"""
        try:
            url = f"{self.base_url}/getUpdates"
            params = {
                "offset": self.last_update_id + 1,
                "timeout": 5
            }
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("ok") and data.get("result"):
                    return data["result"]
            return []
        except Exception as e:
            print(f"Get updates error: {e}")
            return []
    
    def process_updates(self):
        """Process incoming messages and return commands"""
        updates = self.get_updates()
        commands = []
        
        for update in updates:
            self.last_update_id = update.get("update_id", self.last_update_id)
            
            message = update.get("message", {})
            text = message.get("text", "").lower().strip()
            chat_id = str(message.get("chat", {}).get("id", ""))
            
            # Only process messages from authorized chat
            if chat_id == str(self.chat_id):
                if text == "/startlive":
                    commands.append("startlive")
                elif text == "/stoplive":
                    commands.append("stoplive")
                elif text == "/screenshot":
                    commands.append("screenshot")
                elif text == "/status":
                    commands.append("status")
                elif text == "/help":
                    commands.append("help")
        
        return commands
    
    def test_connection(self):
        """Test if bot token is valid"""
        try:
            url = f"{self.base_url}/getMe"
            response = requests.get(url, timeout=10)
            return response.status_code == 200
        except:
            return False


class ScreenshotHandler:
    """Handle screenshot capture"""
    
    def __init__(self):
        self.save_path = self._get_save_path()
        self._ensure_directory()
    
    def _get_save_path(self):
        """Get path for saving screenshots"""
        if platform == 'android':
            try:
                return os.path.join(primary_external_storage_path(), 'ScreenshotBot')
            except:
                return '/sdcard/ScreenshotBot'
        return os.path.join(os.path.expanduser('~'), 'ScreenshotBot')
    
    def _ensure_directory(self):
        """Create directory if not exists"""
        try:
            if not os.path.exists(self.save_path):
                os.makedirs(self.save_path)
        except Exception as e:
            print(f"Directory error: {e}")
    
    def capture(self):
        """Capture screenshot"""
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
        """Capture screenshot on Android"""
        try:
            # Method 1: Standard screencap
            result = os.system(f'screencap -p "{filepath}"')
            if result == 0 and os.path.exists(filepath):
                return filepath
            
            # Method 2: With full path
            result = os.system(f'/system/bin/screencap -p "{filepath}"')
            if result == 0 and os.path.exists(filepath):
                return filepath
                
        except Exception as e:
            print(f"Android capture error: {e}")
        return None
    
    def _capture_pc(self, filepath):
        """Capture screenshot on PC (for testing)"""
        try:
            import pyautogui
            screenshot = pyautogui.screenshot()
            screenshot.save(filepath)
            return filepath
        except ImportError:
            print("Install pyautogui for PC testing")
        except Exception as e:
            print(f"PC capture error: {e}")
        return None


class SettingsPopup(Popup):
    """Settings configuration popup"""
    
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.title = "Settings"
        self.size_hint = (0.9, 0.8)
        
        layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        
        # Bot Token
        layout.add_widget(Label(text="Bot Token:", size_hint_y=None, height=dp(30)))
        self.token_input = TextInput(
            text=app.store.get('settings')['token'] if app.store.exists('settings') else '',
            multiline=False,
            size_hint_y=None,
            height=dp(45),
            hint_text="Enter your Telegram bot token"
        )
        layout.add_widget(self.token_input)
        
        # Chat ID
        layout.add_widget(Label(text="Chat ID:", size_hint_y=None, height=dp(30)))
        self.chat_input = TextInput(
            text=app.store.get('settings')['chat_id'] if app.store.exists('settings') else '',
            multiline=False,
            size_hint_y=None,
            height=dp(45),
            hint_text="Enter your Telegram chat ID"
        )
        layout.add_widget(self.chat_input)
        
        # Interval
        layout.add_widget(Label(text="Interval (seconds):", size_hint_y=None, height=dp(30)))
        self.interval_input = TextInput(
            text=str(app.store.get('settings')['interval']) if app.store.exists('settings') else '30',
            multiline=False,
            size_hint_y=None,
            height=dp(45),
            hint_text="Screenshot interval",
            input_filter='int'
        )
        layout.add_widget(self.interval_input)
        
        # Buttons
        btn_layout = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        
        test_btn = Button(text="Test Connection", background_color=(0.2, 0.6, 1, 1))
        test_btn.bind(on_press=self.test_connection)
        btn_layout.add_widget(test_btn)
        
        save_btn = Button(text="Save", background_color=(0.2, 0.8, 0.2, 1))
        save_btn.bind(on_press=self.save_settings)
        btn_layout.add_widget(save_btn)
        
        layout.add_widget(btn_layout)
        
        self.status_label = Label(text="", size_hint_y=None, height=dp(30))
        layout.add_widget(self.status_label)
        
        # Help text
        help_text = Label(
            text="Commands:\n/startlive - Start screenshots\n/stoplive - Stop screenshots\n/screenshot - Take one\n/status - Check status\n/help - Show commands",
            size_hint_y=None,
            height=dp(120),
            font_size=dp(12)
        )
        layout.add_widget(help_text)
        
        self.content = layout
    
    def test_connection(self, instance):
        """Test Telegram bot connection"""
        self.status_label.text = "Testing..."
        
        def test():
            bot = TelegramBot(self.token_input.text.strip(), self.chat_input.text.strip())
            if bot.test_connection():
                Clock.schedule_once(lambda dt: setattr(self.status_label, 'text', 'Connection successful!'))
            else:
                Clock.schedule_once(lambda dt: setattr(self.status_label, 'text', 'Connection failed!'))
        
        threading.Thread(target=test).start()
    
    def save_settings(self, instance):
        """Save settings to storage"""
        try:
            interval = int(self.interval_input.text) if self.interval_input.text else 30
            self.app.store.put('settings',
                token=self.token_input.text.strip(),
                chat_id=self.chat_input.text.strip(),
                interval=interval
            )
            self.app.load_settings()
            self.status_label.text = "Settings saved!"
            Clock.schedule_once(lambda dt: self.dismiss(), 1)
        except Exception as e:
            self.status_label.text = f"Error: {e}"


class MainScreen(BoxLayout):
    """Main application screen"""
    
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.orientation = 'vertical'
        self.padding = dp(15)
        self.spacing = dp(10)
        
        # Title
        title = Label(
            text="Screenshot Bot",
            font_size=dp(28),
            size_hint_y=None,
            height=dp(60),
            bold=True
        )
        self.add_widget(title)
        
        # Status Card
        status_card = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=dp(100),
            padding=dp(10)
        )
        
        self.status_label = Label(
            text="Stopped",
            font_size=dp(24)
        )
        status_card.add_widget(self.status_label)
        
        self.info_label = Label(
            text="Configure settings to start",
            font_size=dp(14)
        )
        status_card.add_widget(self.info_label)
        
        self.add_widget(status_card)
        
        # Control Buttons
        self.start_btn = Button(
            text="START",
            size_hint_y=None,
            height=dp(60),
            font_size=dp(20),
            background_color=(0.2, 0.8, 0.2, 1)
        )
        self.start_btn.bind(on_press=self.toggle_service)
        self.add_widget(self.start_btn)
        
        # Manual Screenshot Button
        manual_btn = Button(
            text="Take Screenshot Now",
            size_hint_y=None,
            height=dp(50),
            background_color=(0.3, 0.5, 0.9, 1)
        )
        manual_btn.bind(on_press=self.take_manual_screenshot)
        self.add_widget(manual_btn)
        
        # Settings Button
        settings_btn = Button(
            text="Settings",
            size_hint_y=None,
            height=dp(50),
            background_color=(0.5, 0.5, 0.5, 1)
        )
        settings_btn.bind(on_press=self.open_settings)
        self.add_widget(settings_btn)
        
        # Log Area
        log_label = Label(
            text="Activity Log:",
            size_hint_y=None,
            height=dp(30),
            halign='left'
        )
        self.add_widget(log_label)
        
        scroll = ScrollView(size_hint=(1, 1))
        
        self.log_text = Label(
            text="App started. Waiting for commands...\n",
            size_hint_y=None,
            halign='left',
            valign='top',
            text_size=(Window.width - dp(30), None)
        )
        self.log_text.bind(texture_size=lambda *x: setattr(self.log_text, 'height', self.log_text.texture_size[1]))
        scroll.add_widget(self.log_text)
        self.add_widget(scroll)
        
        # State
        self.is_running = False
        self.is_live_mode = False
        self.command_thread = None
        self.screenshot_thread = None
    
    def add_log(self, message):
        """Add message to log"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_text.text += f"[{timestamp}] {message}\n"
    
    def toggle_service(self, instance):
        """Start or stop the command listener service"""
        if self.is_running:
            self.stop_service()
        else:
            self.start_service()
    
    def start_service(self):
        """Start command listener service"""
        if not self.app.bot:
            self.add_log("Configure settings first!")
            return
        
        self.is_running = True
        self.status_label.text = "Listening..."
        self.start_btn.text = "STOP"
        self.start_btn.background_color = (0.9, 0.2, 0.2, 1)
        self.info_label.text = "Waiting for Telegram commands"
        self.add_log("Service started - Listening for commands")
        
        # Send notification to Telegram
        self.app.bot.send_message("Bot is now ONLINE!\n\nCommands:\n/startlive - Start live screenshots\n/stoplive - Stop live screenshots\n/screenshot - Take one screenshot\n/status - Check bot status\n/help - Show commands")
        
        # Start command listener thread
        self.command_thread = threading.Thread(target=self.command_loop, daemon=True)
        self.command_thread.start()
    
    def stop_service(self):
        """Stop command listener service"""
        self.is_running = False
        self.is_live_mode = False
        self.status_label.text = "Stopped"
        self.start_btn.text = "START"
        self.start_btn.background_color = (0.2, 0.8, 0.2, 1)
        self.info_label.text = "Service stopped"
        self.add_log("Service stopped")
        
        if self.app.bot:
            self.app.bot.send_message("Bot is now OFFLINE!")
    
    def command_loop(self):
        """Background loop for listening to Telegram commands"""
        while self.is_running:
            try:
                commands = self.app.bot.process_updates()
                
                for cmd in commands:
                    if cmd == "startlive":
                        self.handle_startlive()
                    elif cmd == "stoplive":
                        self.handle_stoplive()
                    elif cmd == "screenshot":
                        self.handle_screenshot()
                    elif cmd == "status":
                        self.handle_status()
                    elif cmd == "help":
                        self.handle_help()
                
                time.sleep(2)  # Check every 2 seconds
                
            except Exception as e:
                Clock.schedule_once(lambda dt: self.add_log(f"Error: {str(e)[:30]}"))
                time.sleep(5)
    
    def handle_startlive(self):
        """Handle /startlive command"""
        if self.is_live_mode:
            self.app.bot.send_message("Live mode already running!")
            return
        
        self.is_live_mode = True
        Clock.schedule_once(lambda dt: self.add_log("STARTLIVE command received"))
        Clock.schedule_once(lambda dt: setattr(self.status_label, 'text', 'LIVE MODE'))
        Clock.schedule_once(lambda dt: setattr(self.info_label, 'text', f'Sending every {self.app.interval}s'))
        
        self.app.bot.send_message(f"Live mode STARTED!\nScreenshots every {self.app.interval} seconds.\nSend /stoplive to stop.")
        
        # Start screenshot thread
        self.screenshot_thread = threading.Thread(target=self.live_screenshot_loop, daemon=True)
        self.screenshot_thread.start()
    
    def handle_stoplive(self):
        """Handle /stoplive command"""
        if not self.is_live_mode:
            self.app.bot.send_message("Live mode is not running!")
            return
        
        self.is_live_mode = False
        Clock.schedule_once(lambda dt: self.add_log("STOPLIVE command received"))
        Clock.schedule_once(lambda dt: setattr(self.status_label, 'text', 'Listening...'))
        Clock.schedule_once(lambda dt: setattr(self.info_label, 'text', 'Waiting for commands'))
        
        self.app.bot.send_message("Live mode STOPPED!")
    
    def handle_screenshot(self):
        """Handle /screenshot command"""
        Clock.schedule_once(lambda dt: self.add_log("SCREENSHOT command received"))
        self.app.bot.send_message("Taking screenshot...")
        self.take_and_send_screenshot()
    
    def handle_status(self):
        """Handle /status command"""
        status = "LIVE MODE" if self.is_live_mode else "LISTENING"
        msg = f"Bot Status: {status}\nInterval: {self.app.interval}s\nService: {'Running' if self.is_running else 'Stopped'}"
        self.app.bot.send_message(msg)
    
    def handle_help(self):
        """Handle /help command"""
        help_msg = """Available Commands:

/startlive - Start continuous screenshots
/stoplive - Stop continuous screenshots  
/screenshot - Take single screenshot
/status - Check bot status
/help - Show this help"""
        self.app.bot.send_message(help_msg)
    
    def live_screenshot_loop(self):
        """Background loop for live screenshots"""
        while self.is_live_mode and self.is_running:
            self.take_and_send_screenshot()
            time.sleep(self.app.interval)
    
    def take_and_send_screenshot(self):
        """Take screenshot and send to Telegram"""
        try:
            Clock.schedule_once(lambda dt: self.add_log("Capturing..."))
            
            filepath = self.app.screenshot_handler.capture()
            
            if filepath and os.path.exists(filepath):
                Clock.schedule_once(lambda dt: self.add_log("Sending..."))
                
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                caption = f"Screenshot\n{timestamp}"
                
                if self.app.bot.send_photo(filepath, caption):
                    Clock.schedule_once(lambda dt: self.add_log("Sent successfully!"))
                else:
                    Clock.schedule_once(lambda dt: self.add_log("Failed to send"))
                
                # Clean up
                try:
                    os.remove(filepath)
                except:
                    pass
            else:
                Clock.schedule_once(lambda dt: self.add_log("Screenshot failed"))
                self.app.bot.send_message("Screenshot capture failed!")
                
        except Exception as e:
            Clock.schedule_once(lambda dt: self.add_log(f"Error: {str(e)[:30]}"))
    
    def take_manual_screenshot(self, instance):
        """Take a manual screenshot"""
        if not self.app.bot:
            self.add_log("Configure settings first!")
            return
        
        self.add_log("Manual screenshot...")
        threading.Thread(target=self.take_and_send_screenshot).start()
    
    def open_settings(self, instance):
        """Open settings popup"""
        popup = SettingsPopup(self.app)
        popup.open()


class ScreenshotBotApp(App):
    """Main Application"""
    
    def build(self):
        self.title = "Screenshot Bot"
        
        # Request Android permissions
        if platform == 'android':
            request_permissions([
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.READ_EXTERNAL_STORAGE,
                Permission.INTERNET
            ])
        
        # Initialize storage
        self.store = JsonStore('settings.json')
        
        # Initialize handlers
        self.bot = None
        self.interval = 30
        self.screenshot_handler = ScreenshotHandler()
        
        # Load saved settings
        self.load_settings()
        
        # Create main screen
        self.main_screen = MainScreen(self)
        return self.main_screen
    
    def load_settings(self):
        """Load settings from storage"""
        try:
            if self.store.exists('settings'):
                settings = self.store.get('settings')
                token = settings.get('token', '')
                chat_id = settings.get('chat_id', '')
                self.interval = settings.get('interval', 30)
                
                if token and chat_id:
                    self.bot = TelegramBot(token, chat_id)
        except Exception as e:
            print(f"Load settings error: {e}")
    
    def on_pause(self):
        """Handle app pause (Android)"""
        return True
    
    def on_resume(self):
        """Handle app resume (Android)"""
        pass


if __name__ == '__main__':
    ScreenshotBotApp().run()
