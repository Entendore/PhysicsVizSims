import kivy
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.slider import Slider
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from kivy.uix.colorpicker import ColorPicker
from kivy.uix.filechooser import FileChooserListView
from kivy.graphics import Color, Line, Ellipse
from kivy.clock import Clock
from kivy.core.window import Window
import numpy as np
import math
import json

kivy.require('2.0.0')

# --- Physics Simulation ---

class NPendulumPhysics:
    """
    Handles the physics simulation for an n-pendulum.
    """
    def __init__(self, n=2, lengths=None, masses=None, initial_angles=None, integrator='rk4'):
        self.n = n
        self.g = 9.81
        self.integrator = integrator

        # Default values if not provided
        self.lengths = np.ones(n) * 100 if lengths is None else np.array(lengths)
        self.masses = np.ones(n) if masses is None else np.array(masses)
        
        # State vector: [theta1, omega1, theta2, omega2, ..., thetan, omegan]
        self.state = np.zeros(2 * n)
        if initial_angles is None:
            self.state[0::2] = np.pi / 2 + np.random.randn(n) * 0.1
        else:
            self.state[0::2] = np.array(initial_angles)

        # --- MODIFIED: Trail for all bobs ---
        self.trails = [[] for _ in range(n)]
        self.max_trail_length = 500

    def derivatives(self, state, t):
        """Calculates the derivatives of the state vector."""
        n = self.n
        theta = state[0::2]
        omega = state[1::2]
        M = np.zeros((n, n))
        G = np.zeros(n)
        for i in range(n):
            for j in range(n):
                sum_k = sum(self.masses[k:] * self.lengths[k] * self.lengths[j] * np.cos(theta[k] - theta[j]) for k in range(max(i, j), n))
                M[i, j] = sum_k
            G[i] = sum(self.masses[i:] * self.lengths[i] * self.g * np.sin(theta[i:]))
        
        c_omega = np.zeros(n)
        for i in range(n):
            for j in range(n):
                for k in range(n):
                    if k != i:
                        sum_m = sum(self.masses[max(i,k):] * self.lengths[max(i,k):] * self.lengths[j] * np.sin(theta[max(i,k):] - theta[j]))
                        c_omega[i] += sum_m * omega[k] * omega[j]
        try:
            alpha = np.linalg.solve(M, -c_omega - G)
        except np.linalg.LinAlgError:
            alpha = np.zeros(n)
        return np.concatenate([omega, alpha])

    # --- NEW: Different Integrator Methods ---
    def euler_step(self, dt):
        self.state += dt * self.derivatives(self.state, 0)

    def verlet_step(self, dt):
        theta = self.state[0::2]
        omega = self.state[1::2]
        n = self.n
        M = np.zeros((n, n))
        G = np.zeros(n)
        for i in range(n):
            for j in range(n):
                sum_k = sum(self.masses[k:] * self.lengths[k] * self.lengths[j] * np.cos(theta[k] - theta[j]) for k in range(max(i, j), n))
                M[i, j] = sum_k
            G[i] = sum(self.masses[i:] * self.lengths[i] * self.g * np.sin(theta[i:]))
        
        c_omega = np.zeros(n) # Verlet doesn't use the C*omega term in the same way
        try:
            alpha = np.linalg.solve(M, -G)
        except np.linalg.LinAlgError:
            alpha = np.zeros(n)
            
        # Update positions
        self.state[0::2] += self.state[1::2] * dt + 0.5 * alpha * dt**2
        
        # Calculate new acceleration
        new_alpha = self.derivatives(self.state, 0)[1::2]
        
        # Update velocities
        self.state[1::2] += 0.5 * (alpha + new_alpha) * dt

    def rk4_step(self, dt):
        k1 = self.derivatives(self.state, 0)
        k2 = self.derivatives(self.state + 0.5 * dt * k1, 0)
        k3 = self.derivatives(self.state + 0.5 * dt * k2, 0)
        k4 = self.derivatives(self.state + dt * k3, 0)
        self.state += (dt / 6.0) * (k1 + 2*k2 + 2*k3 + k4)

    def step(self, dt):
        """Advances the simulation by one time step using the selected integrator."""
        if self.integrator == 'euler':
            self.euler_step(dt)
        elif self.integrator == 'verlet':
            self.verlet_step(dt)
        else: # Default to RK4
            self.rk4_step(dt)
        
        self.state[0::2] = (self.state[0::2] + np.pi) % (2 * np.pi) - np.pi

    def get_positions(self, origin):
        positions = [origin]
        x, y = origin
        for i in range(self.n):
            x += self.lengths[i] * np.sin(self.state[2*i])
            y -= self.lengths[i] * np.cos(self.state[2*i])
            positions.append((x, y))
        return positions

    # --- MODIFIED: Update trail for a specific bob ---
    def update_trail(self, bob_index, pos):
        self.trails[bob_index].append(pos)
        if len(self.trails[bob_index]) > self.max_trail_length:
            self.trails[bob_index].pop(0)

    def calculate_energy(self, origin):
        theta = self.state[0::2]
        omega = self.state[1::2]
        n = self.n
        M = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                sum_k = sum(self.masses[k:] * self.lengths[k] * self.lengths[j] * np.cos(theta[k] - theta[j]) for k in range(max(i, j), n))
                M[i, j] = sum_k
        ke = 0.5 * np.dot(omega, np.dot(M, omega))
        pe = 0
        positions = self.get_positions(origin)
        for i in range(1, len(positions)):
            height = origin[1] - positions[i][1]
            pe += self.masses[i-1] * self.g * height
        return ke, pe, ke + pe

    # --- NEW: Save/Load State Methods ---
    def to_dict(self):
        return {
            'n': self.n,
            'lengths': self.lengths.tolist(),
            'masses': self.masses.tolist(),
            'state': self.state.tolist(),
            'integrator': self.integrator
        }

    def from_dict(self, data):
        self.n = data['n']
        self.lengths = np.array(data['lengths'])
        self.masses = np.array(data['masses'])
        self.state = np.array(data['state'])
        self.integrator = data['integrator']
        self.trails = [[] for _ in range(self.n)] # Reset trails on load

