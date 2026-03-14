"""
Screenshot Telegram Bot - Kivy Version
"""

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.clock import Clock
from kivy.utils import platform

import threading
import requests
import os
import time
from datetime import datetime

if platform == 'android':
    from android.permissions import request_permissions, Permission
    request_permissions([
        Permission.INTERNET,
        Permission.WRITE_EXTERNAL_STORAGE,
        Permission.READ_EXTERNAL_STORAGE
    ])


class ScreenshotBotApp(App):
    
    def build(self):
        self.title = "Screenshot Bot"
        self.is_running = False
        self.bot_token = ""
        self.chat_id = ""
        self.interval = 30
        
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        layout.add_widget(Label(
            text="Screenshot Bot",
            font_size='28sp',
            size_hint_y=None,
            height=60
        ))
        
        layout.add_widget(Label(text="Bot Token:", size_hint_y=None, height=30))
        self.token_input = TextInput(
            multiline=False,
            size_hint_y=None,
            height=45,
            hint_text="Enter your bot token"
        )
        layout.add_widget(self.token_input)
        
        layout.add_widget(Label(text="Chat ID:", size_hint_y=None, height=30))
        self.chat_input = TextInput(
            multiline=False,
            size_hint_y=None,
            height=45,
            hint_text="Enter your chat ID"
        )
        layout.add_widget(self.chat_input)
        
        layout.add_widget(Label(text="Interval (seconds):", size_hint_y=None, height=30))
        self.interval_input = TextInput(
            text="30",
            multiline=False,
            size_hint_y=None,
            height=45,
            input_filter='int'
        )
        layout.add_widget(self.interval_input)
        
        self.status_label = Label(
            text="Status: Stopped",
            font_size='18sp',
            size_hint_y=None,
            height=50
        )
        layout.add_widget(self.status_label)
        
        self.start_btn = Button(
            text="START",
            size_hint_y=None,
            height=60,
            background_color=(0.2, 0.8, 0.2, 1)
        )
        self.start_btn.bind(on_press=self.toggle_service)
        layout.add_widget(self.start_btn)
        
        test_btn = Button(
            text="Test Connection",
            size_hint_y=None,
            height=50,
            background_color=(0.3, 0.5, 0.9, 1)
        )
        test_btn.bind(on_press=self.test_connection)
        layout.add_widget(test_btn)
        
        manual_btn = Button(
            text="Take Screenshot Now",
            size_hint_y=None,
            height=50,
            background_color=(0.9, 0.5, 0.2, 1)
        )
        manual_btn.bind(on_press=self.manual_screenshot)
        layout.add_widget(manual_btn)
        
        self.log_label = Label(
            text="Ready...",
            size_hint_y=None,
            height=80
        )
        layout.add_widget(self.log_label)
        
        return layout
    
    def log(self, message):
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_label.text = f"[{timestamp}] {message}"
    
    def test_connection(self, instance):
        self.bot_token = self.token_input.text.strip()
        self.chat_id = self.chat_input.text.strip()
        
        if not self.bot_token or not self.chat_id:
            self.log("Enter token and chat ID!")
            return
        
        self.log("Testing...")
        
        def test():
            try:
                url = f"https://api.telegram.org/bot{self.bot_token}/getMe"
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    Clock.schedule_once(lambda dt: self.log("Connected!"))
                    self.send_message("Bot connected!")
                else:
                    Clock.schedule_once(lambda dt: self.log("Invalid token!"))
            except Exception as e:
                Clock.schedule_once(lambda dt: self.log("Error!"))
        
        threading.Thread(target=test).start()
    
    def send_message(self, text):
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {"chat_id": self.chat_id, "text": text}
            requests.post(url, data=data, timeout=30)
            return True
        except:
            return False
    
    def send_photo(self, photo_path, caption=""):
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendPhoto"
            data = {"chat_id": self.chat_id, "caption": caption}
            with open(photo_path, 'rb') as photo:
                files = {"photo": photo}
                response = requests.post(url, data=data, files=files, timeout=60)
            return response.status_code == 200
        except:
            return False
    
    def toggle_service(self, instance):
        if self.is_running:
            self.stop_service()
        else:
            self.start_service()
    
    def start_service(self):
        self.bot_token = self.token_input.text.strip()
        self.chat_id = self.chat_input.text.strip()
        
        try:
            self.interval = int(self.interval_input.text)
        except:
            self.interval = 30
        
        if not self.bot_token or not self.chat_id:
            self.log("Enter token and chat ID!")
            return
        
        self.is_running = True
        self.start_btn.text = "STOP"
        self.start_btn.background_color = (0.9, 0.2, 0.2, 1)
        self.status_label.text = "Status: Running"
        self.log("Started!")
        
        threading.Thread(target=self.screenshot_loop, daemon=True).start()
    
    def stop_service(self):
        self.is_running = False
        self.start_btn.text = "START"
        self.start_btn.background_color = (0.2, 0.8, 0.2, 1)
        self.status_label.text = "Status: Stopped"
        self.log("Stopped!")
    
    def screenshot_loop(self):
        while self.is_running:
            self.take_and_send()
            time.sleep(self.interval)
    
    def take_and_send(self):
        try:
            Clock.schedule_once(lambda dt: self.log("Capturing..."))
            
            filepath = self.take_screenshot()
            
            if filepath and os.path.exists(filepath):
                Clock.schedule_once(lambda dt: self.log("Sending..."))
                
                caption = f"Screenshot\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                
                if self.send_photo(filepath, caption):
                    Clock.schedule_once(lambda dt: self.log("Sent!"))
                else:
                    Clock.schedule_once(lambda dt: self.log("Send failed!"))
                
                try:
                    os.remove(filepath)
                except:
                    pass
            else:
                Clock.schedule_once(lambda dt: self.log("Screenshot failed!"))
        except Exception as e:
            Clock.schedule_once(lambda dt: self.log("Error!"))
    
    def take_screenshot(self):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'screenshot_{timestamp}.png'
        
        if platform == 'android':
            filepath = f'/sdcard/Pictures/{filename}'
            os.system(f'screencap -p {filepath}')
            if os.path.exists(filepath):
                return filepath
        return None
    
    def manual_screenshot(self, instance):
        self.bot_token = self.token_input.text.strip()
        self.chat_id = self.chat_input.text.strip()
        
        if not self.bot_token or not self.chat_id:
            self.log("Enter token and chat ID!")
            return
        
        threading.Thread(target=self.take_and_send).start()


if __name__ == '__main__':
    ScreenshotBotApp().run()
