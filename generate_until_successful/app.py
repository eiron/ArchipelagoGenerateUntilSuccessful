"""
Generate Until Successful - Kivy GUI application.
Repeatedly runs ArchipelagoGenerate until it reports a successfully generated output.
"""

import os
import sys
import subprocess
import threading
import time
import platform

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock

IS_WINDOWS = sys.platform in ("win32", "cygwin", "msys")
IS_MACOS = sys.platform == "darwin"

# Line the generator logs (to both stdout and its log file) right before writing the output zip.
SUCCESS_MARKER = "Creating final archive at "


def get_generate_executable(root):
    """Find the ArchipelagoGenerate executable for the current platform."""
    if IS_WINDOWS:
        exe = os.path.join(root, "ArchipelagoGenerate.exe")
        if os.path.isfile(exe):
            return exe
    # Linux/macOS: could be a script or binary without .exe
    for name in ("ArchipelagoGenerate", "ArchipelagoGenerate.exe"):
        path = os.path.join(root, name)
        if os.path.isfile(path):
            return path
    return None


def get_archipelago_root():
    """Find the Archipelago installation root directory."""
    # Utils.local_path() is the authoritative source - always knows the install location
    try:
        from Utils import local_path
        return local_path()
    except ImportError:
        pass

    # Fallback: walk up from this APWorld's location
    check = os.path.dirname(os.path.abspath(__file__))
    for _ in range(10):
        if get_generate_executable(check):
            return check
        check = os.path.dirname(check)

    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class GenerateApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.archipelago_root = get_archipelago_root()
        self.output_dir = os.path.join(self.archipelago_root, "output")
        self.generate_exe = get_generate_executable(self.archipelago_root)
        self.is_running = False
        self.should_stop = False
        self.current_process = None
        self.latest_line = ""
        self.total_runs = 0
        self.successful_runs = 0
        self.failed_runs = 0
        self.log_lines = []
        self.success_zip_path = None

    def build(self):
        self.title = "Generate Until Successful"
        root = BoxLayout(orientation="vertical", padding=10, spacing=10)

        # Status - current run number
        self.status_label = Label(
            text="Ready to generate",
            size_hint_y=None,
            height=40,
            font_size="18sp",
            bold=True,
        )
        root.add_widget(self.status_label)

        # Latest line from generator
        self.activity_label = Label(
            text="",
            size_hint_y=None,
            height=30,
            font_size="13sp",
            color=(0.8, 0.8, 0.8, 1),
        )
        root.add_widget(self.activity_label)

        # Seed input
        seed_layout = BoxLayout(size_hint_y=None, height=40, spacing=10)
        seed_layout.add_widget(Label(
            text="Seed:",
            size_hint_x=None,
            width=50,
            font_size="14sp",
        ))
        from kivy.uix.textinput import TextInput
        self.seed_input = TextInput(
            hint_text="Leave empty for random",
            multiline=False,
            font_size="14sp",
            size_hint_y=None,
            height=36,
        )
        seed_layout.add_widget(self.seed_input)
        root.add_widget(seed_layout)

        # Successful run target input
        success_goal_layout = BoxLayout(size_hint_y=None, height=40, spacing=10)
        success_goal_layout.add_widget(Label(
            text="Target Successes:",
            size_hint_x=None,
            width=120,
            font_size="14sp",
        ))
        self.success_goal_input = TextInput(
            hint_text="0 = unlimited",
            multiline=False,
            font_size="14sp",
            size_hint_y=None,
            height=36,
            input_filter="int",
        )
        success_goal_layout.add_widget(self.success_goal_input)
        root.add_widget(success_goal_layout)

        # Max failures input
        failures_layout = BoxLayout(size_hint_y=None, height=40, spacing=10)
        failures_layout.add_widget(Label(
            text="Max Failures:",
            size_hint_x=None,
            width=100,
            font_size="14sp",
        ))
        self.max_failures_input = TextInput(
            hint_text="0 = unlimited",
            multiline=False,
            font_size="14sp",
            size_hint_y=None,
            height=36,
            input_filter="int",
        )
        failures_layout.add_widget(self.max_failures_input)
        root.add_widget(failures_layout)

        # Log area - key events only
        scroll = ScrollView(size_hint=(1, 1))
        self.log_label = Label(
            text="Press Start to begin generation runs.\n",
            size_hint_y=None,
            font_size="13sp",
            halign="left",
            valign="top",
        )
        self.log_label.bind(texture_size=self.log_label.setter("size"))
        self.log_label.bind(size=self._update_text_width)
        scroll.add_widget(self.log_label)
        root.add_widget(scroll)

        # Buttons
        btn_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)

        self.start_btn = Button(text="Start", font_size="16sp")
        self.start_btn.bind(on_press=self.start_pressed)
        btn_layout.add_widget(self.start_btn)

        self.stop_btn = Button(text="Stop", font_size="16sp", disabled=True)
        self.stop_btn.bind(on_press=self.stop_pressed)
        btn_layout.add_widget(self.stop_btn)

        self.output_btn = Button(text="Open Output", font_size="16sp")
        self.output_btn.bind(on_press=self.open_output)
        btn_layout.add_widget(self.output_btn)

        self.logs_btn = Button(text="Open Logs", font_size="16sp")
        self.logs_btn.bind(on_press=self.open_logs)
        btn_layout.add_widget(self.logs_btn)

        root.add_widget(btn_layout)

        Clock.schedule_interval(self.update_ui, 0.25)

        return root

    def _update_text_width(self, instance, value):
        instance.text_size = (instance.width, None)

    def start_pressed(self, instance):
        if self.is_running:
            return
        self.log_lines = []
        self.log_label.text = ""
        self.latest_line = ""
        self.start_btn.disabled = True
        self.stop_btn.disabled = False
        self.status_label.text = "Starting..."

        thread = threading.Thread(target=self._generation_loop, daemon=True)
        thread.start()

    def stop_pressed(self, instance):
        self.should_stop = True
        self.stop_btn.disabled = True
        if self.current_process:
            try:
                self.current_process.terminate()
            except Exception:
                pass

    def open_output(self, instance):
        """Open the output folder in the system file manager."""
        os.makedirs(self.output_dir, exist_ok=True)
        if IS_WINDOWS:
            os.startfile(self.output_dir)
        elif IS_MACOS:
            subprocess.Popen(["open", self.output_dir])
        else:
            subprocess.Popen(["xdg-open", self.output_dir])

    def open_logs(self, instance):
        """Open the logs folder in the system file manager."""
        logs_dir = os.path.join(self.archipelago_root, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        if IS_WINDOWS:
            os.startfile(logs_dir)
        elif IS_MACOS:
            subprocess.Popen(["open", logs_dir])
        else:
            subprocess.Popen(["xdg-open", logs_dir])

    def _add_log(self, message):
        """Add a timestamped line to the persistent log area."""
        if message:
            timestamp = time.strftime("%H:%M:%S")
            self.log_lines.append(f"[{timestamp}] {message}")
        else:
            self.log_lines.append("")

    def _generation_loop(self):
        self.is_running = True
        self.should_stop = False
        self.total_runs = 0
        self.successful_runs = 0
        self.failed_runs = 0

        self._add_log(f"Archipelago: {self.archipelago_root}")
        self._add_log("")

        seed = self.seed_input.text.strip()
        failures_text = self.max_failures_input.text.strip()
        success_goal_text = self.success_goal_input.text.strip()
        max_failures = int(failures_text) if failures_text else 0  # 0 means unlimited
        success_goal = int(success_goal_text) if success_goal_text else 0  # 0 means unlimited

        if not self.generate_exe or not os.path.isfile(self.generate_exe):
            self._add_log(f"ERROR: Cannot find ArchipelagoGenerate in {self.archipelago_root}")
            Clock.schedule_once(lambda dt: setattr(self.status_label, "text", "Error - generator not found"))
            self.is_running = False
            Clock.schedule_once(lambda dt: self._on_finished())
            return

        if seed:
            self._add_log(f"Seed: {seed}")
        if max_failures:
            self._add_log(f"Max failures before aborting: {max_failures}")
        if success_goal:
            self._add_log(f"Target successful runs: {success_goal}")
        self._add_log("")

        while not self.should_stop:
            self.total_runs += 1
            self._add_log(f"Run {self.total_runs}...")

            try:
                popen_kwargs = {
                    "cwd": self.archipelago_root,
                    "stdin": subprocess.PIPE,
                    "stdout": subprocess.PIPE,
                    "stderr": subprocess.PIPE,
                    "text": True,
                    "encoding": "utf-8",
                    "errors": "replace",
                }
                if IS_WINDOWS:
                    popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

                cmd = [self.generate_exe]
                if seed:
                    cmd.extend(["--seed", seed])

                self.current_process = subprocess.Popen(
                    cmd,
                    **popen_kwargs,
                )

                try:
                    self.current_process.stdin.write("Y\n")
                    self.current_process.stdin.flush()
                    self.current_process.stdin.close()
                except Exception:
                    pass

                # Read stderr in background
                memory_error_detected = False
                self.success_zip_path = None

                def read_stderr(proc):
                    nonlocal memory_error_detected
                    try:
                        for line in proc.stderr:
                            if line.strip():
                                self.latest_line = f"[{time.strftime('%H:%M:%S')}] {line.rstrip()}"
                                if "MemoryError" in line:
                                    memory_error_detected = True
                                if SUCCESS_MARKER in line:
                                    self.success_zip_path = line.split(SUCCESS_MARKER, 1)[1].strip()
                    except Exception:
                        pass

                stderr_thread = threading.Thread(
                    target=read_stderr,
                    args=(self.current_process,),
                    daemon=True,
                )
                stderr_thread.start()

                # Read stdout, updating the activity line
                for line in self.current_process.stdout:
                    if self.should_stop:
                        self.current_process.terminate()
                        break
                    if line.strip():
                        self.latest_line = f"[{time.strftime('%H:%M:%S')}] {line.rstrip()}"
                        if SUCCESS_MARKER in line:
                            self.success_zip_path = line.split(SUCCESS_MARKER, 1)[1].strip()

                self.current_process.wait()
                stderr_thread.join(timeout=5)

            except Exception as e:
                self._add_log(f"  Error: {e}")
                Clock.schedule_once(lambda dt: setattr(self.status_label, "text", "Error running generator"))
                break
            finally:
                self.current_process = None

            if self.should_stop:
                break

            if memory_error_detected:
                self._add_log("  MemoryError detected. Stopping attempts.")
                Clock.schedule_once(lambda dt: setattr(self.status_label, "text", "Failed - MemoryError"))
                break

            # The generator itself reports success by logging the archive path.
            if self.success_zip_path:
                self.successful_runs += 1
                new_file = os.path.basename(self.success_zip_path)
                self._add_log("")
                self._add_log(f"SUCCESS! Generated on run {self.total_runs}.")
                self._add_log(f"  {new_file}")
                if success_goal:
                    self._add_log(f"  Successful runs: {self.successful_runs}/{success_goal}")
                if success_goal and self.successful_runs >= success_goal:
                    Clock.schedule_once(
                        lambda dt, s=self.successful_runs, g=success_goal: setattr(
                            self.status_label,
                            "text",
                            f"SUCCESS: {s}/{g} run(s) complete!",
                        )
                    )
                    self.latest_line = ""
                    break
                Clock.schedule_once(
                    lambda dt, s=self.successful_runs, r=self.total_runs: setattr(
                        self.status_label,
                        "text",
                        f"SUCCESS: {s} run(s) complete after {r} total run(s)",
                    )
                )
                self.latest_line = ""
                continue
            else:
                self.failed_runs += 1
                if max_failures:
                    self._add_log(f"  Failed. Failures: {self.failed_runs}/{max_failures}")
                else:
                    self._add_log(f"  Failed. Failures: {self.failed_runs}")
                if max_failures and self.failed_runs >= max_failures:
                    self._add_log("")
                    self._add_log(f"Aborted after {self.failed_runs} failed run(s) and {self.total_runs} total run(s).")
                    Clock.schedule_once(lambda dt: setattr(self.status_label, "text", "Failed - max failures reached"))
                    break

        if self.should_stop:
            self._add_log("")
            self._add_log("Stopped by user.")
            Clock.schedule_once(lambda dt: setattr(self.status_label, "text", "Stopped"))
            self.latest_line = ""

        self.is_running = False
        Clock.schedule_once(lambda dt: self._on_finished())

    def _on_finished(self):
        self.start_btn.disabled = False
        self.stop_btn.disabled = True

    def update_ui(self, dt):
        # Update run counters in status while the loop is still active
        if self.is_running and self.total_runs > 0:
            self.status_label.text = (
                f"Run {self.total_runs} | Successes {self.successful_runs} | "
                f"Failures {self.failed_runs}"
            )

        # Update the activity line
        self.activity_label.text = self.latest_line

        # Update log area
        if self.log_lines:
            new_text = "\n".join(self.log_lines)
            self.log_label.text += new_text + "\n"
            self.log_lines = []


def main():
    GenerateApp().run()


if __name__ == "__main__":
    main()