# --- Kivy Visualization ---

class PendulumWidget(Widget):
    def __init__(self, app_ref, **kwargs):
        super().__init__(**kwargs)
        self.app_ref = app_ref # Reference to the main app
        self.physics = None
        self.is_running = False
        self.time_multiplier = 1.0
        self.trace_all_bobs = False
        self.bind(size=self.update_pendulum)

        self.dragging = False
        self.dragged_bob_index = -1
        self.bob_radius = 15

    def initialize_pendulum(self, n, base_length, base_mass, integrator):
        self.physics = NPendulumPhysics(n=n, lengths=[base_length]*n, masses=[base_mass]*n, integrator=integrator)
        self.is_running = False
        self.clear_trails()
        self.update_pendulum()

    def update_pendulum(self, dt=0):
        if not self.physics:
            return

        if self.is_running:
            effective_dt = dt * self.time_multiplier
            effective_dt = min(effective_dt, 0.05)
            self.physics.step(effective_dt)
        
        origin = (self.center_x, self.top - 50)
        positions = self.physics.get_positions(origin)
        
        if self.is_running:
            if self.trace_all_bobs:
                for i in range(self.physics.n):
                    self.physics.update_trail(i, positions[i+1])
            else:
                self.physics.update_trail(self.physics.n - 1, positions[-1])

        self.canvas.clear()
        with self.canvas:
            # --- MODIFIED: Draw trails for all bobs if enabled ---
            for i, trail in enumerate(self.physics.trails):
                if len(trail) > 1:
                    trail_points = [p for pos in trail for p in pos]
                    # Vary color slightly for each bob
                    base_color = self.app_ref.colors['trail']
                    color_variation = (i * 0.1) % 1.0
                    Color(*base_color[:3], a=0.7) 
                    for j in range(0, len(trail_points) - 2, 2):
                        alpha = (j / 2) / len(trail)
                        Color(*base_color[:3], a=alpha * 0.7)
                        Line(points=[trail_points[j], trail_points[j+1], trail_points[j+2], trail_points[j+3]], width=1.5)

            Color(*self.app_ref.colors['rod'])
            for i in range(len(positions) - 1):
                Line(points=positions[i] + positions[i+1], width=2)
            
            Color(*self.app_ref.colors['bob'])
            for i in range(1, len(positions)):
                Ellipse(pos=(positions[i][0] - self.bob_radius, positions[i][1] - self.bob_radius),
                        size=(self.bob_radius * 2, self.bob_radius * 2))
            
            Color(1, 1, 1)
            Ellipse(pos=(origin[0] - 5, origin[1] - 5), size=(10, 10))

        ke, pe, total_e = self.physics.calculate_energy(origin)
        self.app_ref.energy_labels['ke'].text = f"KE: {ke:.2f} J"
        self.app_ref.energy_labels['pe'].text = f"PE: {pe:.2f} J"
        self.app_ref.energy_labels['total'].text = f"Total: {total_e:.2f} J"

    # Touch handlers remain the same
    def on_touch_down(self, touch):
        if not self.physics or self.is_running: return super().on_touch_down(touch)
        origin = (self.center_x, self.top - 50)
        positions = self.physics.get_positions(origin)
        for i in range(1, len(positions)):
            dist = math.hypot(touch.x - positions[i][0], touch.y - positions[i][1])
            if dist < self.bob_radius * 1.5:
                self.dragging = True
                self.dragged_bob_index = i - 1
                return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if not self.dragging: return super().on_touch_move(touch)
        origin = (self.center_x, self.top - 50)
        positions = self.physics.get_positions(origin)
        parent_pos = positions[self.dragged_bob_index]
        dx = touch.x - parent_pos[0]
        dy = touch.y - parent_pos[1]
        new_angle = math.atan2(dx, -dy)
        self.physics.state[self.dragged_bob_index * 2] = new_angle
        self.physics.state[self.dragged_bob_index * 2 + 1] = 0
        self.update_pendulum(dt=0)

    def on_touch_up(self, touch):
        if self.dragging:
            self.dragging = False
            self.dragged_bob_index = -1
        return super().on_touch_up(touch)

    def start_stop(self): self.is_running = not self.is_running
    def clear_trails(self):
        if self.physics: self.physics.trails = [[] for _ in range(self.physics.n)]

    # --- NEW: Save/Load/Export Methods ---
    def save_state(self, path):
        if self.physics:
            with open(path, 'w') as f:
                json.dump(self.physics.to_dict(), f, indent=4)

    def load_state(self, path):
        try:
            with open(path, 'r') as f:
                data = json.load(f)
                self.physics = NPendulumPhysics()
                self.physics.from_dict(data)
                
                # Update UI to reflect loaded state
                self.app_ref.n_slider.value = self.physics.n
                self.app_ref.integrator_spinner.text = self.physics.integrator.capitalize()
                # Note: Length/Mass sliders are not updated as they are now base values
                self.is_running = False
                self.app_ref.start_stop_button.text = 'Start'
                self.clear_trails()
                return True
        except Exception as e:
            print(f"Error loading file: {e}")
            return False

    def export_image(self, path):
        self.export_to_png(path)

