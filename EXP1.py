from __future__ import annotations

import sys
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List, Tuple
import threading
import time
import json

import requests

# -------- SETTINGS --------
API_URL = "https://open.er-api.com/v6/latest"  # new reliable API
TIMEOUT = 10
CACHE_FILE = "rates_cache.json"
CACHE_TTL = 60 * 10  # 10 minutes


# -------- DATA HELPERS --------
def fetch_rates(base: str = "USD") -> Tuple[Dict[str, float], str]:
    """Fetch latest exchange rates for given base currency."""
    try:
        r = requests.get(f"{API_URL}/{base}", timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        if data.get("result") != "success":
            return {}, "API returned error"
        rates = data.get("rates")
        if not isinstance(rates, dict):
            return {}, "Unexpected API response format"
        # cache rates
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as fh:
                json.dump({
                    "base": base,
                    "timestamp": int(time.time()),
                    "rates": rates,
                }, fh)
        except Exception:
            pass
        return {k.upper(): float(v) for k, v in rates.items()}, ""
    except requests.Timeout:
        return {}, "Request timed out. Please try again."
    except requests.RequestException as e:
        return {}, f"Network error: {e}"
    except Exception as e:
        return {}, f"Unexpected error: {e}"


def get_all_currencies() -> List[str]:
    """Get list of supported currency codes (static fallback if needed)."""
    rates, err = fetch_rates("USD")
    # attempt to fallback to cached rates if API fails
    if err:
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as fh:
                cached = json.load(fh)
                if int(time.time()) - int(cached.get("timestamp", 0)) < CACHE_TTL:
                    return sorted([k.upper() for k in cached.get("rates", {}).keys()])
        except Exception:
            pass
        # fallback
        return [
            "USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "CNY", "INR", "NZD",
            "SEK", "NOK", "DKK", "ZAR", "BRL", "HKD", "SGD", "KRW", "MXN", "TRY",
        ]
    return sorted(rates.keys())


CURRENCIES = get_all_currencies()


def convert(amount: float, from_currency: str, to_currency: str) -> Tuple[str, str]:
    """Convert amount using live rates."""
    if from_currency not in CURRENCIES:
        return "", f"Unknown From currency: {from_currency}"
    if to_currency not in CURRENCIES:
        return "", f"Unknown To currency: {to_currency}"
    try:
        amt = float(amount)
    except (TypeError, ValueError):
        return "", "Please enter a valid numeric amount."
    if amt < 0:
        return "", "Amount cannot be negative."
    if from_currency == to_currency:
        return f"{amt:,.4f} {to_currency}", "No conversion needed."

    rates, err = fetch_rates(from_currency)
    if err:
        return "", err
    rate = rates.get(to_currency)
    if rate is None:
        return "", "Rate unavailable."
    converted = amt * rate
    return f"{converted:,.4f} {to_currency}", f"1 {from_currency} = {rate:,.6f} {to_currency}"


# -------- DESKTOP UI --------
class CurrencyConverterApp:
    def __init__(self, root):
        print("[app1] CurrencyConverterApp.__init__ start")
        self.root = root
        self.root.title("💱 Live Currency Converter")
        self.root.geometry("680x540")

        # Modern palette for glassmorphism
        self.colors = {
            'bg_primary': '#0f1724',   # deep navy
            'bg_card': '#12232e',      # card dark
            'bg_secondary': '#19313b', # slightly lighter
            'accent_cyan': '#00d1ff',
            'accent_purple': '#8a2be2',
            'text_primary': '#e6f0f3',
            'text_secondary': '#9fb3bf',
            'success': '#2ee6a6',
            'warning': '#ffb020',
            'danger': '#ff6b88'
        }

        self.root.configure(bg=self.colors['bg_primary'])
        
        # Configure style
        style = ttk.Style()
        style.theme_use('clam')
        # Configure consistent styles for labels, entries, comboboxes and buttons
        try:
            style.configure('Title.TLabel', font=('Segoe UI', 16, 'bold'), foreground=self.colors['text_primary'], background=self.colors['bg_card'])
            style.configure('Subtitle.TLabel', font=('Segoe UI', 10), foreground=self.colors['text_secondary'], background=self.colors['bg_card'])
            style.configure('Custom.TLabel', font=('Segoe UI', 11), foreground=self.colors['text_primary'], background=self.colors['bg_card'])
            style.configure('Custom.TEntry', font=('Segoe UI', 11), fieldbackground=self.colors['bg_secondary'], foreground=self.colors['text_primary'])
            style.configure('Custom.TCombobox', font=('Segoe UI', 11), fieldbackground=self.colors['bg_secondary'], foreground=self.colors['text_primary'])
            style.configure('Flat.TButton', font=('Segoe UI', 10), foreground=self.colors['text_primary'], background=self.colors['bg_card'])
            # Ensure colors apply for readonly/disabled states where supported
            try:
                style.map('Custom.TCombobox', foreground=[('readonly', self.colors['text_primary'])], fieldbackground=[('readonly', self.colors['bg_secondary'])])
                style.map('Custom.TEntry', foreground=[('readonly', self.colors['text_primary'])], fieldbackground=[('readonly', self.colors['bg_secondary'])])
                style.map('Flat.TButton', background=[('active', self.colors['bg_secondary'])], foreground=[('active', self.colors['text_primary'])])
                # Also set default Combobox/Entry styles (fallback) to cover platforms/themes
                style.configure('TCombobox', fieldbackground=self.colors['bg_secondary'], background=self.colors['bg_secondary'], foreground=self.colors['text_primary'])
                style.map('TCombobox', foreground=[('readonly', self.colors['text_primary'])], fieldbackground=[('readonly', self.colors['bg_secondary'])])
                style.configure('TEntry', fieldbackground=self.colors['bg_secondary'], foreground=self.colors['text_primary'])
            except Exception:
                pass
        except Exception:
            # Some themes/platforms may not support certain style options — ignore safely
            pass
        print("[app1] Styles configured; creating widgets...")
        try:
            self.create_widgets()
        except Exception as e:
            import traceback, sys
            traceback.print_exc()
            try:
                messagebox.showerror('Startup error', f'Error during UI setup:\n{e}')
            except Exception:
                pass
            raise
        print("[app1] CurrencyConverterApp.__init__ done")
        # Install Tkinter exception hook to catch callback exceptions
        def _tk_exc_hook(exc, val, tb):
            import traceback
            print('[app1] Tk callback exception:')
            traceback.print_exception(exc, val, tb)
        try:
            self.root.report_callback_exception = lambda exc, val, tb: _tk_exc_hook(exc, val, tb)
        except Exception:
            pass

        # periodic ping to show mainloop is alive
        def _ping():
            try:
                print('[app1] ping: root exists?', bool(self.root.winfo_exists()))
            except Exception as e:
                print('[app1] ping error', e)
            # schedule again in 2 seconds
            try:
                self.root.after(2000, _ping)
            except Exception:
                pass
        try:
            self.root.after(2000, _ping)
        except Exception:
            pass
        
    def create_widgets(self):
        print("[app1] create_widgets start")
        """Build the main UI using glassmorphism cards and the app palette."""
        # Main glass card
        main_frame = self.create_glassmorphism_frame(self.root, pad_x=20, pad_y=20)
        main_frame.pack(fill='both', expand=True, padx=18, pady=18)

        # Title
        title_label = ttk.Label(main_frame, text="💱 Live Currency Converter", style='Title.TLabel')
        title_label.pack(pady=(0, 5))

        subtitle_label = ttk.Label(main_frame, text="Real-time rates powered by open.er-api.com", style='Subtitle.TLabel')
        subtitle_label.pack(pady=(0, 18))

        # Input frame (card)
        input_frame = self.create_glassmorphism_frame(main_frame, pad_x=12, pad_y=10)
        input_frame.pack(fill='x', pady=(0, 18))

        # Amount
        amount_label = ttk.Label(input_frame, text="Amount:", style='Custom.TLabel')
        amount_label.grid(row=0, column=0, sticky='w', pady=(0, 10))

        self.amount_var = tk.StringVar(value="100.0")
        self.amount_entry = ttk.Entry(input_frame, textvariable=self.amount_var, style='Custom.TEntry', width=20)
        self.amount_entry.grid(row=0, column=1, sticky='ew', pady=(0, 10), padx=(10, 0))

        # From currency
        from_label = ttk.Label(input_frame, text="From:", style='Custom.TLabel')
        from_label.grid(row=1, column=0, sticky='w', pady=(0, 10))

        self.from_var = tk.StringVar(value="USD")
        # Use OptionMenu as a reliable, styleable fallback for combobox look
        self.from_combo = tk.OptionMenu(input_frame, self.from_var, *CURRENCIES)
        self.from_combo.config(bg=self.colors['bg_secondary'], fg=self.colors['text_primary'], activebackground=self.colors['bg_secondary'], bd=0)
        try:
            self.from_combo['menu'].config(bg=self.colors['bg_secondary'], fg=self.colors['text_primary'], activebackground=self.colors['bg_card'])
        except Exception:
            pass
        self.from_combo.grid(row=1, column=1, sticky='ew', pady=(0, 10), padx=(10, 0))
        # widget-level fallback: force readable fg/bg where supported
        try:
            self.from_combo.configure(foreground=self.colors['text_primary'], background=self.colors['bg_secondary'])
        except Exception:
            pass

        # To currency
        to_label = ttk.Label(input_frame, text="To:", style='Custom.TLabel')
        to_label.grid(row=2, column=0, sticky='w', pady=(0, 10))

        self.to_var = tk.StringVar(value="EUR")
        self.to_combo = tk.OptionMenu(input_frame, self.to_var, *CURRENCIES)
        self.to_combo.config(bg=self.colors['bg_secondary'], fg=self.colors['text_primary'], activebackground=self.colors['bg_secondary'], bd=0)
        try:
            self.to_combo['menu'].config(bg=self.colors['bg_secondary'], fg=self.colors['text_primary'], activebackground=self.colors['bg_card'])
        except Exception:
            pass
        self.to_combo.grid(row=2, column=1, sticky='ew', pady=(0, 10), padx=(10, 0))
        try:
            self.to_combo.configure(foreground=self.colors['text_primary'], background=self.colors['bg_secondary'])
        except Exception:
            pass

        input_frame.grid_columnconfigure(1, weight=1)

        # Buttons frame
        button_frame = self.create_glassmorphism_frame(main_frame, pad_x=8, pad_y=8)
        button_frame.pack(fill='x', pady=(0, 8))

        left_buttons = tk.Frame(button_frame, bg=self.colors['bg_card'])
        left_buttons.pack(side='left')

        self.swap_btn = ttk.Button(left_buttons, text="Swap ↔", style='Flat.TButton', command=self.swap_currencies)
        self.swap_btn.pack(side='left', padx=(0, 10))

        self.convert_btn = ttk.Button(left_buttons, text="Convert", style='Flat.TButton', command=self.convert_currency)
        self.convert_btn.pack(side='left')

        right_buttons = tk.Frame(button_frame, bg=self.colors['bg_card'])
        right_buttons.pack(side='right')

        self.refresh_btn = ttk.Button(right_buttons, text='Refresh Rates', style='Flat.TButton', command=self.refresh_rates)
        self.refresh_btn.pack(side='right', padx=(5, 0))

        self.copy_btn = ttk.Button(right_buttons, text='Copy Result', style='Flat.TButton', command=self.copy_result)
        self.copy_btn.pack(side='right', padx=(5, 0))

        self.clear_btn = ttk.Button(right_buttons, text='Clear', style='Flat.TButton', command=self.clear_fields)
        self.clear_btn.pack(side='right', padx=(5, 0))

        # Result and history frame inside its own card
        result_frame = self.create_glassmorphism_frame(main_frame, pad_x=12, pad_y=10)
        result_frame.pack(fill='both', expand=True, pady=(10, 0))

        result_label = ttk.Label(result_frame, text="Converted Amount:", style='Custom.TLabel')
        result_label.pack(anchor='w', pady=(0, 5))

        self.result_var = tk.StringVar()
        result_entry = ttk.Entry(result_frame, textvariable=self.result_var, style='Custom.TEntry', state='readonly', font=('Segoe UI', 12, 'bold'))
        result_entry.pack(fill='x', pady=(0, 10))
        try:
            # ensure readonly entry text is visible
            result_entry.configure(foreground=self.colors['text_primary'])
            # for some tk versions, set the tk.Entry options directly
            result_entry.configure(background=self.colors['bg_secondary'])
        except Exception:
            pass

        info_label = ttk.Label(result_frame, text="Exchange Rate Info:", style='Custom.TLabel')
        info_label.pack(anchor='w', pady=(10, 5))

        self.info_text = tk.Text(result_frame, height=4, wrap='word', font=('Segoe UI', 10), state='disabled', bg=self.colors['bg_secondary'], fg=self.colors['text_primary'], relief='flat')
        self.info_text.pack(fill='both', expand=True, pady=(0, 10))

        # History
        history_label = ttk.Label(result_frame, text="Conversion History:", style='Custom.TLabel')
        history_label.pack(anchor='w')

        self.history_list = tk.Listbox(result_frame, height=6, font=('Segoe UI', 10), bg=self.colors['bg_secondary'], fg=self.colors['text_primary'], relief='flat')
        self.history_list.pack(fill='both', expand=False, pady=(5, 10))
        self.history_list.bind('<Double-1>', self.on_history_double)

        # status bar
        self.status_var = tk.StringVar(value='Ready')
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief='flat', anchor='w', background=self.colors['bg_primary'], foreground=self.colors['text_secondary'])
        status_bar.pack(side='bottom', fill='x')

        # progress
        self.progress = ttk.Progressbar(self.root, mode='indeterminate', length=100)
        self.progress.pack(side='bottom', fill='x')

        # keyboard binding
        self.root.bind('<Return>', lambda e: self.convert_currency())

        # Footer
        footer_label = ttk.Label(main_frame, text="Data source: open.er-api.com", style='Subtitle.TLabel')
        footer_label.pack(pady=(10, 0))
    print("[app1] create_widgets done")

    # --- UI helpers for glassmorphism cards ---
    def create_glassmorphism_frame(self, parent, pad_x=12, pad_y=10):
        """Create a safe, simple 'card' frame (avoids complex canvas drawing that can crash on some platforms).

        Returns an inner Frame where callers should place widgets. The outer frame provides padding and a subtle outline.
        """
        # Create a single frame that acts as the card. Do not pack here —
        # let the caller control geometry (pack/grid) to avoid double-packing
        # and layout collapse on some platforms.
        frame = tk.Frame(parent, bg=self.colors['bg_card'], bd=0,
                         highlightthickness=1, highlightbackground=self.colors['bg_secondary'], relief='flat')
        frame.pack_propagate(False)
        return frame

    def _rounded_rect(self, cnv, x1, y1, x2, y2, r, **kwargs):
        # Draw rounded rect using rectangles and ovals
        cnv.create_rectangle(x1 + r, y1, x2 - r, y2, **kwargs)
        cnv.create_rectangle(x1, y1 + r, x2, y2 - r, **kwargs)
        cnv.create_oval(x1, y1, x1 + 2 * r, y1 + 2 * r, **kwargs)
        cnv.create_oval(x2 - 2 * r, y1, x2, y1 + 2 * r, **kwargs)
        cnv.create_oval(x1, y2 - 2 * r, x1 + 2 * r, y2, **kwargs)
        cnv.create_oval(x2 - 2 * r, y2 - 2 * r, x2, y2, **kwargs)

    def _shade_color(self, hexc, percent):
        # Simple shading: percent negative to darken, positive to lighten
        hexc = hexc.lstrip('#')
        r = int(hexc[0:2], 16)
        g = int(hexc[2:4], 16)
        b = int(hexc[4:6], 16)
        def ch(c):
            val = int(c + (percent / 100.0) * 255)
            return max(0, min(255, val))
        return '#%02x%02x%02x' % (ch(r), ch(g), ch(b))
        
    def swap_currencies(self):
        from_val = self.from_var.get()
        to_val = self.to_var.get()
        self.from_var.set(to_val)
        self.to_var.set(from_val)
        
    def convert_currency(self):
        self.convert_btn.config(state='disabled', text='Converting...')
        self.progress.start(10)
        self.status_var.set('Converting...')

        def conversion_thread():
            try:
                amount = float(self.amount_var.get())
                from_currency = self.from_var.get()
                to_currency = self.to_var.get()

                result, info = convert(amount, from_currency, to_currency)

                # append to history
                if result:
                    entry = f"{amount} {from_currency} → {result} ({to_currency})"
                else:
                    entry = f"{amount} {from_currency} → ERROR: {info}"

                self.root.after(0, lambda: self.history_list.insert(0, entry))
                self.root.after(0, self.update_result, result, info)
            except ValueError:
                self.root.after(0, self.update_result, "", "Please enter a valid numeric amount.")
            except Exception as e:
                self.root.after(0, self.update_result, "", f"Error: {str(e)}")
        
        threading.Thread(target=conversion_thread, daemon=True).start()
        
    def update_result(self, result, info):
        self.result_var.set(result)
        
        self.info_text.config(state='normal')
        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(1.0, info)
        self.info_text.config(state='disabled')
        
        self.convert_btn.config(state='normal', text='Convert')
        self.progress.stop()
        self.status_var.set('Ready')

        if not result and info:
            messagebox.showerror("Error", info)
            self.status_var.set(f'Error: {info}')

    # --- Additional UI helpers ---
    def refresh_rates(self):
        """Force refresh the cached rates by calling the API for currently selected base."""
        base = self.from_var.get()
        self.status_var.set('Refreshing rates...')
        self.progress.start(10)

        def do_refresh():
            rates, err = fetch_rates(base)
            time.sleep(0.2)
            self.root.after(0, lambda: self.finish_refresh(err))

        threading.Thread(target=do_refresh, daemon=True).start()

    def finish_refresh(self, err):
        self.progress.stop()
        if err:
            messagebox.showwarning('Refresh', f'Could not refresh rates: {err}')
            self.status_var.set(f'Refresh failed')
        else:
            self.status_var.set('Rates refreshed')

    def copy_result(self):
        val = self.result_var.get()
        if not val:
            messagebox.showinfo('Copy', 'No result to copy')
            return
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(val)
            self.status_var.set('Result copied to clipboard')
        except Exception:
            messagebox.showerror('Copy', 'Failed to copy to clipboard')

    def clear_fields(self):
        self.amount_var.set('')
        self.result_var.set('')
        self.info_text.config(state='normal')
        self.info_text.delete(1.0, tk.END)
        self.info_text.config(state='disabled')
        self.status_var.set('Cleared')

    def on_history_double(self, event):
        sel = self.history_list.curselection()
        if not sel:
            return
        item = self.history_list.get(sel[0])
        # put amount and currencies back into inputs when double-clicking
        try:
            parts = item.split(' ')
            amt = parts[0]
            from_curr = parts[1]
            self.amount_var.set(amt)
            self.from_var.set(from_curr)
            self.status_var.set('Loaded from history')
        except Exception:
            pass


