from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label

class ScreenshotApp(App):
    def build(self):
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        self.label = Label(text='Screenshot Bot', font_size=30)
        layout.add_widget(self.label)
        
        btn = Button(text='Take Screenshot', size_hint=(1, 0.3))
        btn.bind(on_press=self.take_screenshot)
        layout.add_widget(btn)
        
        return layout
    
    def take_screenshot(self, instance):
        self.label.text = 'Screenshot captured!'

if __name__ == '__main__':
    ScreenshotApp().run()