# --- Kivy App ---

class PendulumApp(App):
    def build(self):
        Window.clearcolor = (0.1, 0.1, 0.1, 1) # Dark background
        root = BoxLayout(orientation='horizontal')
        
        self.colors = {
            'bob': [0.2, 0.6, 1, 1], 
            'rod': [0.8, 0.8, 0.8, 1], 
            'trail': [1, 0.8, 0.2, 1]  
        }
        
        self.energy_labels = {
            'ke': Label(text='KE: 0.00 J', font_size='12sp'),
            'pe': Label(text='PE: 0.00 J', font_size='12sp'),
            'total': Label(text='Total: 0.00 J', font_size='12sp')
        }
        
        self.pendulum_widget = PendulumWidget(app_ref=self)
        root.add_widget(self.pendulum_widget)

        controls = BoxLayout(orientation='vertical', size_hint=(0.3, 1), spacing=5, padding=10)
        scroll_view = kivy.uix.scrollview.ScrollView(size_hint=(1, 1))
        controls_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=5, padding=10)
        controls_layout.bind(minimum_height=controls_layout.setter('height'))

        # --- Presets ---
        controls_layout.add_widget(Label(text='--- Presets ---', font_size='16sp', size_hint_y=None, height=30))
        self.presets = {
            'Chaos': {'n': 3, 'angles': [np.pi/2, np.pi/2, np.pi/2]},
            'Double Helix': {'n': 4, 'angles': [np.pi/2, -np.pi/2, np.pi/2, -np.pi/2]},
            'Symmetric Drop': {'n': 5, 'angles': [np.pi/4]*5},
            'Custom': None
        }
        self.preset_spinner = Spinner(text='Custom', values=list(self.presets.keys()))
        self.preset_spinner.bind(text=self.on_preset_select)
        controls_layout.add_widget(self.preset_spinner)

        # --- Physics Properties ---
        controls_layout.add_widget(Label(text='--- Physics ---', font_size='16sp', size_hint_y=None, height=30))
        self.n_slider = Slider(min=2, max=10, value=2, step=1)
        self.n_label = Label(text=f'Bobs: {int(self.n_slider.value)}')
        self.n_slider.bind(value=self.on_n_change)
        controls_layout.add_widget(self.n_label); controls_layout.add_widget(self.n_slider)

        self.length_slider = Slider(min=50, max=200, value=100, step=5)
        self.length_label = Label(text=f'Length: {self.length_slider.value:.0f} px')
        self.length_slider.bind(value=self.on_length_change)
        controls_layout.add_widget(self.length_label); controls_layout.add_widget(self.length_slider)

        self.mass_slider = Slider(min=0.5, max=5.0, value=1.0, step=0.1)
        self.mass_label = Label(text=f'Mass: {self.mass_slider.value:.1f} kg')
        self.mass_slider.bind(value=self.on_mass_change)
        controls_layout.add_widget(self.mass_label); controls_layout.add_widget(self.mass_slider)
        
        self.integrator_spinner = Spinner(text='RK4', values=['Euler', 'Verlet', 'RK4'])
        self.integrator_spinner.bind(text=self.on_integrator_change)
        controls_layout.add_widget(Label(text='Integrator:')); controls_layout.add_widget(self.integrator_spinner)

        # --- Simulation Control ---
        controls_layout.add_widget(Label(text='--- Simulation ---', font_size='16sp', size_hint_y=None, height=30))
        self.speed_slider = Slider(min=0.1, max=3.0, value=1.0, step=0.1)
        self.speed_label = Label(text=f'Speed: {self.speed_slider.value:.1f}x')
        self.speed_slider.bind(value=self.on_speed_change)
        controls_layout.add_widget(self.speed_label); controls_layout.add_widget(self.speed_slider)

        self.start_stop_button = Button(text='Start', on_press=self.on_start_stop)
        controls_layout.add_widget(self.start_stop_button)
        controls_layout.add_widget(Button(text='Reset', on_press=self.on_reset))
        controls_layout.add_widget(Button(text='Clear Trails', on_press=self.on_clear_trails))

        # --- Appearance ---
        controls_layout.add_widget(Label(text='--- Appearance ---', font_size='16sp', size_hint_y=None, height=30))
        self.trace_all_checkbox = CheckBox(group='trace')
        controls_layout.add_widget(Label(text='Trace All Bobs'))
        controls_layout.add_widget(self.trace_all_checkbox)
        self.trace_all_checkbox.bind(active=self.on_trace_all_change)
        
        controls_layout.add_widget(Button(text='Bob Color', on_press=lambda x: self.open_color_picker('bob')))
        controls_layout.add_widget(Button(text='Rod Color', on_press=lambda x: self.open_color_picker('rod')))
        controls_layout.add_widget(Button(text='Trail Color', on_press=lambda x: self.open_color_picker('trail')))

        # --- File Operations ---
        controls_layout.add_widget(Label(text='--- File ---', font_size='16sp', size_hint_y=None, height=30))
        controls_layout.add_widget(Button(text='Save State', on_press=self.show_save_dialog))
        controls_layout.add_widget(Button(text='Load State', on_press=self.show_load_dialog))
        controls_layout.add_widget(Button(text='Export Image', on_press=self.show_export_dialog))

        # --- Energy Display ---
        controls_layout.add_widget(Label(text='--- Energy ---', font_size='16sp', size_hint_y=None, height=30))
        controls_layout.add_widget(self.energy_labels['ke'])
        controls_layout.add_widget(self.energy_labels['pe'])
        controls_layout.add_widget(self.energy_labels['total'])
        
        scroll_view.add_widget(controls_layout)
        controls.add_widget(scroll_view)
        root.add_widget(controls)

        Clock.schedule_once(lambda dt: self.on_reset(None))
        Clock.schedule_interval(self.pendulum_widget.update_pendulum, 1.0 / 60.0)
        return root

    # --- Event Handlers ---
    def on_preset_select(self, spinner, text):
        if text == 'Custom' or not self.presets[text]: return
        preset = self.presets[text]
        self.n_slider.value = preset['n']
        self.on_reset(None)
        self.pendulum_widget.physics.state[0::2] = preset['angles']
        self.pendulum_widget.clear_trails()

    def on_n_change(self, instance, value): self.n_label.text = f'Bobs: {int(value)}'
    def on_length_change(self, instance, value): self.length_label.text = f'Length: {value:.0f} px'
    def on_mass_change(self, instance, value): self.mass_label.text = f'Mass: {value:.1f} kg'
    def on_speed_change(self, instance, value):
        self.pendulum_widget.time_multiplier = value
        self.speed_label.text = f'Speed: {value:.1f}x'
    def on_integrator_change(self, spinner, text):
        if self.pendulum_widget.physics:
            self.pendulum_widget.physics.integrator = text.lower()
    def on_trace_all_change(self, checkbox, value): self.pendulum_widget.trace_all_bobs = value

    def on_start_stop(self, instance):
        self.pendulum_widget.start_stop()
        self.start_stop_button.text = 'Stop' if self.pendulum_widget.is_running else 'Start'

    def on_reset(self, instance):
        n = int(self.n_slider.value)
        base_length = self.length_slider.value
        base_mass = self.mass_slider.value
        integrator = self.integrator_spinner.text.lower()
        self.pendulum_widget.initialize_pendulum(n, base_length, base_mass, integrator)
        self.start_stop_button.text = 'Start'
        self.preset_spinner.text = 'Custom'

    def on_clear_trails(self, instance):
        self.pendulum_widget.clear_trails()

    def open_color_picker(self, target):
        popup = Popup(title=f'Choose {target.capitalize()} Color', content=ColorPicker(color=self.colors[target]), size_hint=(0.9, 0.9))
        def on_color_dismiss(instance): self.colors[target] = list(instance.color)
        popup.content.bind(on_dismiss=on_color_dismiss); popup.open()

    # --- File Dialog Helpers ---
    def show_save_dialog(self, instance):
        content = BoxLayout(orientation='vertical')
        filechooser = FileChooserListView(filters=['*.json'])
        save_button = Button(text='Save', size_hint_y=None, height=50)
        content.add_widget(filechooser); content.add_widget(save_button)
        popup = Popup(title='Save State', content=content, size_hint=(0.9, 0.9))
        def save(instance):
            if filechooser.selection:
                self.pendulum_widget.save_state(filechooser.selection[0])
                popup.dismiss()
        save_button.bind(on_press=save); popup.open()

    def show_load_dialog(self, instance):
        content = BoxLayout(orientation='vertical')
        filechooser = FileChooserListView(filters=['*.json'])
        load_button = Button(text='Load', size_hint_y=None, height=50)
        content.add_widget(filechooser); content.add_widget(load_button)
        popup = Popup(title='Load State', content=content, size_hint=(0.9, 0.9))
        def load(instance):
            if filechooser.selection and self.pendulum_widget.load_state(filechooser.selection[0]):
                popup.dismiss()
        load_button.bind(on_press=load); popup.open()

    def show_export_dialog(self, instance):
        content = BoxLayout(orientation='vertical')
        filechooser = FileChooserListView(filters=['*.png'])
        export_button = Button(text='Export', size_hint_y=None, height=50)
        content.add_widget(filechooser); content.add_widget(export_button)
        popup = Popup(title='Export Image', content=content, size_hint=(0.9, 0.9))
        def export(instance):
            if filechooser.selection:
                self.pendulum_widget.export_image(filechooser.selection[0])
                popup.dismiss()
        export_button.bind(on_press=export); popup.open()

if __name__ == '__main__':
    PendulumApp().run()