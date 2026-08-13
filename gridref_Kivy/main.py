"""
GridRef - Lat/Long -> MGRS Grid Reference Converter (Android/Kivy edition)

Same conversion engine as the original desktop CLI tool, rebuilt with a
touch-friendly UI for Android 12+.
"""

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.core.clipboard import Clipboard
from kivy.metrics import dp
from kivy.graphics import Color, RoundedRectangle
from kivy.properties import ListProperty
from kivy.uix.widget import Widget

from mgrs_core import (
    Coordinate,
    Precision,
    MGRSConverter,
    InputParser,
    APP_NAME,
    APP_TAGLINE,
)

# ─── Color Theme (mirrors the original rich CLI cyan/dark theme) ───────────

BG_COLOR = (0.043, 0.055, 0.075, 1)         # near-black blue
CARD_COLOR = (0.09, 0.11, 0.15, 1)          # dark slate card
PRIMARY_CYAN = (0.28, 0.85, 0.92, 1)
ACCENT_GREEN = (0.30, 0.85, 0.55, 1)
ERROR_RED = (0.95, 0.35, 0.35, 1)
MUTED_TEXT = (0.6, 0.65, 0.7, 1)
WHITE_TEXT = (0.95, 0.96, 0.97, 1)


class RoundedCard(BoxLayout):
    """A BoxLayout with a rounded rect background, used as a card container."""

    bg_color = ListProperty(CARD_COLOR)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*self.bg_color)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(14)])
        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, *args):
        self._rect.pos = self.pos
        self._rect.size = self.size


class ResultRow(BoxLayout):
    """A single label/value row inside the result card."""

    def __init__(self, label, value, value_color=WHITE_TEXT, **kwargs):
        super().__init__(orientation="horizontal", size_hint_y=None, height=dp(30), **kwargs)
        self.add_widget(
            Label(
                text=label,
                size_hint_x=0.4,
                color=MUTED_TEXT,
                font_size=dp(13),
                halign="right",
                valign="middle",
            )
        )
        val = Label(
            text=value,
            size_hint_x=0.6,
            color=value_color,
            font_size=dp(15),
            bold=True,
            halign="left",
            valign="middle",
        )
        self.add_widget(val)
        # ensure text_size updates for halign to actually apply
        for child in self.children:
            child.bind(size=lambda inst, val: setattr(inst, "text_size", inst.size))