def main() -> int:
    root = tk.Tk()
    print("[app1] main: creating app")
    app = CurrencyConverterApp(root)
    # Log destroy events
    def _on_destroy(event=None):
        try:
            print('[app1] root Destroy event:', event)
        except Exception:
            pass
    root.bind('<Destroy>', _on_destroy)
    # Override window close protocol to log
    def _on_wm_close():
        print('[app1] WM_DELETE_WINDOW called')
        # Do not destroy automatically; call default destroy
        try:
            root.destroy()
        except Exception:
            pass
    root.protocol('WM_DELETE_WINDOW', _on_wm_close)
    # Instrument destroy and quit to log stack traces if called
    try:
        import traceback
        _orig_destroy = root.destroy
        def _logged_destroy(*a, **kw):
            print('[app1] root.destroy() called. Stack trace:')
            traceback.print_stack(limit=10)
            return _orig_destroy(*a, **kw)
        root.destroy = _logged_destroy

        _orig_quit = root.quit
        def _logged_quit(*a, **kw):
            print('[app1] root.quit() called. Stack trace:')
            traceback.print_stack(limit=10)
            return _orig_quit(*a, **kw)
        root.quit = _logged_quit
    except Exception:
        pass
    print("[app1] main: entering mainloop")
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("[app1] mainloop interrupted by KeyboardInterrupt")
    except Exception:
        import traceback
        traceback.print_exc()
    print("[app1] mainloop exited")
    return 0


if __name__ == "__main__":
    sys.exit(main())