class GridRefRoot(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=dp(16), spacing=dp(12), **kwargs)

        self.converter = MGRSConverter()
        self.parser = InputParser()

        with self.canvas.before:
            Color(*BG_COLOR)
            self._bg = RoundedRectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        self._build_header()
        self._build_scroll_body()

    def _update_bg(self, *args):
        self._bg.pos = self.pos
        self._bg.size = self.size

    # ─── Layout construction ────────────────────────────────────────────

    def _build_header(self):
        header = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(64))
        title = Label(
            text=f"[b]{APP_NAME}[/b]",
            markup=True,
            font_size=dp(26),
            color=PRIMARY_CYAN,
            size_hint_y=None,
            height=dp(36),
        )
        subtitle = Label(
            text=APP_TAGLINE,
            font_size=dp(12),
            color=MUTED_TEXT,
            size_hint_y=None,
            height=dp(20),
        )
        header.add_widget(title)
        header.add_widget(subtitle)
        self.add_widget(header)

    def _build_scroll_body(self):
        scroll = ScrollView(size_hint=(1, 1))
        body = BoxLayout(orientation="vertical", spacing=dp(14), size_hint_y=None, padding=(0, dp(4)))
        body.bind(minimum_height=body.setter("height"))

        # --- Input card ---
        input_card = RoundedCard(orientation="vertical", padding=dp(14), spacing=dp(10),
                                  size_hint_y=None, height=dp(230))

        input_card.add_widget(self._section_label("COORDINATES"))

        self.combined_input = TextInput(
            hint_text="e.g. 28.6139, 77.2090  or 28.6139N, 77.2090E",
            multiline=False,
            size_hint_y=None,
            height=dp(44),
            background_color=(0.15, 0.18, 0.22, 1),
            foreground_color=WHITE_TEXT,
            hint_text_color=MUTED_TEXT,
            padding=(dp(10), dp(12)),
        )
        input_card.add_widget(self.combined_input)

        input_card.add_widget(self._section_label("— or enter separately —"))

        row = BoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None, height=dp(44))
        self.lat_input = TextInput(
            hint_text="Latitude",
            multiline=False,
            background_color=(0.15, 0.18, 0.22, 1),
            foreground_color=WHITE_TEXT,
            hint_text_color=MUTED_TEXT,
            padding=(dp(10), dp(12)),
        )
        self.lon_input = TextInput(
            hint_text="Longitude",
            multiline=False,
            background_color=(0.15, 0.18, 0.22, 1),
            foreground_color=WHITE_TEXT,
            hint_text_color=MUTED_TEXT,
            padding=(dp(10), dp(12)),
        )
        row.add_widget(self.lat_input)
        row.add_widget(self.lon_input)
        input_card.add_widget(row)

        precision_row = BoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None, height=dp(44))
        precision_row.add_widget(
            Label(text="Precision", color=MUTED_TEXT, size_hint_x=0.4, font_size=dp(13))
        )
        self.precision_spinner = Spinner(
            text=Precision.SIX_FIGURE.label,
            values=[p.label for p in Precision],
            size_hint_x=0.6,
            background_color=(0.15, 0.18, 0.22, 1),
            color=WHITE_TEXT,
        )
        precision_row.add_widget(self.precision_spinner)
        input_card.add_widget(precision_row)

        body.add_widget(input_card)

        # --- Convert button ---
        self.convert_btn = Button(
            text="CONVERT",
            size_hint_y=None,
            height=dp(50),
            background_normal="",
            background_color=PRIMARY_CYAN,
            color=(0.02, 0.05, 0.06, 1),
            bold=True,
            font_size=dp(16),
        )
        self.convert_btn.bind(on_release=self.on_convert)
        body.add_widget(self.convert_btn)

        # --- Error label ---
        self.error_label = Label(
            text="",
            color=ERROR_RED,
            size_hint_y=None,
            height=dp(0),
            font_size=dp(13),
        )
        body.add_widget(self.error_label)

        # --- Result card (hidden until first conversion) ---
        self.result_card = RoundedCard(orientation="vertical", padding=dp(14), spacing=dp(4),
                                        size_hint_y=None, height=dp(0), opacity=0)
        body.add_widget(self.result_card)

        # --- Copy button (hidden until result exists) ---
        self.copy_btn = Button(
            text="COPY MGRS TO CLIPBOARD",
            size_hint_y=None,
            height=dp(0),
            opacity=0,
            background_normal="",
            background_color=ACCENT_GREEN,
            color=(0.02, 0.06, 0.03, 1),
            bold=True,
            font_size=dp(14),
        )
        self.copy_btn.bind(on_release=self.on_copy)
        body.add_widget(self.copy_btn)

        scroll.add_widget(body)
        self.add_widget(scroll)
        self._body = body

    def _section_label(self, text):
        return Label(
            text=text,
            color=MUTED_TEXT,
            font_size=dp(11),
            size_hint_y=None,
            height=dp(18),
            halign="left",
        )

    # ─── Actions ─────────────────────────────────────────────────────────

    def on_convert(self, *args):
        self._clear_error()
        try:
            coord = self._resolve_coordinate()
            precision = self._resolve_precision()
            result = self.converter.convert(coord, precision)
            self._show_result(result)
        except ValueError as e:
            self._show_error(str(e))
        except Exception as e:
            self._show_error(f"Unexpected error: {e}")

    def _resolve_coordinate(self) -> Coordinate:
        combined = self.combined_input.text.strip()
        if combined:
            coord = self.parser.try_parse_combined(combined)
            if coord is not None:
                return coord
            # Fall through to try as latitude-only style error
            raise ValueError(
                "Could not parse coordinates. Try '28.6139, 77.2090' "
                "or use the separate Latitude/Longitude fields."
            )

        lat_raw = self.lat_input.text.strip()
        lon_raw = self.lon_input.text.strip()
        if not lat_raw or not lon_raw:
            raise ValueError("Enter coordinates above, or fill both Latitude and Longitude.")

        lat = self.parser.parse_float(lat_raw, "Latitude", -90.0, 90.0)
        lon = self.parser.parse_float(lon_raw, "Longitude", -180.0, 180.0)
        return Coordinate(lat, lon)

    def _resolve_precision(self) -> Precision:
        for p in Precision:
            if p.label == self.precision_spinner.text:
                return p
        return Precision.SIX_FIGURE

    def _show_result(self, result):
        self.result_card.clear_widgets()
        self.result_card.opacity = 1

        rows = [
            ("MGRS Code", result.formatted, PRIMARY_CYAN),
            ("Grid Zone", result.grid_zone, (1, 0.9, 0.4, 1)),
            ("Square ID", result.square_id, ACCENT_GREEN),
            ("Easting", result.easting, PRIMARY_CYAN),
            ("Northing", result.northing, (0.85, 0.6, 0.95, 1)),
            ("Precision", f"{result.precision.label} ({result.precision.accuracy})", WHITE_TEXT),
            ("Input", result.coordinate.display, MUTED_TEXT),
        ]

        header = Label(
            text="[b]RESULT[/b]",
            markup=True,
            color=ACCENT_GREEN,
            font_size=dp(13),
            size_hint_y=None,
            height=dp(22),
            halign="left",
        )
        self.result_card.add_widget(header)

        for label, value, color in rows:
            self.result_card.add_widget(ResultRow(label, value, value_color=color))

        self.result_card.height = dp(22) + dp(30) * len(rows) + dp(28)

        self._last_result_text = result.formatted
        self.copy_btn.height = dp(46)
        self.copy_btn.opacity = 1

    def on_copy(self, *args):
        text = getattr(self, "_last_result_text", "")
        if text:
            Clipboard.copy(text)
            self._flash_copy_confirmation()

    def _flash_copy_confirmation(self):
        original = self.copy_btn.text
        self.copy_btn.text = "COPIED ✓"
        from kivy.clock import Clock
        Clock.schedule_once(lambda dt: setattr(self.copy_btn, "text", original), 1.2)

    def _show_error(self, message):
        self.error_label.text = message
        self.error_label.height = dp(40)

    def _clear_error(self):
        self.error_label.text = ""
        self.error_label.height = dp(0)


class GridRefApp(App):
    def build(self):
        self.title = "GridRef"
        return GridRefRoot()


if __name__ == "__main__":
    GridRefApp().run()
