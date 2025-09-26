"""
Personal Finance Dashboard - Simplified & Compatible Version
Works with any Python/tkinter installation
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
from matplotlib.widgets import Cursor
import requests
import os
import threading
import numpy as np
from datetime import datetime
import time
import json
import math

# Optional imports with fallbacks
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


class FinanceDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("💰 Personal Finance Dashboard")
        self.root.geometry("1400x900")
        self.root.configure(bg='#0a0a0a')  # Deep black background
        
        # Vibe color palette
        self.colors = {
            'bg_primary': '#0a0a0a',      # Deep black
            'bg_secondary': '#1a1a2e',    # Dark blue-black
            'bg_card': '#16213e',         # Midnight blue
            'accent_cyan': '#00ffff',     # Electric cyan
            'accent_pink': '#ff00ff',     # Electric magenta
            'accent_purple': '#8a2be2',   # Blue violet
            'text_primary': '#ffffff',    # Pure white
            'text_secondary': '#b0b0b0',  # Light gray
            'success': '#00ff41',         # Matrix green
            'warning': '#ffaa00',         # Amber
            'danger': '#ff0066'           # Hot pink
        }
        
        # Financial data storage
        self.transactions_df = None
        self.portfolio = {}  # {symbol: {'shares': float, 'avg_price': float}}
        self.financial_goals = []  # List of financial goals
        self.loans = []  # Active loans list
        self.cash_balance = 0.0  # Available cash for investments
        
        # Initialize data file for persistence
        self.data_file = "finance_data.json"
        # Flag to indicate whether on-disk data was detected corrupted
        self.data_corrupted = False
        self.load_data()
        
        self.setup_styles()
        self.setup_ui()
        # Start loan scheduler to process per-minute payments
        self.loan_scheduler_running = False
        self.start_loan_scheduler()
        # Start cash interest scheduler
        self.cash_interest_scheduler_running = False
        self.start_cash_interest_scheduler()

    def setup_styles(self):
        """Configure premium ttk styles with glassmorphism effects"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure notebook for glassmorphism tabs
        style.configure('Vibe.TNotebook', 
                       background=self.colors['bg_primary'],
                       borderwidth=0,
                       tabposition='n')
        
        style.configure('Vibe.TNotebook.Tab',
                       background=self.colors['bg_card'],
                       foreground=self.colors['text_primary'],
                       padding=[20, 12],
                       borderwidth=2,
                       relief='flat',
                       font=('Segoe UI', 11, 'bold'))
        
        style.map('Vibe.TNotebook.Tab',
                 background=[('selected', self.colors['accent_cyan']),
                           ('active', self.colors['accent_purple'])],
                 foreground=[('selected', self.colors['bg_primary']),
                           ('active', self.colors['text_primary'])])
    
    def create_glassmorphism_frame(self, parent, bg_color=None):
        """Create a glassmorphism effect frame"""
        if bg_color is None:
            bg_color = self.colors['bg_card']
        
        frame = tk.Frame(parent, bg=bg_color, 
                        highlightbackground=self.colors['accent_cyan'],
                        highlightthickness=1, relief='flat')
        return frame
    
    def load_data(self):
        """Load saved financial data"""
        try:
            if os.path.exists(self.data_file):
                try:
                    with open(self.data_file, 'r') as f:
                        data = json.load(f)
                except json.JSONDecodeError:
                    # If file is corrupted, create a timestamped corrupt backup and try to restore from previous .bak
                    import shutil
                    corrupt_backup = f"{self.data_file}.corrupt.{int(time.time())}.bak"
                    shutil.copy2(self.data_file, corrupt_backup)

                    prev_backup = f"{self.data_file}.bak"
                    restored = False
                    if os.path.exists(prev_backup):
                        try:
                            with open(prev_backup, 'r') as bf:
                                data = json.load(bf)
                            restored = True
                        except Exception:
                            restored = False

                    if restored:
                        messagebox.showinfo(
                            "Data Restoration",
                            f"Data file was corrupted. Restored previous backup ({prev_backup}).\nA corrupt copy was saved as {corrupt_backup}."
                        )
                    else:
                        # Do NOT delete or overwrite the original corrupted file. Keep it for manual inspection.
                        messagebox.showwarning(
                            "Data File Issue",
                            f"Data file appears corrupted. A copy has been saved as {corrupt_backup}.\n"
                            "The original file will be preserved. The app will keep existing in-memory defaults and will NOT overwrite the corrupted file automatically.\n"
                            "If you want to create a new saved file, use Save As from the app or respond Yes when prompted to overwrite."
                        )
                        data = None
                        self.data_corrupted = True
                    
                # If we couldn't load data (data is None), keep existing in-memory state and ensure CASH exists
                if data is None:
                    if not isinstance(self.portfolio, dict):
                        self.portfolio = {'CASH': {'shares': 0.0, 'avg_price': 1.0}}
                    if 'CASH' not in self.portfolio:
                        self.portfolio['CASH'] = {'shares': 0.0, 'avg_price': 1.0}
                    # Do not change self.cash_balance here; keep whatever in-memory value is present
                else:
                    # Load portfolio data from file
                    self.portfolio = data.get('portfolio', {'CASH': {'shares': 0.0, 'avg_price': 1.0}})
                    # Ensure CASH entry exists in portfolio
                    if 'CASH' not in self.portfolio:
                        self.portfolio['CASH'] = {'shares': 0.0, 'avg_price': 1.0}
                    
                # Load transactions if present
                tx = data.get('transactions', None)
                if tx is not None:
                    try:
                        self.transactions_df = pd.DataFrame(tx)
                        if 'date' in self.transactions_df.columns:
                            self.transactions_df['date'] = pd.to_datetime(self.transactions_df['date'])
                    except Exception:
                        self.transactions_df = None
                else:
                    self.transactions_df = None
                    
                    # Load other data with defaults
                    self.financial_goals = data.get('goals', [])
                    self.loans = data.get('loans', [])
                    self.cash_balance = data.get('cash_balance', 0.0)
                    self.csv_loaded = data.get('csv_loaded', False)
                
                # Load last interest time for calculating offline interest
                self.last_interest_time = data.get('last_interest_time', datetime.now().isoformat())
                
                # Validate cash balance matches CASH in portfolio
                if abs(self.cash_balance - self.portfolio['CASH']['shares']) > 0.01:
                    print("Fixing cash balance mismatch...")
                    self.cash_balance = self.portfolio['CASH']['shares']
            else:
                # Initialize with CASH in portfolio
                self.portfolio = {'CASH': {'shares': 0.0, 'avg_price': 1.0}}
                self.financial_goals = []
                self.loans = []
                self.cash_balance = 0.0
                self.transactions_df = None
                self.csv_loaded = False
                self.last_interest_time = datetime.now().isoformat()
                
        except Exception as e:
            print(f"Error loading data: {e}")
            # Initialize with CASH in portfolio
            self.portfolio = {'CASH': {'shares': 0.0, 'avg_price': 1.0}}
            self.financial_goals = []
            self.loans = []
            self.cash_balance = 0.0
            self.transactions_df = None
            self.csv_loaded = False
            self.last_interest_time = datetime.now().isoformat()
            messagebox.showerror("Data Loading Error", 
                               "Could not load previous data. Starting fresh.")
            self.csv_loaded = False
    
    def save_data(self):
        """Save financial data"""
        try:
            # Ensure portfolio has CASH with correct structure
            if 'CASH' not in self.portfolio:
                self.portfolio['CASH'] = {'shares': self.cash_balance, 'avg_price': 1.0}
            else:
                # Sync CASH shares with cash_balance
                self.portfolio['CASH']['shares'] = self.cash_balance
                self.portfolio['CASH']['avg_price'] = 1.0

            # Prepare transactions data if it exists
            transactions_data = None
            if self.transactions_df is not None:
                # Convert datetime to ISO format string for JSON serialization
                tx_data = self.transactions_df.copy()
                if 'date' in tx_data.columns:
                    tx_data['date'] = tx_data['date'].dt.strftime('%Y-%m-%dT%H:%M:%S')
                transactions_data = tx_data.to_dict(orient='records')

            data = {
                'portfolio': self.portfolio,
                'goals': self.financial_goals,
                'loans': self.loans,
                'cash_balance': self.cash_balance,
                'transactions': transactions_data,
                'csv_loaded': getattr(self, 'csv_loaded', False),
                'last_interest_time': getattr(self, 'last_interest_time', datetime.now().isoformat())
            }
            
            # If previously we detected corruption, avoid overwriting the original file without explicit user consent.
            if getattr(self, 'data_corrupted', False):
                # Ask user whether to overwrite the original corrupted file or write to a recovered file instead
                resp = messagebox.askyesno(
                    "Save Data",
                    "The on-disk data file was previously detected as corrupted.\n"
                    "Overwriting may destroy the corrupted file.\n"
                    "Do you want to overwrite the original file? (Yes = overwrite, No = write to a new recovered file)"
                )
                if resp:
                    # Create backup of existing corrupt file first
                    if os.path.exists(self.data_file):
                        backup_file = f"{self.data_file}.bak"
                        import shutil
                        shutil.copy2(self.data_file, backup_file)
                    with open(self.data_file, 'w') as f:
                        json.dump(data, f, indent=2)
                    self.data_corrupted = False
                    messagebox.showinfo('Save', f'Data saved and original file overwritten ({self.data_file}).')
                else:
                    # Write to a new recovered file to avoid touching corrupt original
                    recovered = f"{self.data_file}.recovered.{int(time.time())}.json"
                    with open(recovered, 'w') as f:
                        json.dump(data, f, indent=2)
                    messagebox.showinfo('Save', f'Data saved to recovered file: {recovered}. Original corrupted file preserved.')
            else:
                # Create a backup of existing file if it exists
                if os.path.exists(self.data_file):
                    backup_file = f"{self.data_file}.bak"
                    import shutil
                    shutil.copy2(self.data_file, backup_file)
                # Save new data
                with open(self.data_file, 'w') as f:
                    json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"Error saving data: {e}")
            messagebox.showerror("Data Saving Error", 
                               f"Failed to save data: {str(e)}")
    

    def setup_ui(self):
        """Setup the user interface with premium styling"""


        # Add close (X) button at top right
        close_frame = tk.Frame(self.root, bg=self.colors['bg_primary'])
        close_frame.pack(fill='x', side='top', anchor='ne')
        tk.Button(close_frame, text='✖', command=self.root.destroy, bg=self.colors['danger'], fg=self.colors['text_primary'], borderwidth=0, font=('Segoe UI', 12, 'bold'), relief='flat', padx=8, pady=2, activebackground=self.colors['accent_pink']).pack(side='right', padx=8, pady=4)

        # Create notebook for tabs with premium styling
        self.notebook = ttk.Notebook(self.root, style='Vibe.TNotebook')
        self.notebook.pack(fill='both', expand=True, padx=15, pady=0)

        # Create dashboard tab FIRST and keep reference to its frame
        self.dashboard_frame = self.create_glassmorphism_frame(self.notebook, self.colors['bg_primary'])
        self.notebook.add(self.dashboard_frame, text="🎆 DASHBOARD")

        # Add other tabs
        self.create_expenses_tab()
        self.create_portfolio_tab()
        self.create_goals_tab()
        self.create_stock_tab()
        self.create_currency_tab()
        self.create_charts_tab()

        # Populate dashboard tab UI
        # Create scrollable dashboard
        canvas = tk.Canvas(self.dashboard_frame, bg=self.colors['bg_primary'], highlightthickness=0)
        scrollbar = tk.Scrollbar(self.dashboard_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.colors['bg_primary'])

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Enable mouse wheel and touchpad scrolling
        def _on_mousewheel(event):
            # Windows, Linux: event.delta, Mac: event.delta/120
            if event.num == 5 or event.delta < 0:
                canvas.yview_scroll(1, "units")
            elif event.num == 4 or event.delta > 0:
                canvas.yview_scroll(-1, "units")
        # Windows and MacOS
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        # Linux (button 4/5)
        canvas.bind_all("<Button-4>", _on_mousewheel)
        canvas.bind_all("<Button-5>", _on_mousewheel)

        # Title
        tk.Label(scrollable_frame, text="⚡ UNIFIED FINANCIAL DASHBOARD ⚡", 
                 font=('Segoe UI', 22, 'bold'), fg=self.colors['accent_cyan'], 
                 bg=self.colors['bg_primary']).pack(pady=20)

        # Top row: Key metrics
        metrics_frame = tk.Frame(scrollable_frame, bg=self.colors['bg_primary'])
        metrics_frame.pack(fill='x', padx=20, pady=10)

        # Cash Balance Card
        cash_card = self.create_glassmorphism_frame(metrics_frame)
        cash_card.grid(row=0, column=0, padx=10, pady=10, sticky='ew')
        tk.Label(cash_card, text="💵 CASH BALANCE", font=('Segoe UI', 12, 'bold'),
                 fg=self.colors['accent_cyan'], bg=self.colors['bg_card']).pack(pady=5)
        self.cash_label = tk.Label(cash_card, text=f"${self.cash_balance:,.2f}", 
                                  font=('Segoe UI', 16, 'bold'), fg=self.colors['success'], bg=self.colors['bg_card'])
        self.cash_label.pack(pady=5)

        # Portfolio Value Card
        portfolio_card = self.create_glassmorphism_frame(metrics_frame)
        portfolio_card.grid(row=0, column=1, padx=10, pady=10, sticky='ew')
        tk.Label(portfolio_card, text="📈 PORTFOLIO VALUE", font=('Segoe UI', 12, 'bold'),
                 fg=self.colors['accent_pink'], bg=self.colors['bg_card']).pack(pady=5)
        self.portfolio_value_label = tk.Label(portfolio_card, text="$0.00", font=('Segoe UI', 16, 'bold'), fg=self.colors['warning'], bg=self.colors['bg_card'])
        self.portfolio_value_label.pack(pady=5)

        # Net Worth Card
        networth_card = self.create_glassmorphism_frame(metrics_frame)
        networth_card.grid(row=0, column=2, padx=10, pady=10, sticky='ew')
        tk.Label(networth_card, text="💰 NET WORTH", font=('Segoe UI', 12, 'bold'), fg=self.colors['accent_purple'], bg=self.colors['bg_card']).pack(pady=5)
        self.networth_label = tk.Label(networth_card, text="$0.00", font=('Segoe UI', 16, 'bold'), fg=self.colors['text_primary'], bg=self.colors['bg_card'])
        self.networth_label.pack(pady=5)

        # Loans Card
        loan_card = self.create_glassmorphism_frame(metrics_frame)
        loan_card.grid(row=0, column=3, padx=10, pady=10, sticky='ew')
        tk.Label(loan_card, text="💸 LOANS", font=('Segoe UI', 12, 'bold'), fg=self.colors['accent_pink'], bg=self.colors['bg_card']).pack(pady=5)
        self.loans_label = tk.Label(loan_card, text="No active loans", font=('Segoe UI', 12, 'bold'), fg=self.colors['warning'], bg=self.colors['bg_card'])
        self.loans_label.pack(pady=5)
        tk.Button(loan_card, text="➕ TAKE LOAN", command=self.manage_loans_dialog, bg=self.colors['accent_cyan'], fg=self.colors['bg_primary'], font=('Segoe UI', 10, 'bold'), padx=10, pady=6, relief='flat').pack(pady=5)
        tk.Button(loan_card, text="🛠️ Manage Loans", command=self.manage_loans_dialog, bg=self.colors['bg_card'], fg=self.colors['text_primary'], font=('Segoe UI', 9), padx=8, pady=4, relief='flat').pack(pady=2)

        # Configure grid weights
        metrics_frame.grid_columnconfigure(0, weight=1)
        metrics_frame.grid_columnconfigure(1, weight=1)
        metrics_frame.grid_columnconfigure(2, weight=1)
        metrics_frame.grid_columnconfigure(3, weight=1)


        # --- Transaction Analysis Section ---
        self.analysis_section = self.create_glassmorphism_frame(scrollable_frame)
        self.analysis_section.pack(fill='x', padx=20, pady=10)
        tk.Label(self.analysis_section, text="📊 TRANSACTION ANALYSIS", font=('Segoe UI', 14, 'bold'), fg=self.colors['accent_cyan'], bg=self.colors['bg_card']).pack(pady=10)
        self.analysis_text = tk.Label(self.analysis_section, text="No data loaded", font=('Consolas', 11), fg=self.colors['text_primary'], bg=self.colors['bg_card'], justify='left')
        self.analysis_text.pack(anchor='w', padx=10, pady=5)

        # Recent transactions section
        trans_section = self.create_glassmorphism_frame(scrollable_frame)
        trans_section.pack(fill='x', padx=20, pady=10)
        tk.Label(trans_section, text="📅 RECENT TRANSACTIONS", font=('Segoe UI', 14, 'bold'), fg=self.colors['accent_cyan'], bg=self.colors['bg_card']).pack(pady=10)
        self.recent_trans_frame = tk.Frame(trans_section, bg=self.colors['bg_card'])
        self.recent_trans_frame.pack(fill='x', padx=10, pady=10)
        # Add the transactions label
        self.transactions_label = tk.Label(self.recent_trans_frame, text="No recent transactions",
                                         font=('Segoe UI', 10), fg=self.colors['text_primary'],
                                         bg=self.colors['bg_card'], justify='left')
        self.transactions_label.pack(anchor='w', padx=10)

        # Portfolio summary section
        portfolio_section = self.create_glassmorphism_frame(scrollable_frame)
        portfolio_section.pack(fill='x', padx=20, pady=10)
        tk.Label(portfolio_section, text="📊 PORTFOLIO SUMMARY", font=('Segoe UI', 14, 'bold'), fg=self.colors['accent_pink'], bg=self.colors['bg_card']).pack(pady=10)
        self.portfolio_summary_frame = tk.Frame(portfolio_section, bg=self.colors['bg_card'])
        self.portfolio_summary_frame.pack(fill='x', padx=10, pady=10)

        # Goals progress section
        goals_section = self.create_glassmorphism_frame(scrollable_frame)
        goals_section.pack(fill='x', padx=20, pady=10)
        tk.Label(goals_section, text="🎯 GOALS PROGRESS", font=('Segoe UI', 14, 'bold'), fg=self.colors['accent_purple'], bg=self.colors['bg_card']).pack(pady=10)
        self.goals_summary_frame = tk.Frame(goals_section, bg=self.colors['bg_card'])
        self.goals_summary_frame.pack(fill='x', padx=10, pady=10)

        # Finalize
        self.update_dashboard()

        # Select dashboard tab as default
        self.notebook.select(0)
        
    def update_dashboard(self):
        """Update all dashboard components with current data"""
        try:
            # Update cash balance
            self.cash_label.config(text=f"${self.cash_balance:,.2f}")
            
            # Update portfolio value
            portfolio_value = self.calculate_portfolio_value()
            self.portfolio_value_label.config(text=f"${portfolio_value:,.2f}")
            
            # Update net worth
            net_worth = self.calculate_net_worth()
            self.networth_label.config(text=f"${net_worth:,.2f}")

            # --- Transaction Analysis Update ---
            if self.transactions_df is not None and not self.transactions_df.empty:
                df = self.transactions_df.copy()
                income = df[df['amount'] > 0]['amount'].sum()
                expenses = df[df['amount'] < 0]['amount'].sum()
                net_flow = income + expenses
                # Category breakdown
                cat_summary = df.groupby('category')['amount'].sum().sort_values(ascending=False)
                analysis = f"Income: [38;5;82m${income:,.2f}\u001b[0m\n" \
                           f"Expenses: [38;5;197m${abs(expenses):,.2f}\u001b[0m\n" \
                           f"Net Flow: [38;5;45m${net_flow:,.2f}\u001b[0m\n\n" \
                           f"Category Breakdown:\n"
                for cat, amt in cat_summary.items():
                    color = self.colors['success'] if amt > 0 else self.colors['danger']
                    analysis += f"  {cat}: "+f"${amt:,.2f}"+"\n"
                self.analysis_text.config(text=analysis, fg=self.colors['text_primary'])
            else:
                self.analysis_text.config(text="No transactions loaded.", fg=self.colors['text_secondary'])
            
            # Update recent transactions
            self.update_recent_transactions()
            
            # Update portfolio summary
            self.update_portfolio_summary()
            
            # Update goals progress
            self.update_goals_summary()
            # Update loans display
            if self.loans:
                active = len(self.loans)
                total_owed = sum([loan.get('remaining', loan.get('amount', 0)) for loan in self.loans])
                self.loans_label.config(text=f"{active} active | Owed: ${total_owed:,.2f}")
            else:
                self.loans_label.config(text="No active loans")
            
        except Exception as e:
            print(f"Error updating dashboard: {e}")
            # Show error in UI
            messagebox.showerror("Dashboard Error", f"Failed to update dashboard: {e}")
            
    def calculate_portfolio_value(self):
        """Calculate total portfolio value based on current prices, with CASH always $1/unit"""
        if not self.portfolio:
            return 0.0
        total_value = 0.0
        failed_symbols = []
        try:
            for symbol, data in self.portfolio.items():
                if symbol.upper() == "CASH":
                    # Always $1 per unit for CASH
                    shares = data['shares']
                    value = shares * 1.0
                    total_value += value
                    self.portfolio[symbol]['current_price'] = 1.0
                    continue
                try:
                    # Try to get current price from portfolio data first
                    if 'current_price' in data:
                        current_price = data['current_price']
                    else:
                        if not YFINANCE_AVAILABLE:
                            current_price = data.get('avg_price', 0)
                        else:
                            stock = yf.Ticker(symbol)
                            hist = stock.history(period="1d")
                            if not hist.empty:
                                current_price = hist['Close'].iloc[-1]
                                self.portfolio[symbol]['current_price'] = current_price
                            else:
                                current_price = data.get('avg_price', 0)
                                failed_symbols.append(f"{symbol}: No current data")
                    shares = data['shares']
                    value = current_price * shares
                    total_value += value
                except Exception as e:
                    try:
                        avg_price = data.get('avg_price', 0)
                        shares = data['shares']
                        value = avg_price * shares
                        total_value += value
                        failed_symbols.append(f"{symbol}: {str(e)}")
                    except Exception:
                        failed_symbols.append(f"{symbol}: Error calculating value")
            if failed_symbols:
                print(f"Portfolio calculation warnings: {', '.join(failed_symbols)}")
        except Exception as e:
            print(f"Error calculating portfolio value: {e}")
            return 0.0
        return total_value

    def calculate_net_worth(self):
        """Calculate total net worth including portfolio value and cash balance, minus loans"""
        net_worth = self.calculate_portfolio_value()
        net_worth += self.cash_balance
        
        # Subtract outstanding loan amounts
        for loan in self.loans:
            net_worth -= loan['remaining_amount']
            
        return net_worth
        
    def start_loan_scheduler(self):
        """Start a scheduler to process loan payments every minute"""
        if not self.loan_scheduler_running:
            # Process immediately then schedule
            self.process_loans_minute()
            self.root.after(60000, self.start_loan_scheduler)  # Run every 60 seconds
            self.loan_scheduler_running = True

    def start_cash_interest_scheduler(self):
        """Start a scheduler to add $10 per minute to cash balance if CASH is in portfolio.
        Also handles missed interest from time between sessions."""
        if getattr(self, 'cash_interest_scheduler_running', False):
            return
            
        self.cash_interest_scheduler_running = True
        current_time = datetime.now()
        
        try:
            # Only process if CASH is in portfolio
            cash_holding = self.portfolio.get('CASH') or self.portfolio.get('cash')
            if cash_holding and cash_holding.get('shares', 0) > 0:
                # Calculate missed interest if we have a last interest time
                if hasattr(self, 'last_interest_time'):
                    last_time = datetime.fromisoformat(self.last_interest_time)
                    minutes_passed = int((current_time - last_time).total_seconds() / 60)
                    if minutes_passed > 0:
                        interest_earned = minutes_passed * 10  # $10 per minute
                        self.cash_balance += interest_earned
                        cash_holding['shares'] += interest_earned
                        self.add_transaction_record(
                            current_time.isoformat(), 
                            'Missed Interest', 
                            interest_earned,
                            f'Interest for {minutes_passed} minutes offline'
                        )
                        messagebox.showinfo(
                            "Interest Earned", 
                            f"💰 You earned ${interest_earned:,.2f} in interest\n"
                            f"while you were away for {minutes_passed} minutes!"
                        )
        except (AttributeError, ValueError) as e:
            print(f"Error processing missed interest: {e}")
            
        # Update last interest time
        self.last_interest_time = current_time.isoformat()
        
        def tick():
            try:
                # Only add interest if CASH is in portfolio
                cash_holding = self.portfolio.get('CASH') or self.portfolio.get('cash')
                if cash_holding and cash_holding.get('shares', 0) > 0:
                    # Add $10 per minute
                    self.cash_balance += 10.0
                    cash_holding['shares'] += 10.0
                    self.last_interest_time = datetime.now().isoformat()
                    self.add_transaction_record(
                        datetime.now().isoformat(),
                        'Interest',
                        10.0,
                        'Interest credited to cash'
                    )
                    self.save_data()
                    self.update_dashboard()
            except Exception as e:
                print(f"Error in cash interest scheduler: {e}")
            if self.cash_interest_scheduler_running:
                self.root.after(60 * 1000, tick)
        # Start after 60 seconds
        self.root.after(60 * 1000, tick)

    def stop_loan_scheduler(self):
        self.loan_scheduler_running = False

    def update_recent_transactions(self):
        """Update the recent transactions display"""
        if not hasattr(self, 'transactions_df') or self.transactions_df is None or self.transactions_df.empty:
            self.transactions_label.config(text="No recent transactions")
            return
            
        # Get last 5 transactions, sorted by date
        recent = self.transactions_df.sort_values('date', ascending=False).head(5)
        
        # Format transactions text
        text = "Recent Transactions:\n\n"
        for _, row in recent.iterrows():
            date = pd.to_datetime(row['date']).strftime('%Y-%m-%d')
            amount = f"${row['amount']:,.2f}"
            text += f"📅 {date}: {row['category']} - {amount}\n"
            
        self.transactions_label.config(text=text)

    def process_loans_minute(self):
        """Process loans: for each active loan, deduct per-minute interest from cash balance and reduce mins_left and remaining."""
        updated = False
        to_remove = []
        for loan in list(self.loans):
            try:
                if loan.get('mins_left', 0) <= 0:
                    to_remove.append(loan)
                    continue

                # interest for this minute = fixed dollars per minute
                interest = float(loan.get('interest_per_min', 0.0))

                # Deduct interest from cash balance
                self.cash_balance -= interest

                # Reduce remaining amount and minutes
                loan['remaining'] = max(0.0, loan.get('remaining', loan.get('amount', 0)) - interest)
                loan['mins_left'] = max(0, loan.get('mins_left', 0) - 1)
                updated = True

                # Notification (show dollars)
                self.notify_ui(f"Loan interest charged: ${interest:,.2f}. Minutes left: {loan['mins_left']}")

                # If finished, mark for removal
                if loan['mins_left'] <= 0:
                    to_remove.append(loan)

            except Exception as e:
                print(f"Loan processing error: {e}")

        # Remove finished loans
        for l in to_remove:
            try:
                self.loans.remove(l)
            except Exception:
                pass

        if updated:
            self.save_data()
            self.update_dashboard()

    def notify_ui(self, text):
        """Show a small transient notification label on the main window."""
        try:
            notif = tk.Toplevel(self.root)
            notif.overrideredirect(True)
            notif.attributes('-topmost', True)
            notif.configure(bg=self.colors['bg_secondary'])

            # Position near bottom-right
            notif.update_idletasks()
            w = 320
            h = 60
            x = self.root.winfo_x() + self.root.winfo_width() - w - 20
            y = self.root.winfo_y() + self.root.winfo_height() - h - 40
            notif.geometry(f"{w}x{h}+{x}+{y}")

            tk.Label(notif, text=text, bg=self.colors['bg_secondary'], fg=self.colors['text_primary'], font=('Segoe UI', 10), wraplength=300).pack(fill='both', expand=True, padx=10, pady=10)

            # Auto-destroy after 4 seconds
            notif.after(4000, notif.destroy)
        except Exception:
            # Fallback to messagebox if UI fails
            try:
                messagebox.showinfo("Notification", text)
            except Exception:
                print(text)

    def manage_loans_dialog(self):
        """Dialog to view active loans and allow repayments (clear loan by paying money)."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Manage Loans")
        dialog.geometry("520x360")
        dialog.configure(bg=self.colors['bg_primary'])
        dialog.transient(self.root)
        dialog.grab_set()

        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (520 // 2)
        y = (dialog.winfo_screenheight() // 2) - (360 // 2)
        dialog.geometry(f'520x360+{x}+{y}')

        tk.Label(dialog, text="Manage Loans", font=('Segoe UI', 14, 'bold'), fg=self.colors['accent_purple'], bg=self.colors['bg_primary']).pack(pady=10)

        list_frame = tk.Frame(dialog, bg=self.colors['bg_primary'])
        list_frame.pack(fill='both', expand=True, padx=10, pady=6)

        loan_listbox = tk.Listbox(list_frame, bg=self.colors['bg_secondary'], fg=self.colors['text_primary'], height=8)
        loan_listbox.pack(side='left', fill='both', expand=True, padx=(0,8))

        scrollbar = tk.Scrollbar(list_frame, orient='vertical', command=loan_listbox.yview)
        scrollbar.pack(side='right', fill='y')
        loan_listbox.config(yscrollcommand=scrollbar.set)

        # Populate listbox
        for idx, loan in enumerate(self.loans):
            pid = loan.get('id')
            amt = loan.get('amount', 0)
            rem = loan.get('remaining', 0)
            ipm = loan.get('interest_per_min', loan.get('interest_per_min', 0.0))
            mins = loan.get('mins_left', 0)
            loan_listbox.insert('end', f"{idx+1}. ${amt:,.2f} | remaining: ${rem:,.2f} | ${ipm:.2f}/min | {mins} mins left | id:{pid}")

        # Repayment controls
        control_frame = tk.Frame(dialog, bg=self.colors['bg_primary'])
        control_frame.pack(fill='x', padx=10, pady=8)

        tk.Label(control_frame, text="Repay amount ($):", font=('Segoe UI', 11), fg=self.colors['text_primary'], bg=self.colors['bg_primary']).grid(row=0, column=0, sticky='w')
        repay_var = tk.StringVar(value="0")
        repay_entry = tk.Entry(control_frame, textvariable=repay_var, bg=self.colors['bg_secondary'], fg=self.colors['text_primary'], width=18)
        repay_entry.grid(row=0, column=1, padx=8)

        def repay_selected():
            sel = loan_listbox.curselection()
            if not sel:
                messagebox.showwarning("Select loan", "Please select a loan to repay")
                return
            idx = sel[0]
            try:
                repay_amt = float(repay_var.get())
            except Exception:
                messagebox.showerror("Invalid", "Enter a valid repay amount")
                return
            if repay_amt <= 0:
                messagebox.showerror("Invalid", "Enter positive repay amount")
                return
            if self.cash_balance < repay_amt:
                messagebox.showerror("Insufficient", "Not enough cash balance to repay")
                return

            loan = self.loans[idx]
            # Deduct from cash balance
            self.cash_balance -= repay_amt
            # Reduce loan remaining
            loan['remaining'] = max(0.0, loan.get('remaining', 0.0) - repay_amt)

            # If fully repaid (or remaining <= principal?), remove loan
            if loan['remaining'] <= 0.0:
                try:
                    self.loans.pop(idx)
                    self.notify_ui(f"Loan fully repaid and cleared (${repay_amt:,.2f})")
                except Exception:
                    pass
            else:
                self.notify_ui(f"Repayment made: ${repay_amt:,.2f}. Remaining: ${loan['remaining']:,.2f}")

            self.save_data()
            self.update_dashboard()
            # refresh listbox
            loan_listbox.delete(0, 'end')
            for j, ln in enumerate(self.loans):
                pid = ln.get('id')
                amt = ln.get('amount', 0)
                rem = ln.get('remaining', 0)
                ipm = ln.get('interest_per_min', 0.0)
                mins = ln.get('mins_left', 0)
                loan_listbox.insert('end', f"{j+1}. ${amt:,.2f} | remaining: ${rem:,.2f} | ${ipm:.2f}/min | {mins} mins left | id:{pid}")

        tk.Button(control_frame, text="Repay Selected", command=repay_selected, bg=self.colors['accent_cyan'], fg=self.colors['bg_primary'], padx=12, pady=6).grid(row=0, column=2, padx=8)
        tk.Button(control_frame, text="Close", command=dialog.destroy, bg=self.colors['danger'], fg=self.colors['text_primary'], padx=12, pady=6).grid(row=0, column=3, padx=8)
                    
    def update_portfolio_summary(self):
        """Update portfolio summary display"""
        # Clear previous content
        for widget in self.portfolio_summary_frame.winfo_children():
            widget.destroy()
            
        if not self.portfolio:
            tk.Label(self.portfolio_summary_frame, text="No investments yet", 
                    font=('Segoe UI', 10), fg=self.colors['text_secondary'], 
                    bg=self.colors['bg_card']).pack()
            return
            
        # Show top 5 portfolio holdings
        sorted_holdings = sorted(self.portfolio.items(), 
                               key=lambda x: x[1]['shares'] * x[1].get('current_price', x[1].get('avg_price', 0)), 
                               reverse=True)
        
        top_holdings = sorted_holdings[:5]  # Show top 5
        
        for symbol, data in top_holdings:
            holding_frame = tk.Frame(self.portfolio_summary_frame, bg=self.colors['bg_card'])
            holding_frame.pack(fill='x', pady=2)
            
            shares = data['shares']
            avg_price = data['avg_price']
            current_price = data.get('current_price', avg_price)
            current_value = shares * current_price
            gain_loss = current_value - (shares * avg_price)
            gain_loss_pct = (gain_loss / (shares * avg_price) * 100) if (shares * avg_price) > 0 else 0
            
            # Symbol and value
            tk.Label(holding_frame, text=f"{symbol}: ${current_value:,.0f}", font=('Segoe UI', 10, 'bold'), 
                    fg=self.colors['accent_pink'], bg=self.colors['bg_card']).pack(side='left', padx=5)
            
            # Gain/loss with color coding
            gain_color = self.colors['success'] if gain_loss >= 0 else self.colors['danger']
            tk.Label(holding_frame, text=f"({gain_loss_pct:+.1f}%)", font=('Segoe UI', 10), 
                    fg=gain_color, bg=self.colors['bg_card']).pack(side='right', padx=5)
            
        # Add total portfolio value
        total_value = self.calculate_portfolio_value()
        total_frame = tk.Frame(self.portfolio_summary_frame, bg=self.colors['bg_card'])
        total_frame.pack(fill='x', pady=5)
        
        tk.Label(total_frame, text=f"Total: ${total_value:,.0f}", font=('Segoe UI', 11, 'bold'), 
                fg=self.colors['text_primary'], bg=self.colors['bg_card']).pack(side='left', padx=5)
        
    def update_goals_summary(self):
        """Update financial goals progress display"""
        # Clear previous content
        for widget in self.goals_summary_frame.winfo_children():
            widget.destroy()
            
        if not self.financial_goals:
            tk.Label(self.goals_summary_frame, text="No financial goals set", 
                    font=('Segoe UI', 10), fg=self.colors['text_secondary'], 
                    bg=self.colors['bg_card']).pack()
            return
            
        # Show top 3 goals by progress
        sorted_goals = sorted(self.financial_goals, 
                            key=lambda x: x['current'] / x['target'] if x['target'] > 0 else 0, 
                            reverse=True)
        
        top_goals = sorted_goals[:3]  # Show top 3
        
        for goal in top_goals:
            goal_frame = tk.Frame(self.goals_summary_frame, bg=self.colors['bg_card'])
            goal_frame.pack(fill='x', pady=2)
            
            name = goal['name']
            target = goal['target']
            current = goal['current']
            progress = (current / target) * 100 if target > 0 else 0
            
            # Name label
            tk.Label(goal_frame, text=name, font=('Segoe UI', 10, 'bold'),
                    fg=self.colors['accent_purple'], bg=self.colors['bg_card']).pack(side='left', padx=10)
            
            # Format the goal information
            # Create progress bar directly
            bar_length = 20
            filled_length = int(bar_length * progress // 100)
            bar = '█' * filled_length + '░' * (bar_length - filled_length)
            
            # Progress with color coding
            progress_color = self.colors['success'] if progress >= 100 else (
                             self.colors['warning'] if progress >= 75 else self.colors['text_primary'])
            tk.Label(goal_frame, text=f"${current:,.0f}/${target:,.0f} ({progress:.0f}%)", 
                    font=('Segoe UI', 10), fg=progress_color, 
                    bg=self.colors['bg_card']).pack(side='right', padx=10)
            
        # Add total goals progress
        total_target = sum(goal['target'] for goal in self.financial_goals)
        total_current = sum(goal['current'] for goal in self.financial_goals)
        overall_progress = (total_current / total_target * 100) if total_target > 0 else 0
        
        total_frame = tk.Frame(self.goals_summary_frame, bg=self.colors['bg_card'])
        total_frame.pack(fill='x', pady=5)
        
        overall_color = self.colors['success'] if overall_progress >= 100 else (
                         self.colors['warning'] if overall_progress >= 75 else self.colors['text_primary'])
        tk.Label(total_frame, text=f"Overall: {overall_progress:.0f}% (${total_current:,.0f}/${total_target:,.0f})", 
                font=('Segoe UI', 11, 'bold'), fg=overall_color, 
                bg=self.colors['bg_card']).pack(side='left', padx=5)


    def create_expenses_tab(self):
        """Main expenses and income tab with premium styling"""
        self.main_frame = self.create_glassmorphism_frame(self.notebook, self.colors['bg_primary'])
        self.notebook.add(self.main_frame, text="💳 EXPENSES & INCOME")
        
        # Title with neon glow effect
        title = tk.Label(self.main_frame, text="⚡ PERSONAL FINANCE DASHBOARD ⚡", 
                        font=('Segoe UI', 20, 'bold'), fg=self.colors['accent_cyan'], 
                        bg=self.colors['bg_primary'])
        title.pack(pady=25)
        
        # Buttons frame with glassmorphism
        btn_frame = self.create_glassmorphism_frame(self.main_frame)
        btn_frame.pack(pady=20, padx=20, fill='x')
        
        # Container for buttons
        btn_container = tk.Frame(btn_frame, bg=self.colors['bg_card'])
        btn_container.pack(pady=15)
        
        self.upload_btn = tk.Button(btn_container, text="📁 UPLOAD CSV", 
                                   command=self.upload_csv, bg=self.colors['accent_cyan'], 
                                   fg=self.colors['bg_primary'],
                                   font=('Segoe UI', 12, 'bold'), padx=25, pady=12,
                                   relief='flat', activebackground=self.colors['accent_pink'])
        self.upload_btn.pack(side='left', padx=15)
        
        self.report_btn = tk.Button(btn_container, text="📊 GENERATE REPORT", 
                                   command=self.generate_report, bg=self.colors['success'], 
                                   fg=self.colors['bg_primary'],
                                   font=('Segoe UI', 12, 'bold'), padx=25, pady=12, 
                                   state='disabled', relief='flat',
                                   activebackground=self.colors['warning'])
        self.report_btn.pack(side='left', padx=15)
        
        # Manual transaction button
        self.manual_btn = tk.Button(btn_container, text="➕ ADD TRANSACTION", 
                                   command=self.add_manual_transaction, bg=self.colors['accent_purple'], 
                                   fg=self.colors['text_primary'],
                                   font=('Segoe UI', 12, 'bold'), padx=25, pady=12, 
                                   state='normal', relief='flat',
                                   activebackground=self.colors['accent_cyan'])
        self.manual_btn.pack(side='left', padx=15)
        
        # Allocate funds button
        self.allocate_btn = tk.Button(btn_container, text="💰 ALLOCATE FUNDS", 
                                     command=self.allocate_funds_to_portfolio, bg=self.colors['warning'], 
                                     fg=self.colors['bg_primary'],
                                     font=('Segoe UI', 12, 'bold'), padx=25, pady=12, 
                                     state='normal', relief='flat',
                                     activebackground=self.colors['accent_cyan'])
        self.allocate_btn.pack(side='left', padx=15)
        
        # Status with premium styling
        self.status_label = tk.Label(self.main_frame, text="No file loaded", 
                                    font=('Segoe UI', 11, 'bold'), fg=self.colors['text_secondary'], 
                                    bg=self.colors['bg_primary'])
        self.status_label.pack(pady=15)
        
        # Summary text with dark theme and scrollbar
        text_frame = self.create_glassmorphism_frame(self.main_frame)
        text_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Text widget with scrollbar
        text_container = tk.Frame(text_frame, bg=self.colors['bg_card'])
        text_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.summary_text = tk.Text(text_container, height=20, width=100,
                                   font=('Consolas', 10), bg=self.colors['bg_secondary'], 
                                   fg=self.colors['text_primary'], insertbackground=self.colors['accent_cyan'],
                                   selectbackground=self.colors['accent_purple'], relief='flat')
        
        scrollbar = tk.Scrollbar(text_container, orient='vertical', command=self.summary_text.yview)
        self.summary_text.configure(yscrollcommand=scrollbar.set)
        
        self.summary_text.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Initial welcome message with premium styling
        welcome_message = f"""
{self.colors['accent_cyan']}================================================================
⚡ WELCOME TO ULTIMATE PERSONAL FINANCE DASHBOARD ⚡
================================================================{self.colors['text_primary']}

Upload a CSV file with these columns:
• date: Transaction date (YYYY-MM-DD)
• category: Expense category  
• amount: Amount (positive for income, negative for expenses)

{self.colors['accent_pink']}Sample format:{self.colors['text_primary']}
date,category,amount
2024-01-01,Salary,5000.00
2024-01-02,Food,-45.50
2024-01-03,Rent,-1200.00

{self.colors['success']}Ready to analyze your financial data! 🚀{self.colors['text_primary']}
        """
        self.summary_text.insert('1.0', welcome_message)
    
    def create_portfolio_tab(self):
        """Portfolio management tab with premium styling"""
        self.portfolio_frame = self.create_glassmorphism_frame(self.notebook, self.colors['bg_primary'])
        self.notebook.add(self.portfolio_frame, text="💼 PORTFOLIO")
        
        title = tk.Label(self.portfolio_frame, text="💼 INVESTMENT PORTFOLIO", 
                        font=('Segoe UI', 20, 'bold'), fg=self.colors['accent_pink'], 
                        bg=self.colors['bg_primary'])
        title.pack(pady=20)
        
        # Portfolio controls
        controls_frame = self.create_glassmorphism_frame(self.portfolio_frame)
        controls_frame.pack(pady=10, padx=20, fill='x')
        
        controls_container = tk.Frame(controls_frame, bg=self.colors['bg_card'])
        controls_container.pack(pady=15)
        
        tk.Button(controls_container, text="➕ ADD INVESTMENT", command=self.add_investment,
                 bg=self.colors['accent_cyan'], fg=self.colors['bg_primary'],
                 font=('Segoe UI', 11, 'bold'), padx=15, pady=8, relief='flat').pack(side='left', padx=5)
        
        tk.Button(controls_container, text="💰 SELL INVESTMENT", command=self.sell_investment,
                 bg=self.colors['success'], fg=self.colors['bg_primary'],
                 font=('Segoe UI', 11, 'bold'), padx=15, pady=8, relief='flat').pack(side='left', padx=5)
        
        tk.Button(controls_container, text="❌ REMOVE INVESTMENT", command=self.remove_investment,
                 bg=self.colors['danger'], fg=self.colors['text_primary'],
                 font=('Segoe UI', 11, 'bold'), padx=15, pady=8, relief='flat').pack(side='left', padx=5)
        
        tk.Button(controls_container, text="🔄 UPDATE PRICES", command=self.update_portfolio_prices,
                 bg=self.colors['accent_purple'], fg=self.colors['text_primary'],
                 font=('Segoe UI', 11, 'bold'), padx=15, pady=8, relief='flat').pack(side='left', padx=5)
        
        tk.Button(controls_container, text="💾 EXPORT DATA", command=self.export_portfolio_data,
                 bg=self.colors['warning'], fg=self.colors['bg_primary'],
                 font=('Segoe UI', 11, 'bold'), padx=15, pady=8, relief='flat').pack(side='left', padx=5)
        
        # Portfolio display
        display_frame = tk.Frame(self.portfolio_frame, bg=self.colors['bg_primary'])
        display_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Portfolio holdings (left)
        holdings_frame = self.create_glassmorphism_frame(display_frame)
        holdings_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        tk.Label(holdings_frame, text="📊 PORTFOLIO HOLDINGS", 
                font=('Segoe UI', 14, 'bold'), fg=self.colors['accent_cyan'],
                bg=self.colors['bg_card']).pack(pady=10)
        
        self.holdings_text = tk.Text(holdings_frame, height=15, font=('Consolas', 10),
                                   bg=self.colors['bg_secondary'], fg=self.colors['text_primary'],
                                   insertbackground=self.colors['accent_cyan'])
        holdings_scroll = tk.Scrollbar(holdings_frame, orient='vertical', command=self.holdings_text.yview)
        self.holdings_text.configure(yscrollcommand=holdings_scroll.set)
        
        self.holdings_text.pack(side='left', fill='both', expand=True, padx=10, pady=10)
        holdings_scroll.pack(side='right', fill='y', pady=10)
        
        # Portfolio summary (right)
        summary_frame = self.create_glassmorphism_frame(display_frame)
        summary_frame.pack(side='right', fill='both', expand=True, padx=(10, 0))
        
        tk.Label(summary_frame, text="📈 PORTFOLIO SUMMARY", 
                font=('Segoe UI', 14, 'bold'), fg=self.colors['accent_pink'],
                bg=self.colors['bg_card']).pack(pady=10)
        
        self.summary_text = tk.Text(summary_frame, height=15, font=('Consolas', 10),
                                   bg=self.colors['bg_secondary'], fg=self.colors['text_primary'],
                                   insertbackground=self.colors['accent_cyan'])
        summary_scroll = tk.Scrollbar(summary_frame, orient='vertical', command=self.summary_text.yview)
        self.summary_text.configure(yscrollcommand=summary_scroll.set)
        
        self.summary_text.pack(side='left', fill='both', expand=True, padx=10, pady=10)
        summary_scroll.pack(side='right', fill='y', pady=10)
        
        # Initialize displays
        self.update_portfolio_display()

        self.update_portfolio_display()
        
    def create_stock_tab(self):
        """Stock data tab with premium styling"""
        self.stock_frame = self.create_glassmorphism_frame(self.notebook, self.colors['bg_primary'])
        self.notebook.add(self.stock_frame, text="📈 INVESTMENTS")
        
        title = tk.Label(self.stock_frame, text="📈 STOCK MARKET DATA", 
                        font=('Segoe UI', 20, 'bold'), fg=self.colors['accent_pink'], 
                        bg=self.colors['bg_primary'])
        title.pack(pady=25)
        
        # Stock input with glassmorphism
        input_frame = self.create_glassmorphism_frame(self.stock_frame)
        input_frame.pack(pady=20, padx=20, fill='x')
        
        input_container = tk.Frame(input_frame, bg=self.colors['bg_card'])
        input_container.pack(pady=15)
        
        tk.Label(input_container, text="Symbol:", font=('Segoe UI', 12, 'bold'), 
                fg=self.colors['text_primary'], bg=self.colors['bg_card']).pack(side='left', padx=10)
        
        self.stock_var = tk.StringVar(value="AAPL")
        stock_entry = tk.Entry(input_container, textvariable=self.stock_var, 
                              font=('Segoe UI', 12), width=12, bg=self.colors['bg_secondary'],
                              fg=self.colors['text_primary'], insertbackground=self.colors['accent_cyan'],
                              relief='flat')
        stock_entry.pack(side='left', padx=10)
        
        tk.Button(input_container, text="📊 FETCH DATA", command=self.fetch_stock,
                 bg=self.colors['danger'], fg=self.colors['text_primary'], 
                 font=('Segoe UI', 11, 'bold'), padx=20, pady=8, relief='flat').pack(side='left', padx=10)
        
        tk.Button(input_container, text="📉 SHOW CHART", command=self.show_stock_chart,
                 bg=self.colors['success'], fg=self.colors['bg_primary'], 
                 font=('Segoe UI', 11, 'bold'), padx=20, pady=8, relief='flat').pack(side='left', padx=10)
        
        # Popular stocks info with premium styling
        info_frame = self.create_glassmorphism_frame(self.stock_frame)
        info_frame.pack(fill='x', padx=20, pady=10)
        
        info_label = tk.Label(info_frame, 
                             text="💡 POPULAR STOCKS: AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, NFLX, AMD, INTC", 
                             font=('Segoe UI', 11, 'bold'), fg=self.colors['warning'], 
                             bg=self.colors['bg_card'])
        info_label.pack(pady=15)
        
        # Stock display with premium styling
        display_frame = tk.Frame(self.stock_frame, bg=self.colors['bg_primary'])
        display_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Stock text info (left side) with glassmorphism
        text_frame = self.create_glassmorphism_frame(display_frame)
        text_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        text_container = tk.Frame(text_frame, bg=self.colors['bg_card'])
        text_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.stock_text = tk.Text(text_container, height=18, width=60,
                                 font=('Consolas', 9), bg=self.colors['bg_secondary'], 
                                 fg=self.colors['text_primary'], insertbackground=self.colors['accent_cyan'])
        
        stock_scrollbar = tk.Scrollbar(text_container, orient='vertical', command=self.stock_text.yview)
        self.stock_text.configure(yscrollcommand=stock_scrollbar.set)
        
        self.stock_text.pack(side='left', fill='both', expand=True)
        stock_scrollbar.pack(side='right', fill='y')
        
        # Stock chart area (right side) with glassmorphism
        self.stock_chart_frame = self.create_glassmorphism_frame(display_frame)
        self.stock_chart_frame.pack(side='right', fill='both', expand=True, padx=(10, 0))
        self.stock_chart_frame.configure(width=450)
        
        if not YFINANCE_AVAILABLE:
            self.stock_text.insert('1.0', "Install yfinance for stock data:\npip install yfinance")
        else:
            # Add comprehensive stock info
            stock_info = """
STOCK INVESTMENT GUIDE
=====================

POPULAR STOCKS TO SEARCH:

🏢 TECH GIANTS:
• AAPL - Apple Inc.
• GOOGL - Alphabet Inc. (Google)
• MSFT - Microsoft Corporation
• AMZN - Amazon.com Inc.
• META - Meta Platforms (Facebook)
• NFLX - Netflix Inc.
• NVDA - NVIDIA Corporation
• AMD - Advanced Micro Devices

🚗 AUTOMOTIVE:
• TSLA - Tesla Inc.
• F - Ford Motor Company
• GM - General Motors
• NIO - NIO Inc.

🏦 FINANCIAL:
• JPM - JPMorgan Chase
• BAC - Bank of America
• WFC - Wells Fargo
• GS - Goldman Sachs

🏥 HEALTHCARE:
• JNJ - Johnson & Johnson
• PFE - Pfizer Inc.
• UNH - UnitedHealth Group
• MRNA - Moderna Inc.

⚡ ENERGY:
• XOM - Exxon Mobil
• CVX - Chevron Corporation
• TSLA - Tesla (Electric)

🛒 RETAIL:
• WMT - Walmart Inc.
• HD - Home Depot
• TGT - Target Corporation

✈️ AIRLINES:
• AAL - American Airlines
• DAL - Delta Air Lines
• UAL - United Airlines

TIP: Enter any stock symbol above and click 'Fetch Data' for real-time information!
            """
            self.stock_text.insert('1.0', stock_info)
    
    def show_stock_chart(self):
        """Show professional stock chart with candlesticks"""
        if not YFINANCE_AVAILABLE:
            messagebox.showerror("Error", "Install yfinance: pip install yfinance")
            return
            
        symbol = self.stock_var.get().upper().strip()
        if not symbol:
            messagebox.showwarning("Warning", "Please enter a stock symbol first")
            return
        
        # Clear previous chart
        for widget in self.stock_chart_frame.winfo_children():
            widget.destroy()
        
        # Show loading message
        loading_label = tk.Label(self.stock_chart_frame, text="Loading chart...", 
                                fg=self.colors['warning'], bg=self.colors['bg_secondary'], font=('Arial', 12))
        loading_label.pack(pady=100)
        
        def create_chart():
            try:
                # Fetch stock data
                symbol_val = self.stock_var.get().upper().strip()
                stock = yf.Ticker(symbol_val)
                hist = stock.history(period="3mo")  # 3 months of data
                if hist.empty:
                    self.root.after(0, lambda: self.show_chart_error("No data available for this symbol"))
                    return
                # Schedule chart creation on main thread
                self.root.after(0, lambda: self.create_stock_chart_ui(hist, symbol_val))
            except Exception as e:
                self.root.after(0, lambda: self.show_chart_error(f"Error: {str(e)}"))
        # Create chart in thread
        threading.Thread(target=create_chart, daemon=True).start()
    
    def show_chart_error(self, error_msg):
        """Show error message in chart area"""
        for widget in self.stock_chart_frame.winfo_children():
            widget.destroy()
        error_label = tk.Label(self.stock_chart_frame, text=error_msg, 
                              fg=self.colors['danger'], bg=self.colors['bg_secondary'], font=('Arial', 10))
        error_label.pack(pady=50)
    
    def create_stock_chart_ui(self, hist, symbol):
        """Create stock chart UI on main thread"""
        try:
            # Clear loading message
            for widget in self.stock_chart_frame.winfo_children():
                widget.destroy()
            
            # Create professional stock chart
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 10), 
                                          facecolor='#34495e', gridspec_kw={'height_ratios': [3, 1]})
            
            # Price chart with candlesticks simulation
            ax1.set_facecolor('#2c3e50')
            
            # Calculate moving averages
            hist['MA20'] = hist['Close'].rolling(window=20).mean()
            hist['MA50'] = hist['Close'].rolling(window=50).mean()
            
            # Plot candlestick-style chart
            for i, (date, row) in enumerate(hist.iterrows()):
                color = '#27ae60' if row['Close'] >= row['Open'] else '#e74c3c'
                
                # Draw candlestick body
                body_height = abs(row['Close'] - row['Open'])
                body_bottom = min(row['Close'], row['Open'])
                
                ax1.bar(date, body_height, bottom=body_bottom, 
                       color=color, alpha=0.8, width=0.8)
                
                # Draw wicks
                ax1.plot([date, date], [row['Low'], row['High']], 
                        color=color, linewidth=1, alpha=0.8)
            
            # Add moving averages
            ax1.plot(hist.index, hist['MA20'], color='#f39c12', linewidth=2, 
                    alpha=0.7, label='MA20')
            ax1.plot(hist.index, hist['MA50'], color='#9b59b6', linewidth=2, 
                    alpha=0.7, label='MA50')
            
            # Style price chart
            ax1.set_title(f'{symbol} Stock Price Chart\n(Green=Up, Red=Down)', 
                         color='white', fontsize=14, fontweight='bold', pad=10)
            ax1.set_ylabel('Price ($)', color='white', fontweight='bold')
            ax1.tick_params(colors='white', labelsize=9)
            ax1.grid(True, alpha=0.3, color='white')
            ax1.legend(loc='upper left', fontsize=10)
            
            for spine in ax1.spines.values():
                spine.set_color('white')
            
            # Volume chart
            ax2.set_facecolor('#2c3e50')
            colors = ['#27ae60' if hist['Close'].iloc[i] >= hist['Open'].iloc[i] 
                     else '#e74c3c' for i in range(len(hist))]
            
            ax2.bar(hist.index, hist['Volume'], color=colors, alpha=0.6)
            ax2.set_title('Volume', color='white', fontweight='bold')
            ax2.set_ylabel('Volume', color='white', fontweight='bold')
            ax2.tick_params(colors='white', labelsize=9)
            ax2.grid(True, alpha=0.3, color='white')
            
            for spine in ax2.spines.values():
                spine.set_color('white')
            
            # Format dates
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
            ax2.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
            
            # Add price change info
            current_price = hist['Close'].iloc[-1]
            prev_price = hist['Close'].iloc[-2]
            change = current_price - prev_price
            change_pct = (change / prev_price) * 100
            
            change_text = f"Last: ${current_price:.2f} ({change:+.2f}, {change_pct:+.1f}%)"
            change_color = '#27ae60' if change >= 0 else '#e74c3c'
            
            ax1.text(0.02, 0.98, change_text, transform=ax1.transAxes, 
                    color=change_color, fontweight='bold', fontsize=10,
                    verticalalignment='top', bbox=dict(boxstyle='round', 
                    facecolor='black', alpha=0.7))
            
            plt.tight_layout()
            plt.subplots_adjust(hspace=0.3)
            
            # Embed in tkinter
            canvas = FigureCanvasTkAgg(fig, self.stock_chart_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill='both', expand=True)
            
        except Exception as e:
            self.show_chart_error(f"Chart Error: {str(e)}")
    
    def create_goals_tab(self):
        """Financial goals tracking tab"""
        self.goals_frame = self.create_glassmorphism_frame(self.notebook, self.colors['bg_primary'])
        self.notebook.add(self.goals_frame, text="🎯 GOALS")
        
        title = tk.Label(self.goals_frame, text="🎯 FINANCIAL GOALS TRACKER", 
                        font=('Segoe UI', 20, 'bold'), fg=self.colors['accent_purple'], 
                        bg=self.colors['bg_primary'])
        title.pack(pady=20)
        
        # Goals controls
        controls_frame = self.create_glassmorphism_frame(self.goals_frame)
        controls_frame.pack(pady=10, padx=20, fill='x')
        
        controls_container = tk.Frame(controls_frame, bg=self.colors['bg_card'])
        controls_container.pack(pady=15)
        
        tk.Button(controls_container, text="➕ ADD GOAL", command=self.add_financial_goal,
                 bg=self.colors['accent_cyan'], fg=self.colors['bg_primary'],
                 font=('Segoe UI', 11, 'bold'), padx=15, pady=8, relief='flat').pack(side='left', padx=10)
        
        tk.Button(controls_container, text="✏️ UPDATE GOAL", command=self.update_financial_goal,
                 bg=self.colors['accent_purple'], fg=self.colors['text_primary'],
                 font=('Segoe UI', 11, 'bold'), padx=15, pady=8, relief='flat').pack(side='left', padx=10)
        
        tk.Button(controls_container, text="❌ DELETE GOAL", command=self.delete_financial_goal,
                 bg=self.colors['danger'], fg=self.colors['text_primary'],
                 font=('Segoe UI', 11, 'bold'), padx=15, pady=8, relief='flat').pack(side='left', padx=10)
        
        tk.Button(controls_container, text="💰 ALLOCATE FUNDS", command=self.allocate_funds_to_goal,
                 bg=self.colors['warning'], fg=self.colors['bg_primary'],
                 font=('Segoe UI', 11, 'bold'), padx=15, pady=8, relief='flat').pack(side='left', padx=10)
        
        tk.Button(controls_container, text="🔄 REFRESH", command=self.update_goals_display,
                 bg=self.colors['success'], fg=self.colors['bg_primary'],
                 font=('Segoe UI', 11, 'bold'), padx=15, pady=8, relief='flat').pack(side='left', padx=10)
        
        # Goals display
        display_frame = self.create_glassmorphism_frame(self.goals_frame)
        display_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Replace Text widget with Listbox for better selection
        list_frame = tk.Frame(display_frame, bg=self.colors['bg_card'])
        list_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        scrollbar = tk.Scrollbar(list_frame)
        self.goals_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, 
                                 bg=self.colors['bg_secondary'], fg=self.colors['text_primary'],
                                 selectbackground=self.colors['accent_purple'],
                                 font=('Consolas', 11), height=20)
        scrollbar.config(command=self.goals_listbox.yview)
        
        self.goals_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Initialize display
        self.update_goals_display()
        
    def create_currency_tab(self):
        """Currency conversion tab with premium styling"""
        self.currency_frame = self.create_glassmorphism_frame(self.notebook, self.colors['bg_primary'])
        self.notebook.add(self.currency_frame, text="💱 CURRENCY")
        
        title = tk.Label(self.currency_frame, text="💱 CURRENCY CONVERTER", 
                        font=('Segoe UI', 20, 'bold'), fg=self.colors['accent_purple'], 
                        bg=self.colors['bg_primary'])
        title.pack(pady=30)
        
        # Input frame with glassmorphism
        input_frame = self.create_glassmorphism_frame(self.currency_frame)
        input_frame.pack(pady=30, padx=40)
        
        input_container = tk.Frame(input_frame, bg=self.colors['bg_card'])
        input_container.pack(pady=20, padx=20)
        
        tk.Label(input_container, text="Amount:", font=('Segoe UI', 12, 'bold'), 
                fg=self.colors['text_primary'], bg=self.colors['bg_card']).grid(row=0, column=0, padx=15, pady=15, sticky='e')
        
        self.amount_var = tk.StringVar(value="100")
        amount_entry = tk.Entry(input_container, textvariable=self.amount_var, 
                               font=('Segoe UI', 12), bg=self.colors['bg_secondary'],
                               fg=self.colors['text_primary'], insertbackground=self.colors['accent_cyan'],
                               relief='flat', width=15)
        amount_entry.grid(row=0, column=1, padx=15, pady=15)
        
        tk.Label(input_container, text="From:", font=('Segoe UI', 12, 'bold'), 
                fg=self.colors['text_primary'], bg=self.colors['bg_card']).grid(row=1, column=0, padx=15, pady=15, sticky='e')
        
        self.from_curr = ttk.Combobox(input_container, values=['USD', 'EUR', 'GBP', 'INR', 'JPY'],
                                     font=('Segoe UI', 11), width=12)
        self.from_curr.set('USD')
        self.from_curr.grid(row=1, column=1, padx=15, pady=15)
        
        tk.Label(input_container, text="To:", font=('Segoe UI', 12, 'bold'), 
                fg=self.colors['text_primary'], bg=self.colors['bg_card']).grid(row=2, column=0, padx=15, pady=15, sticky='e')
        
        self.to_curr = ttk.Combobox(input_container, values=['USD', 'EUR', 'GBP', 'INR', 'JPY'],
                                   font=('Segoe UI', 11), width=12)
        self.to_curr.set('INR')
        self.to_curr.grid(row=2, column=1, padx=15, pady=15)
        
        tk.Button(input_container, text="💱 CONVERT", command=self.convert_currency,
                 bg=self.colors['accent_purple'], fg=self.colors['text_primary'], 
                 font=('Segoe UI', 12, 'bold'), padx=25, pady=12, relief='flat').grid(row=3, column=0, columnspan=2, pady=25)
        
        # Result with premium styling
        self.currency_result = tk.Label(self.currency_frame, text="Enter amount and convert", 
                                       font=('Segoe UI', 14, 'bold'), fg=self.colors['warning'], 
                                       bg=self.colors['bg_primary'])
        self.currency_result.pack(pady=20)
    
    def create_charts_tab(self):
        """Charts and reports tab with premium styling"""
        self.charts_frame = self.create_glassmorphism_frame(self.notebook, self.colors['bg_primary'])
        self.notebook.add(self.charts_frame, text="📊 CHARTS")
        
        title = tk.Label(self.charts_frame, text="📊 FINANCIAL CHARTS", 
                        font=('Segoe UI', 20, 'bold'), fg=self.colors['accent_cyan'], 
                        bg=self.colors['bg_primary'])
        title.pack(pady=25)
        
        # Chart buttons with premium styling
        btn_frame = self.create_glassmorphism_frame(self.charts_frame)
        btn_frame.pack(pady=20, padx=20)
        
        btn_container = tk.Frame(btn_frame, bg=self.colors['bg_card'])
        btn_container.pack(pady=15)
        
        self.pie_btn = tk.Button(btn_container, text="📊 EXPENSE PIE CHART", 
                                command=self.show_pie_chart, bg=self.colors['warning'], 
                                fg=self.colors['bg_primary'], font=('Segoe UI', 12, 'bold'), 
                                padx=20, pady=12, state='disabled', relief='flat')
        self.pie_btn.pack(side='left', padx=15)
        
        self.line_btn = tk.Button(btn_container, text="📈 CASH FLOW CHART", 
                                 command=self.show_line_chart, bg=self.colors['success'], 
                                 fg=self.colors['bg_primary'], font=('Segoe UI', 12, 'bold'), 
                                 padx=20, pady=12, state='disabled', relief='flat')
        self.line_btn.pack(side='left', padx=15)
        
        # Chart area with glassmorphism
        self.chart_frame = self.create_glassmorphism_frame(self.charts_frame)
        self.chart_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        placeholder_label = tk.Label(self.chart_frame, 
                                    text="Upload CSV and generate report to enable charts", 
                                    font=('Segoe UI', 14), fg=self.colors['text_secondary'], 
                                    bg=self.colors['bg_card'])
        placeholder_label.pack(expand=True)
    
    def upload_csv(self):
        """Import transactions from a CSV file, robust to missing columns"""
        file_path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if not file_path:
            return
        try:
            import pandas as pd
            df = pd.read_csv(file_path)
            # Accept CSVs with at least date, category, amount; description is optional
            required = {'date', 'category', 'amount'}
            missing = required - set(df.columns)
            if missing:
                messagebox.showerror("CSV Import Error", f"Missing columns: {', '.join(missing)}")
                return
            if 'description' not in df.columns:
                df['description'] = ''
            # Append to transactions_df or create if missing
            if self.transactions_df is None:
                self.transactions_df = df
            else:
                self.transactions_df = pd.concat([self.transactions_df, df], ignore_index=True)
            # Add to persistent transactions list
            for _, row in df.iterrows():
                self.add_transaction_record(
                    str(row['date']),
                    str(row['category']),
                    float(row['amount']),
                    str(row.get('description', ''))
                )
            self.save_data()
            self.update_recent_transactions()
            self.update_dashboard()
            self.notify_ui("CSV imported successfully!")
        except Exception as e:
            messagebox.showerror("CSV Import Error", f"Failed to import CSV: {e}")
    
    def generate_report(self):
        """Generate a summary report of portfolio and transactions"""
        import pandas as pd
        try:
            if self.transactions_df is None or self.transactions_df.empty:
                messagebox.showinfo("No Data", "No transactions to report.")
                return
            df = self.transactions_df.copy()
            # Ensure required columns
            for col in ['date', 'category', 'amount']:
                if col not in df.columns:
                    messagebox.showerror("Report Error", f"Missing column: {col}")
                    return
            if 'description' not in df.columns:
                df['description'] = ''
            # Convert date to datetime for grouping
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            df = df.dropna(subset=['date'])
            # Group by category
            summary = df.groupby('category')['amount'].sum().reset_index()
            # Save report to CSV
            report_path = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[("CSV Files", "*.csv")])
            if not report_path:
                return
            summary.to_csv(report_path, index=False)
            messagebox.showinfo("Report Generated", f"Report saved to {report_path}")
        except Exception as e:
            messagebox.showerror("Report Error", f"Failed to generate report: {e}")
    
    def fetch_stock(self):
        """Fetch stock data"""
        if not YFINANCE_AVAILABLE:
            messagebox.showerror("Error", "Install yfinance: pip install yfinance")
            return
            
        symbol = self.stock_var.get().upper()
        
        def fetch():
            try:
                stock = yf.Ticker(symbol)
                info = stock.info
                hist = stock.history(period="1d")
                
                stock_info = f"""
STOCK DATA: {symbol}
{'='*40}

COMPANY: {info.get('longName', 'N/A')}
SECTOR: {info.get('sector', 'N/A')}

PRICE DATA:
Current: ${info.get('currentPrice', 'N/A')}
Previous Close: ${info.get('previousClose', 'N/A')}
52W High: ${info.get('fiftyTwoWeekHigh', 'N/A')}
52W Low: ${info.get('fiftyTwoWeekLow', 'N/A')}

RECENT PRICES:
"""
                for date, row in hist.tail(10).iterrows():
                    stock_info += f"{date.strftime('%Y-%m-%d')}: ${row['Close']:.2f}\n"
                
                self.root.after(0, lambda: self.update_stock_text(stock_info))
                
            except Exception as e:
                error = f"Error fetching {symbol}: {e}"
                self.root.after(0, lambda: self.update_stock_text(error))
        
        threading.Thread(target=fetch, daemon=True).start()
    
    def update_stock_text(self, text):
        """Update stock display"""
        self.stock_text.delete('1.0', tk.END)
        self.stock_text.insert('1.0', text)
    
    
    def add_investment(self):
        """Add a new investment to the portfolio with current market price"""
        # Create investment dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Investment")
        dialog.geometry("450x450")  # Increased height for cash balance display
        dialog.configure(bg=self.colors['bg_primary'])
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (450 // 2)
        y = (dialog.winfo_screenheight() // 2) - (450 // 2)
        dialog.geometry(f'450x450+{x}+{y}')
        
        tk.Label(dialog, text="Add New Investment", font=('Segoe UI', 16, 'bold'), 
                fg=self.colors['accent_cyan'], bg=self.colors['bg_primary']).pack(pady=10)
                
        # Display current cash balance
        cash_balance_frame = tk.Frame(dialog, bg=self.colors['bg_primary'])
        cash_balance_frame.pack(fill='x', padx=20, pady=5)
        
        cash_balance_label = tk.Label(cash_balance_frame, 
                                     text=f"Current Cash Balance: ${self.cash_balance:,.2f}", 
                                     font=('Segoe UI', 12), 
                                     fg=self.colors['success'], 
                                     bg=self.colors['bg_primary'])
        cash_balance_label.pack(anchor='w')
        
        # Input fields
        input_frame = tk.Frame(dialog, bg=self.colors['bg_primary'])
        input_frame.pack(pady=10)
        
        # Symbol
        tk.Label(input_frame, text="Symbol:", font=('Segoe UI', 11), 
                fg=self.colors['text_primary'], bg=self.colors['bg_primary']).grid(row=0, column=0, sticky='w', pady=5)
        symbol_var = tk.StringVar()
        symbol_entry = tk.Entry(input_frame, textvariable=symbol_var, font=('Segoe UI', 11),
                bg=self.colors['bg_secondary'], fg=self.colors['text_primary'],
                insertbackground=self.colors['accent_cyan'], width=20)
        symbol_entry.grid(row=0, column=1, pady=5, padx=10)
        
        # Company name display
        company_label = tk.Label(input_frame, text="", font=('Segoe UI', 9), 
                               fg=self.colors['text_secondary'], bg=self.colors['bg_primary'])
        company_label.grid(row=1, column=1, sticky='w', pady=2)
        
        # Shares
        tk.Label(input_frame, text="Shares:", font=('Segoe UI', 11), 
                fg=self.colors['text_primary'], bg=self.colors['bg_primary']).grid(row=2, column=0, sticky='w', pady=5)
        shares_var = tk.StringVar()
        shares_entry = tk.Entry(input_frame, textvariable=shares_var, font=('Segoe UI', 11),
                bg=self.colors['bg_secondary'], fg=self.colors['text_primary'],
                insertbackground=self.colors['accent_cyan'], width=20)
        shares_entry.grid(row=2, column=1, pady=5, padx=10)
        
        # Current Price (fetched automatically, but editable)
        tk.Label(input_frame, text="Current Price:", font=('Segoe UI', 11), 
                fg=self.colors['text_primary'], bg=self.colors['bg_primary']).grid(row=3, column=0, sticky='w', pady=5)
        price_var = tk.StringVar()
        price_entry = tk.Entry(input_frame, textvariable=price_var, font=('Segoe UI', 11),
                bg=self.colors['bg_secondary'], fg=self.colors['text_primary'],
                insertbackground=self.colors['accent_cyan'], width=20)
        price_entry.grid(row=3, column=1, pady=5, padx=10)
        
        # Status label for price fetching
        status_label = tk.Label(input_frame, text="", font=('Segoe UI', 9), 
                               fg=self.colors['warning'], bg=self.colors['bg_primary'])
        status_label.grid(row=4, column=0, columnspan=2, pady=5)
        
        def validate_symbol():
            """Validate the stock symbol and display company name"""
            symbol = symbol_var.get().upper().strip()
            if not symbol:
                company_label.config(text="")
                return
                
            company_name, error = self.validate_stock_symbol(symbol)
            if company_name:
                company_label.config(text=company_name, fg=self.colors['success'])
            else:
                company_label.config(text=f"Invalid symbol: {error}", fg=self.colors['danger'])
        
        def fetch_current_price():
            """Fetch current market price for the symbol"""
            symbol = symbol_var.get().upper().strip()
            if not symbol:
                status_label.config(text="Please enter a symbol")
                return
                
            status_label.config(text="Fetching price...")
            dialog.update_idletasks()
            
            current_price, error = self.get_current_stock_price(symbol)
            if current_price:
                price_var.set(f"{current_price:.2f}")
                status_label.config(text=f"Price fetched: ${current_price:.2f}", fg=self.colors['success'])
            else:
                status_label.config(text=f"Error: {error}", fg=self.colors['danger'])
        
        # Bind symbol validation to entry
        symbol_var.trace('w', lambda *args: validate_symbol())
        
        # Fetch price button
        fetch_btn = tk.Button(input_frame, text="🔍 Fetch Price", command=fetch_current_price,
                             bg=self.colors['accent_purple'], fg=self.colors['text_primary'],
                             font=('Segoe UI', 9), padx=10, pady=2, relief='flat')
        fetch_btn.grid(row=0, column=2, padx=5)
        
        def save_investment():
            symbol = symbol_var.get().upper().strip()
            try:
                shares = float(shares_var.get())
                current_price = float(price_var.get())

                if not symbol:
                    messagebox.showerror("Error", "Please enter a stock symbol")
                    return

                if shares <= 0:
                    messagebox.showerror("Error", "Please enter a valid number of shares")
                    return

                if current_price <= 0:
                    messagebox.showerror("Error", "Please enter a valid price")
                    return

                # Calculate total purchase cost
                total_purchase_cost = shares * current_price

                # Check if cash balance is sufficient
                if total_purchase_cost > self.cash_balance:
                    messagebox.showerror("Error", f"Insufficient cash balance. Required: ${total_purchase_cost:,.2f}, Available: ${self.cash_balance:,.2f}")
                    return

                # Calculate average price (for tracking purposes)
                if symbol in self.portfolio:
                    existing_shares = self.portfolio[symbol]['shares']
                    existing_avg_price = self.portfolio[symbol]['avg_price']
                    total_shares = existing_shares + shares
                    total_cost = (existing_shares * existing_avg_price) + (shares * current_price)
                    new_avg_price = total_cost / total_shares
                    self.portfolio[symbol] = {
                        'shares': total_shares,
                        'avg_price': new_avg_price,
                        'current_price': current_price
                    }
                else:
                    self.portfolio[symbol] = {
                        'shares': shares,
                        'avg_price': current_price,
                        'current_price': current_price
                    }

                # Deduct purchase cost from cash balance
                self.cash_balance -= total_purchase_cost

                # Add transaction record
                transaction_date = datetime.now().strftime('%Y-%m-%d')
                self.add_transaction_record(transaction_date, f"Investment: {symbol}", -total_purchase_cost, f"Purchased {shares} shares at ${current_price:,.2f}")

                self.save_data()
                self.update_portfolio_display()
                self.update_dashboard()
                dialog.destroy()
                messagebox.showinfo("Success", f"Added {symbol} to portfolio!\nPurchase cost: ${total_purchase_cost:,.2f}\nRemaining cash balance: ${self.cash_balance:,.2f}")
            except ValueError:
                messagebox.showerror("Error", "Please enter valid numbers for shares and price")

        # Buttons: Save and Cancel
        btn_frame = tk.Frame(dialog, bg=self.colors['bg_primary'])
        btn_frame.pack(pady=15)

        tk.Button(btn_frame, text="💾 Save Investment", command=save_investment,
                 bg=self.colors['success'], fg=self.colors['bg_primary'],
                 font=('Segoe UI', 11, 'bold'), padx=18, pady=6, relief='flat').pack(side='left', padx=10)

        tk.Button(btn_frame, text="Cancel", command=dialog.destroy,
                 bg=self.colors['danger'], fg=self.colors['text_primary'],
                 font=('Segoe UI', 11, 'bold'), padx=18, pady=6, relief='flat').pack(side='left', padx=10)

        # Autofocus symbol entry for convenience
        symbol_entry.focus_set()
        
    
    def add_manual_transaction(self):
        """Add a manual transaction to the transactions dataframe"""
        # Create transaction dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Manual Transaction")
        dialog.geometry("400x350")
        dialog.configure(bg=self.colors['bg_primary'])
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (dialog.winfo_screenheight() // 2) - (350 // 2)
        dialog.geometry(f'400x350+{x}+{y}')
        
        tk.Label(dialog, text="Add Manual Transaction", font=('Segoe UI', 16, 'bold'), 
                fg=self.colors['accent_cyan'], bg=self.colors['bg_primary']).pack(pady=20)
        
        # Input fields
        input_frame = tk.Frame(dialog, bg=self.colors['bg_primary'])
        input_frame.pack(pady=10)
        
        # Date
        tk.Label(input_frame, text="Date:", font=('Segoe UI', 11), 
                fg=self.colors['text_primary'], bg=self.colors['bg_primary']).grid(row=0, column=0, sticky='w', pady=5)
        date_var = tk.StringVar(value=datetime.now().strftime('%Y-%m-%d'))
        date_entry = tk.Entry(input_frame, textvariable=date_var, font=('Segoe UI', 11),
                bg=self.colors['bg_secondary'], fg=self.colors['text_primary'],
                insertbackground=self.colors['accent_cyan'], width=20)
        date_entry.grid(row=0, column=1, pady=5, padx=10)
        
        # Category
        tk.Label(input_frame, text="Category:", font=('Segoe UI', 11), 
                fg=self.colors['text_primary'], bg=self.colors['bg_primary']).grid(row=1, column=0, sticky='w', pady=5)
        category_var = tk.StringVar()
        category_entry = tk.Entry(input_frame, textvariable=category_var, font=('Segoe UI', 11),
                bg=self.colors['bg_secondary'], fg=self.colors['text_primary'],
                insertbackground=self.colors['accent_cyan'], width=20)
        category_entry.grid(row=1, column=1, pady=5, padx=10)
        
        # Amount
        tk.Label(input_frame, text="Amount:", font=('Segoe UI', 11), 
                fg=self.colors['text_primary'], bg=self.colors['bg_primary']).grid(row=2, column=0, sticky='w', pady=5)
        amount_var = tk.StringVar()
        amount_entry = tk.Entry(input_frame, textvariable=amount_var, font=('Segoe UI', 11),
                bg=self.colors['bg_secondary'], fg=self.colors['text_primary'],
                insertbackground=self.colors['accent_cyan'], width=20)
        amount_entry.grid(row=2, column=1, pady=5, padx=10)
        
        # Description
        tk.Label(input_frame, text="Description:", font=('Segoe UI', 11), 
                fg=self.colors['text_primary'], bg=self.colors['bg_primary']).grid(row=3, column=0, sticky='w', pady=5)
        description_var = tk.StringVar()
        description_entry = tk.Entry(input_frame, textvariable=description_var, font=('Segoe UI', 11),
                bg=self.colors['bg_secondary'], fg=self.colors['text_primary'],
                insertbackground=self.colors['accent_cyan'], width=20)
        description_entry.grid(row=3, column=1, pady=5, padx=10)
        
        # Quick category buttons
        categories = ["Salary", "Food", "Rent", "Utilities", "Entertainment", "Shopping", "Travel", "Investment", "Other"]
        category_frame = tk.Frame(dialog, bg=self.colors['bg_primary'])
        category_frame.pack(pady=10)
        
        def set_category(cat):
            category_var.set(cat)
        
        tk.Label(category_frame, text="Quick Categories:", font=('Segoe UI', 9), 
                fg=self.colors['text_secondary'], bg=self.colors['bg_primary']).pack()
        
        cat_buttons_frame = tk.Frame(category_frame, bg=self.colors['bg_primary'])
        cat_buttons_frame.pack()
        
        for i, cat in enumerate(categories):
            if i % 5 == 0:  # New row every 5 buttons
                row_frame = tk.Frame(cat_buttons_frame, bg=self.colors['bg_primary'])
                row_frame.pack()
            
            tk.Button(row_frame, text=cat, command=lambda c=cat: set_category(c),
                     bg=self.colors['bg_card'], fg=self.colors['text_primary'],
                     font=('Segoe UI', 8), padx=5, pady=2, relief='flat').pack(side='left', padx=2)
        
        def save_transaction():
            try:
                date_str = date_var.get()
                category = category_var.get().strip()
                amount_str = amount_var.get()
                description = description_var.get().strip()
                
                # Validate inputs
                if not date_str or not category or not amount_str:
                    messagebox.showerror("Error", "Please fill in all required fields")
                    return
                
                # Parse date
                date = pd.to_datetime(date_str)
                
                # Parse amount
                amount = float(amount_str)
                
                # Create new transaction
                new_transaction = pd.DataFrame({
                    'date': [date],
                    'category': [category],
                    'amount': [amount],
                    'description': [description] if description else [""]
                })
                
                # Add to existing transactions
                if self.transactions_df is not None and not self.transactions_df.empty:
                    self.transactions_df = pd.concat([self.transactions_df, new_transaction], ignore_index=True)
                else:
                    self.transactions_df = new_transaction
                
                # Update cash balance
                self.cash_balance += amount
                
                # Update UI
                self.save_data()
                self.update_dashboard()
                
                dialog.destroy()
                messagebox.showinfo("Success", f"Added transaction: {category} ${amount:,.2f}")
                
            except ValueError as e:
                messagebox.showerror("Error", f"Invalid input: {e}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add transaction: {e}")
        
        # Buttons
        button_frame = tk.Frame(dialog, bg=self.colors['bg_primary'])
        button_frame.pack(pady=20)
        
        tk.Button(button_frame, text="Save", command=save_transaction,
                 bg=self.colors['success'], fg=self.colors['bg_primary'],
                 font=('Segoe UI', 11, 'bold'), padx=20, pady=5, relief='flat').pack(side='left', padx=10)
        
        tk.Button(button_frame, text="Cancel", command=dialog.destroy,
                 bg=self.colors['danger'], fg=self.colors['text_primary'],
                 font=('Segoe UI', 11, 'bold'), padx=20, pady=5, relief='flat').pack(side='left', padx=10)
        
    
    def sell_investment(self):
        """Sell shares from an existing investment"""
        if not self.portfolio:
            messagebox.showwarning("Warning", "No investments to sell")
            return
            
        # Create dialog to select investment
        dialog = tk.Toplevel(self.root)
        dialog.title("Sell Investment")
        dialog.geometry("450x350")
        dialog.configure(bg=self.colors['bg_primary'])
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (450 // 2)
        y = (dialog.winfo_screenheight() // 2) - (350 // 2)
        dialog.geometry(f'450x350+{x}+{y}')
        
        tk.Label(dialog, text="Sell Investment", font=('Segoe UI', 16, 'bold'), 
                fg=self.colors['accent_cyan'], bg=self.colors['bg_primary']).pack(pady=20)
        
        # Investment selection
        selection_frame = tk.Frame(dialog, bg=self.colors['bg_primary'])
        selection_frame.pack(fill='x', padx=20, pady=10)
        
        tk.Label(selection_frame, text="Select Investment:", font=('Segoe UI', 11), 
                fg=self.colors['text_primary'], bg=self.colors['bg_primary']).grid(row=0, column=0, sticky='w', pady=5)
        
        # Combobox for investments
        symbol_var = tk.StringVar()
        symbol_combo = ttk.Combobox(selection_frame, textvariable=symbol_var, 
                                   values=list(self.portfolio.keys()), font=('Segoe UI', 11), width=20)
        symbol_combo.grid(row=0, column=1, pady=5, padx=10)
        
        # Investment details display
        details_frame = tk.Frame(dialog, bg=self.colors['bg_primary'])
        details_frame.pack(fill='x', padx=20, pady=10)
        
        shares_label = tk.Label(details_frame, text="Available Shares: ", font=('Segoe UI', 10), 
                               fg=self.colors['text_primary'], bg=self.colors['bg_primary'])
        shares_label.pack(anchor='w')
        
        value_label = tk.Label(details_frame, text="Current Value: ", font=('Segoe UI', 10), 
                              fg=self.colors['text_primary'], bg=self.colors['bg_primary'])
        value_label.pack(anchor='w')
        
        # Shares to sell
        sell_frame = tk.Frame(dialog, bg=self.colors['bg_primary'])
        sell_frame.pack(fill='x', padx=20, pady=10)
        
        tk.Label(sell_frame, text="Shares to Sell:", font=('Segoe UI', 11), 
                fg=self.colors['text_primary'], bg=self.colors['bg_primary']).grid(row=0, column=0, sticky='w', pady=5)
        
        shares_to_sell_var = tk.StringVar(value="0")
        shares_entry = tk.Entry(sell_frame, textvariable=shares_to_sell_var, font=('Segoe UI', 11),
                bg=self.colors['bg_secondary'], fg=self.colors['text_primary'],
                insertbackground=self.colors['accent_cyan'], width=20)
        shares_entry.grid(row=0, column=1, pady=5, padx=10)
        
        # Status label
        status_label = tk.Label(dialog, text="", font=('Segoe UI', 9), 
                               fg=self.colors['warning'], bg=self.colors['bg_primary'])
        status_label.pack(pady=5)
        
        def update_investment_details(event=None):
            """Update investment details when selection changes"""
            symbol = symbol_var.get()
            if symbol and symbol in self.portfolio:
                data = self.portfolio[symbol]
                shares = data['shares']
                current_price = data.get('current_price', data.get('avg_price', 0))
                value = shares * current_price
                
                shares_label.config(text=f"Available Shares: {shares:,.4f}")
                value_label.config(text=f"Current Value: ${value:,.2f} (${current_price:,.2f}/share)")
        
        # Bind selection event
        symbol_combo.bind('<<ComboboxSelected>>', update_investment_details)
        
        def sell_shares():
            symbol = symbol_var.get()
            try:
                shares_to_sell = float(shares_to_sell_var.get())
                
                if not symbol:
                    messagebox.showerror("Error", "Please select an investment")
                    return
                    
                if symbol not in self.portfolio:
                    messagebox.showerror("Error", "Investment not found")
                    return
                    
                if shares_to_sell <= 0:
                    messagebox.showerror("Error", "Please enter a valid number of shares to sell")
                    return
                
                data = self.portfolio[symbol]
                available_shares = data['shares']
                current_price = data.get('current_price', data.get('avg_price', 0))
                
                if shares_to_sell > available_shares:
                    messagebox.showerror("Error", f"Cannot sell {shares_to_sell} shares. Only {available_shares} available.")
                    return
                
                # Calculate sale proceeds
                proceeds = shares_to_sell * current_price
                
                # Update portfolio
                if shares_to_sell == available_shares:
                    # Remove entire investment
                    del self.portfolio[symbol]
                else:
                    # Reduce share count
                    self.portfolio[symbol]['shares'] = available_shares - shares_to_sell
                
                # Add proceeds to cash balance
                self.cash_balance += proceeds
                
                self.save_data()
                self.update_portfolio_display()
                self.update_dashboard()
                
                dialog.destroy()
                messagebox.showinfo("Success", f"Sold {shares_to_sell} shares of {symbol} for ${proceeds:,.2f}!\nCash balance: ${self.cash_balance:,.2f}")
                
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid number of shares")
        
        # Buttons
        button_frame = tk.Frame(dialog, bg=self.colors['bg_primary'])
        button_frame.pack(pady=20)
        
        tk.Button(button_frame, text="Sell", command=sell_shares,
                 bg=self.colors['success'], fg=self.colors['bg_primary'],
                 font=('Segoe UI', 11, 'bold'), padx=20, pady=5, relief='flat').pack(side='left', padx=10)
        
        tk.Button(button_frame, text="Cancel", command=dialog.destroy,
                 bg=self.colors['danger'], fg=self.colors['text_primary'],
                 font=('Segoe UI', 11, 'bold'), padx=20, pady=5, relief='flat').pack(side='left', padx=10)
    
    def upload_csv(self):
        """Upload and validate CSV file, combining with existing data"""
        file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if not file_path:
            return
            
        try:
            new_transactions_df = pd.read_csv(file_path)
            
            # Validate columns
            required = ['date', 'category', 'amount']
            if not all(col in new_transactions_df.columns for col in required):
                messagebox.showerror("Error", f"CSV must have columns: {', '.join(required)}")
                return
            
            # Convert date
            new_transactions_df['date'] = pd.to_datetime(new_transactions_df['date'])
            
            # Combine with existing data if it exists
            if self.transactions_df is not None and not self.transactions_df.empty:
                # Append new transactions to existing ones
                self.transactions_df = pd.concat([self.transactions_df, new_transactions_df], ignore_index=True)
                action = "added to"
            else:
                # First upload
                self.transactions_df = new_transactions_df
                action = "loaded"
            
            # Update cash balance with new transactions only
            new_cash = new_transactions_df['amount'].sum()
            self.cash_balance += new_cash
            
            # Update CASH in portfolio
            if 'CASH' not in self.portfolio:
                self.portfolio['CASH'] = {'shares': self.cash_balance, 'avg_price': 1.0}
            else:
                self.portfolio['CASH']['shares'] = self.cash_balance
            
            # Mark that these transactions came from a CSV upload
            self.csv_loaded = True
            
            # Update UI with premium styling
            filename = os.path.basename(file_path)
            self.status_label.config(text=f"✅ {action.capitalize()}: {filename} ({len(new_transactions_df)} transactions)",
                                   fg=self.colors['success'])
            self.report_btn.config(state='normal', bg=self.colors['success'])
            self.pie_btn.config(state='normal', bg=self.colors['warning'])
            self.line_btn.config(state='normal', bg=self.colors['success'])
            
            # Save data
            self.save_data()
            
            # Update dashboard
            self.update_dashboard()
            
            messagebox.showinfo("Success", f"✨ {action.capitalize()} {len(new_transactions_df)} transactions successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load CSV: {e}")

    def allocate_funds_to_portfolio(self):
        """Allocate a portion of cash balance to portfolio

        Dialog offers three modes: uninvested CASH, buy a single symbol, or even split
        across existing holdings. It records transactions and updates portfolio/cash.
        """
        if self.cash_balance <= 0:
            messagebox.showwarning("Warning", "No cash available to allocate")
            return

        # Create allocation dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Allocate Funds to Portfolio")
        dialog.geometry("420x340")
        dialog.configure(bg=self.colors['bg_primary'])
        dialog.transient(self.root)
        dialog.grab_set()

        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (420 // 2)
        y = (dialog.winfo_screenheight() // 2) - (340 // 2)
        dialog.geometry(f'420x340+{x}+{y}')

        tk.Label(dialog, text="Allocate Funds to Portfolio", font=('Segoe UI', 16, 'bold'), fg=self.colors['accent_cyan'], bg=self.colors['bg_primary']).pack(pady=12)

        # Display available cash
        tk.Label(dialog, text=f"Available Cash: ${self.cash_balance:,.2f}", font=('Segoe UI', 12), fg=self.colors['text_primary'], bg=self.colors['bg_primary']).pack(pady=6)

        # Input row
        input_frame = tk.Frame(dialog, bg=self.colors['bg_primary'])
        input_frame.pack(pady=8)

        tk.Label(input_frame, text="Amount:", bg=self.colors['bg_primary'], fg=self.colors['text_primary']).grid(row=0, column=0, sticky='w')
        amount_var = tk.StringVar(value="0")
        tk.Entry(input_frame, textvariable=amount_var, bg=self.colors['bg_secondary'], fg=self.colors['text_primary'], width=18).grid(row=0, column=1, padx=8)

        # Percentage helper
        def set_percentage(pct):
            amount = self.cash_balance * (pct / 100.0)
            amount_var.set(f"{amount:.2f}")

        pct_frame = tk.Frame(dialog, bg=self.colors['bg_primary'])
        pct_frame.pack(pady=8)
        for pct in (10, 25, 50, 75, 100):
            tk.Button(pct_frame, text=f"{pct}%", command=lambda p=pct: set_percentage(p), bg=self.colors['accent_purple'], fg=self.colors['text_primary'], relief='flat').pack(side='left', padx=6)

        # Modes
        mode_frame = tk.Frame(dialog, bg=self.colors['bg_primary'])
        mode_frame.pack(pady=6)
        mode_var = tk.StringVar(value='cash')
        tk.Radiobutton(mode_frame, text='Uninvested (CASH)', variable=mode_var, value='cash', bg=self.colors['bg_primary'], fg=self.colors['text_primary'], selectcolor=self.colors['bg_card']).pack(side='left', padx=6)
        tk.Radiobutton(mode_frame, text='Buy Single Symbol', variable=mode_var, value='single', bg=self.colors['bg_primary'], fg=self.colors['text_primary'], selectcolor=self.colors['bg_card']).pack(side='left', padx=6)
        tk.Radiobutton(mode_frame, text='Even Split', variable=mode_var, value='split', bg=self.colors['bg_primary'], fg=self.colors['text_primary'], selectcolor=self.colors['bg_card']).pack(side='left', padx=6)

        # Symbol input for single buy
        symbol_frame = tk.Frame(dialog, bg=self.colors['bg_primary'])
        symbol_frame.pack(pady=6)
        tk.Label(symbol_frame, text='Symbol (for single buy):', bg=self.colors['bg_primary'], fg=self.colors['text_primary']).pack(side='left', padx=6)
        symbol_var = tk.StringVar()
        tk.Entry(symbol_frame, textvariable=symbol_var, bg=self.colors['bg_secondary'], fg=self.colors['text_primary'], width=12).pack(side='left')

        def allocate_action():
            try:
                amt = float(amount_var.get())
            except Exception:
                messagebox.showerror('Error', 'Enter a valid number')
                return

            if amt <= 0:
                messagebox.showerror('Error', 'Please enter an amount greater than zero')
                return
            if amt > self.cash_balance:
                messagebox.showerror('Error', 'Amount exceeds available cash')
                return

            mode = mode_var.get()
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Record the allocation cash-out
            self.add_transaction_record(now, 'Allocate: Portfolio', -amt, f'Allocated ${amt:,.2f} ({mode})')

            if mode == 'cash':
                # Add/Update CASH holding (shares = dollars)
                if 'CASH' in self.portfolio:
                    self.portfolio['CASH']['shares'] = self.portfolio['CASH'].get('shares', 0) + amt
                    self.portfolio['CASH']['current_price'] = 1.0
                else:
                    self.portfolio['CASH'] = {'shares': amt, 'avg_price': 1.0, 'current_price': 1.0}

            elif mode == 'single':
                sym = symbol_var.get().upper().strip()
                if not sym:
                    messagebox.showerror('Error', 'Please enter a symbol for single buy')
                    return
                price, err = self.get_current_stock_price(sym)
                if price is None:
                    messagebox.showerror('Error', f'Could not fetch price for {sym}: {err}')
                    return
                shares = amt / price if price > 0 else 0
                if sym in self.portfolio:
                    ex = self.portfolio[sym]
                    tot_sh = ex['shares'] + shares
                    tot_cost = ex['shares'] * ex.get('avg_price', ex.get('current_price', price)) + shares * price
                    new_avg = tot_cost / tot_sh if tot_sh > 0 else price
                    self.portfolio[sym] = {'shares': tot_sh, 'avg_price': new_avg, 'current_price': price}
                else:
                    self.portfolio[sym] = {'shares': shares, 'avg_price': price, 'current_price': price}
                self.add_transaction_record(now, f'Investment: {sym}', -amt, f'Bought {shares:.6f} @ ${price:.2f}')

            else:  # split
                targets = [s for s in self.portfolio.keys() if s != 'CASH']
                if not targets:
                    # fallback to CASH
                    if 'CASH' in self.portfolio:
                        self.portfolio['CASH']['shares'] += amt
                    else:
                        self.portfolio['CASH'] = {'shares': amt, 'avg_price': 1.0, 'current_price': 1.0}
                else:
                    per = amt / len(targets)
                    for s in targets:
                        price, err = self.get_current_stock_price(s)
                        if price is None:
                            price = self.portfolio[s].get('current_price', self.portfolio[s].get('avg_price', 0))
                        shares = per / price if price > 0 else 0
                        ex = self.portfolio[s]
                        tot_sh = ex['shares'] + shares
                        tot_cost = ex['shares'] * ex.get('avg_price', ex.get('current_price', price)) + shares * price
                        new_avg = tot_cost / tot_sh if tot_sh > 0 else price
                        self.portfolio[s] = {'shares': tot_sh, 'avg_price': new_avg, 'current_price': price}
                        self.add_transaction_record(now, f'Investment: {s}', -per, f'Allocated ${per:,.2f} to {s} (approx {shares:.6f} shares)')

            # Save and update UI
            self.save_data()
            self.update_portfolio_display()
            self.update_dashboard()
            dialog.destroy()
            messagebox.showinfo('Success', f'Allocated ${amt:,.2f} to portfolio ({mode})')

        # Buttons
        btn_frame = tk.Frame(dialog, bg=self.colors['bg_primary'])
        btn_frame.pack(pady=12)
        tk.Button(btn_frame, text='Save', command=allocate_action, bg=self.colors['success'], fg=self.colors['bg_primary'], font=('Segoe UI', 11, 'bold')).pack(side='left', padx=8)
        tk.Button(btn_frame, text='Cancel', command=dialog.destroy, bg=self.colors['danger'], fg=self.colors['text_primary'], font=('Segoe UI', 11, 'bold')).pack(side='left', padx=8)

    def remove_investment(self):
        """Remove an investment from the portfolio"""
        if not self.portfolio:
            messagebox.showwarning("Warning", "No investments to remove")
            return
            
        # Create dialog to select investment
        dialog = tk.Toplevel(self.root)
        dialog.title("Remove Investment")
        dialog.geometry("400x300")
        dialog.configure(bg=self.colors['bg_primary'])
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (dialog.winfo_screenheight() // 2) - (300 // 2)
        dialog.geometry(f'400x300+{x}+{y}')
        
        tk.Label(dialog, text="Remove Investment", font=('Segoe UI', 16, 'bold'), 
                fg=self.colors['accent_cyan'], bg=self.colors['bg_primary']).pack(pady=20)
        
        # Investment selection
        selection_frame = tk.Frame(dialog, bg=self.colors['bg_primary'])
        selection_frame.pack(fill='x', padx=20, pady=10)
        
        tk.Label(selection_frame, text="Select Investment:", font=('Segoe UI', 11), 
                fg=self.colors['text_primary'], bg=self.colors['bg_primary']).grid(row=0, column=0, sticky='w', pady=5)

        # Combobox for investments
        symbol_var = tk.StringVar()
        symbol_combo = ttk.Combobox(selection_frame, textvariable=symbol_var, 
                                   values=list(self.portfolio.keys()), font=('Segoe UI', 11), width=20)
        symbol_combo.grid(row=0, column=1, pady=5, padx=10)
        
        # Investment details display
        details_frame = tk.Frame(dialog, bg=self.colors['bg_primary'])
        details_frame.pack(fill='x', padx=20, pady=10)
        
        shares_label = tk.Label(details_frame, text="Available Shares: ", font=('Segoe UI', 10), 
                               fg=self.colors['text_primary'], bg=self.colors['bg_primary'])
        shares_label.pack(anchor='w')
        
        # Value label
        value_label = tk.Label(details_frame, text="Current Value: ", font=('Segoe UI', 10),
                             fg=self.colors['text_primary'], bg=self.colors['bg_primary'])
        value_label.pack(anchor='w')

    def allocate_funds_to_portfolio(self):
        """Allocate a portion of cash balance to portfolio

        Dialog offers three modes: uninvested CASH, buy a single symbol, or even split
        across existing holdings. It records transactions and updates portfolio/cash.
        """
        if self.cash_balance <= 0:
            messagebox.showwarning("Warning", "No cash available to allocate")
            return

        # Create allocation dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Allocate Funds to Portfolio")
        dialog.geometry("420x340")
        dialog.configure(bg=self.colors['bg_primary'])
        dialog.transient(self.root)
        dialog.grab_set()

        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (420 // 2)
        y = (dialog.winfo_screenheight() // 2) - (340 // 2)
        dialog.geometry(f'420x340+{x}+{y}')

        tk.Label(dialog, text="Allocate Funds to Portfolio", font=('Segoe UI', 16, 'bold'), fg=self.colors['accent_cyan'], bg=self.colors['bg_primary']).pack(pady=12)

        # Display available cash
        tk.Label(dialog, text=f"Available Cash: ${self.cash_balance:,.2f}", font=('Segoe UI', 12), fg=self.colors['text_primary'], bg=self.colors['bg_primary']).pack(pady=6)

        # Input row
        input_frame = tk.Frame(dialog, bg=self.colors['bg_primary'])
        input_frame.pack(pady=8)

        tk.Label(input_frame, text="Amount:", bg=self.colors['bg_primary'], fg=self.colors['text_primary']).grid(row=0, column=0, sticky='w')
        amount_var = tk.StringVar(value="0")
        tk.Entry(input_frame, textvariable=amount_var, bg=self.colors['bg_secondary'], fg=self.colors['text_primary'], width=18).grid(row=0, column=1, padx=8)

        # Percentage helper
        def set_percentage(pct):
            amount = self.cash_balance * (pct / 100.0)
            amount_var.set(f"{amount:.2f}")

        pct_frame = tk.Frame(dialog, bg=self.colors['bg_primary'])
        pct_frame.pack(pady=8)
        for pct in (10, 25, 50, 75, 100):
            tk.Button(pct_frame, text=f"{pct}%", command=lambda p=pct: set_percentage(p), bg=self.colors['accent_purple'], fg=self.colors['text_primary'], relief='flat').pack(side='left', padx=6)

        # Modes
        mode_frame = tk.Frame(dialog, bg=self.colors['bg_primary'])
        mode_frame.pack(pady=6)
        mode_var = tk.StringVar(value='cash')
        tk.Radiobutton(mode_frame, text='Uninvested (CASH)', variable=mode_var, value='cash', bg=self.colors['bg_primary'], fg=self.colors['text_primary'], selectcolor=self.colors['bg_card']).pack(side='left', padx=6)
        tk.Radiobutton(mode_frame, text='Buy Single Symbol', variable=mode_var, value='single', bg=self.colors['bg_primary'], fg=self.colors['text_primary'], selectcolor=self.colors['bg_card']).pack(side='left', padx=6)
        tk.Radiobutton(mode_frame, text='Even Split', variable=mode_var, value='split', bg=self.colors['bg_primary'], fg=self.colors['text_primary'], selectcolor=self.colors['bg_card']).pack(side='left', padx=6)

        # Symbol input for single buy
        symbol_frame = tk.Frame(dialog, bg=self.colors['bg_primary'])
        symbol_frame.pack(pady=6)
        tk.Label(symbol_frame, text='Symbol (for single buy):', bg=self.colors['bg_primary'], fg=self.colors['text_primary']).pack(side='left', padx=6)
        symbol_var = tk.StringVar()
        tk.Entry(symbol_frame, textvariable=symbol_var, bg=self.colors['bg_secondary'], fg=self.colors['text_primary'], width=12).pack(side='left')

        def allocate_action():
            try:
                amt = float(amount_var.get())
            except Exception:
                messagebox.showerror('Error', 'Enter a valid number')
                return

            if amt <= 0:
                messagebox.showerror('Error', 'Please enter an amount greater than zero')
                return
            if amt > self.cash_balance:
                messagebox.showerror('Error', 'Amount exceeds available cash')
                return

            mode = mode_var.get()
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Record the allocation cash-out
            self.add_transaction_record(now, 'Allocate: Portfolio', -amt, f'Allocated ${amt:,.2f} ({mode})')

            if mode == 'cash':
                # Add/Update CASH holding (shares = dollars)
                if 'CASH' in self.portfolio:
                    self.portfolio['CASH']['shares'] = self.portfolio['CASH'].get('shares', 0) + amt
                    self.portfolio['CASH']['current_price'] = 1.0
                else:
                    self.portfolio['CASH'] = {'shares': amt, 'avg_price': 1.0, 'current_price': 1.0}

            elif mode == 'single':
                sym = symbol_var.get().upper().strip()
                if not sym:
                    messagebox.showerror('Error', 'Please enter a symbol for single buy')
                    return
                price, err = self.get_current_stock_price(sym)
                if price is None:
                    messagebox.showerror('Error', f'Could not fetch price for {sym}: {err}')
                    return
                shares = amt / price if price > 0 else 0
                if sym in self.portfolio:
                    ex = self.portfolio[sym]
                    tot_sh = ex['shares'] + shares
                    tot_cost = ex['shares'] * ex.get('avg_price', ex.get('current_price', price)) + shares * price
                    new_avg = tot_cost / tot_sh if tot_sh > 0 else price
                    self.portfolio[sym] = {'shares': tot_sh, 'avg_price': new_avg, 'current_price': price}
                else:
                    self.portfolio[sym] = {'shares': shares, 'avg_price': price, 'current_price': price}
                self.add_transaction_record(now, f'Investment: {sym}', -amt, f'Bought {shares:.6f} @ ${price:.2f}')

            else:  # split
                targets = [s for s in self.portfolio.keys() if s != 'CASH']
                if not targets:
                    # fallback to CASH
                    if 'CASH' in self.portfolio:
                        self.portfolio['CASH']['shares'] += amt
                    else:
                        self.portfolio['CASH'] = {'shares': amt, 'avg_price': 1.0, 'current_price': 1.0}
                else:
                    per = amt / len(targets)
                    for s in targets:
                        price, err = self.get_current_stock_price(s)
                        if price is None:
                            price = self.portfolio[s].get('current_price', self.portfolio[s].get('avg_price', 0))
                        shares = per / price if price > 0 else 0
                        ex = self.portfolio[s]
                        tot_sh = ex['shares'] + shares
                        tot_cost = ex['shares'] * ex.get('avg_price', ex.get('current_price', price)) + shares * price
                        new_avg = tot_cost / tot_sh if tot_sh > 0 else price
                        self.portfolio[s] = {'shares': tot_sh, 'avg_price': new_avg, 'current_price': price}
                        self.add_transaction_record(now, f'Investment: {s}', -per, f'Allocated ${per:,.2f} to {s} (approx {shares:.6f} shares)')

            # Save and update UI
            self.save_data()
            self.update_portfolio_display()
            self.update_dashboard()
            dialog.destroy()
            messagebox.showinfo('Success', f'Allocated ${amt:,.2f} to portfolio ({mode})')

        # Buttons
        btn_frame = tk.Frame(dialog, bg=self.colors['bg_primary'])
        btn_frame.pack(pady=12)
        tk.Button(btn_frame, text='Save', command=allocate_action, bg=self.colors['success'], fg=self.colors['bg_primary'], font=('Segoe UI', 11, 'bold')).pack(side='left', padx=8)
        tk.Button(btn_frame, text='Cancel', command=dialog.destroy, bg=self.colors['danger'], fg=self.colors['text_primary'], font=('Segoe UI', 11, 'bold')).pack(side='left', padx=8)

    def remove_investment(self):
        """Remove an investment from the portfolio"""
        if not self.portfolio:
            messagebox.showwarning("Warning", "No investments to remove")
            return
            
        # Create dialog to select investment
        dialog = tk.Toplevel(self.root)
        dialog.title("Remove Investment")
        dialog.geometry("400x300")
        dialog.configure(bg=self.colors['bg_primary'])
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (dialog.winfo_screenheight() // 2) - (300 // 2)
        dialog.geometry(f'400x300+{x}+{y}')
        
        tk.Label(dialog, text="Select Investment to Remove", font=('Segoe UI', 16, 'bold'), 
                fg=self.colors['accent_cyan'], bg=self.colors['bg_primary']).pack(pady=20)
        
        # Listbox for investments
        list_frame = tk.Frame(dialog, bg=self.colors['bg_primary'])
        list_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        scrollbar = tk.Scrollbar(list_frame)
        investment_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, 
                                 bg=self.colors['bg_secondary'], fg=self.colors['text_primary'],
                                 selectbackground=self.colors['accent_purple'])
        scrollbar.config(command=investment_listbox.yview)
        scrollbar.pack(side='right', fill='y')
        investment_listbox.pack(side='left', fill='both', expand=True)
        
        # Populate listbox
        for symbol, data in self.portfolio.items():
            shares = data['shares']
            current_price = data.get('current_price', data.get('avg_price', 0))
            value = shares * current_price
            investment_listbox.insert(tk.END, f"{symbol}: {shares} shares (${value:,.2f})")
        
        def on_select():
            selection = investment_listbox.curselection()
            if selection:
                # Get the symbol from the selected item
                selected_text = investment_listbox.get(selection[0])
                symbol = selected_text.split(':')[0]
                
                # Confirm removal
                if messagebox.askyesno("Confirm Removal", f"Are you sure you want to remove {symbol} from your portfolio?"):
                    if symbol in self.portfolio:
                        data = self.portfolio.pop(symbol)
                        shares = data.get('shares', 0)
                        current_price = data.get('current_price', data.get('avg_price', 0))
                        credit_amount = shares * current_price

                        # Credit cash balance
                        self.cash_balance += credit_amount

                        # Record transaction returning funds to cash
                        transaction_date = datetime.now().strftime('%Y-%m-%d')
                        self.add_transaction_record(transaction_date, f"Liquidation: {symbol}", credit_amount, f"Removed {shares} shares at ${current_price:,.2f}")

                        # Save and refresh UI
                        self.save_data()
                        self.update_portfolio_display()
                        self.update_dashboard()
                        dialog.destroy()
                        messagebox.showinfo("Success", f"Removed {symbol} from portfolio!\nCredited: ${credit_amount:,.2f}\nNew cash balance: ${self.cash_balance:,.2f}")
            else:
                messagebox.showwarning("Warning", "Please select an investment")
        
        # Buttons
        button_frame = tk.Frame(dialog, bg=self.colors['bg_primary'])
        button_frame.pack(pady=20)
        
        tk.Button(button_frame, text="Remove", command=on_select,
                 bg=self.colors['danger'], fg=self.colors['text_primary'],
                 font=('Segoe UI', 11, 'bold'), padx=20, pady=5, relief='flat').pack(side='left', padx=10)
        
        tk.Button(button_frame, text="Cancel", command=dialog.destroy,
                 bg=self.colors['accent_purple'], fg=self.colors['text_primary'],
                 font=('Segoe UI', 11, 'bold'), padx=20, pady=5, relief='flat').pack(side='left', padx=10)

    def add_financial_goal(self):
        """Add a new financial goal"""
        self._create_goal_dialog("Add Financial Goal", None)

    def delete_financial_goal(self):
        """Delete a financial goal and return its funds to cash balance"""
        # Initialize financial_goals if it doesn't exist
        if not hasattr(self, 'financial_goals') or self.financial_goals is None:
            self.financial_goals = []
            
        if not self.financial_goals:
            messagebox.showwarning("Warning", "No goals to delete")
            return
            
        # Get the selected goal from the main listbox
        selected = self.goals_listbox.curselection()
        
        if not selected:
            messagebox.showinfo("Selection Required", "Please select a goal from the list to delete.")
            return
            
        # Calculate the actual goal index, accounting for header lines
        header_lines = 5 if not self.financial_goals else 5
        
        # Check if the selection is in the header area
        if selected[0] < header_lines:
            messagebox.showinfo("Invalid Selection", "Please select a goal from the list, not the header.")
            return
            
        # Calculate the actual goal index
        goal_index = selected[0] - header_lines
        
        # Verify the index is valid
        if goal_index < 0 or goal_index >= len(self.financial_goals):
            messagebox.showinfo("Invalid Selection", "Please select a valid goal from the list.")
            return
            
        # Get the selected goal
        goal = self.financial_goals[goal_index]
        
        # Confirm deletion
        confirm = messagebox.askyesno("Confirm Deletion", 
                                     f"Are you sure you want to delete the goal '{goal['name']}'?\n\n"
                                     f"${goal['current']:.2f} will be returned to your cash balance.")
        if not confirm:
            return
            
        # Return funds to cash balance
        self.cash_balance += goal['current']
        
        # Remove goal
        del self.financial_goals[goal_index]
        
        # Save data
        self.save_data()
        
        # Update displays
        self.update_goals_display()
        self.update_cash_display()
        self.update_dashboard()
        
        messagebox.showinfo("Goal Deleted", f"Goal '{goal['name']}' has been deleted and ${goal['current']:.2f} has been returned to your cash balance.")
    
    def update_financial_goal(self):
        """Update an existing financial goal"""
        # Get the selected goal from the main listbox
        selected = self.goals_listbox.curselection()
        
        if not selected:
            messagebox.showinfo("Selection Required", "Please select a goal from the list to update.")
            return
            
        # Calculate the actual goal index, accounting for header lines
        header_lines = 5 if not self.financial_goals else 5
        
        # Check if the selection is in the header area
        if selected[0] < header_lines:
            messagebox.showinfo("Invalid Selection", "Please select a goal from the list, not the header.")
            return
            
        # Calculate the actual goal index
        goal_index = selected[0] - header_lines
        
        # Verify the index is valid
        if goal_index < 0 or goal_index >= len(self.financial_goals):
            messagebox.showinfo("Invalid Selection", "Please select a valid goal from the list.")
            return
            
        # Get the selected goal
        goal = self.financial_goals[goal_index]
        
        # Open the goal dialog with the selected goal
        self._create_goal_dialog("Update Financial Goal", goal)
    
    def allocate_funds_to_goal(self):
        """Allocate funds from cash balance to a goal"""
        if not self.financial_goals:
            messagebox.showwarning("Warning", "No goals to allocate funds to")
            return
            
        if self.cash_balance <= 0:
            messagebox.showwarning("Warning", "No cash available to allocate")
            return
            
        # Create dialog to select goal
        dialog = tk.Toplevel(self.root)
        dialog.title("Allocate Funds to Goal")
        dialog.geometry("400x400")
        dialog.configure(bg=self.colors['bg_primary'])
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (dialog.winfo_screenheight() // 2) - (400 // 2)
        dialog.geometry(f'400x400+{x}+{y}')
        
        tk.Label(dialog, text="Allocate Funds to Goal", font=('Segoe UI', 16, 'bold'), 
                fg=self.colors['warning'], bg=self.colors['bg_primary']).pack(pady=20)
        
        # Cash balance display
        tk.Label(dialog, text=f"Available Cash: ${self.cash_balance:.2f}", font=('Segoe UI', 12), 
                fg=self.colors['success'], bg=self.colors['bg_primary']).pack(pady=5)
        
        # Listbox for goals
        list_frame = tk.Frame(dialog, bg=self.colors['bg_primary'])
        list_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        scrollbar = tk.Scrollbar(list_frame)
        goal_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, 
                                 bg=self.colors['bg_secondary'], fg=self.colors['text_primary'],
                                 selectbackground=self.colors['warning'])
        scrollbar.config(command=goal_listbox.yview)
        
        goal_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Populate listbox
        for i, goal in enumerate(self.financial_goals):
            remaining = goal['target'] - goal['current']
            goal_listbox.insert(tk.END, f"{goal['name']} (${goal['current']:.2f} / ${goal['target']:.2f}, ${remaining:.2f} needed)")
        
        # Amount entry
        amount_frame = tk.Frame(dialog, bg=self.colors['bg_primary'])
        amount_frame.pack(pady=10)
        
        tk.Label(amount_frame, text="Amount to Allocate: $", font=('Segoe UI', 12), 
                fg=self.colors['text_primary'], bg=self.colors['bg_primary']).pack(side='left')
        
        amount_var = tk.StringVar(value="0.00")
        amount_entry = tk.Entry(amount_frame, textvariable=amount_var, width=10, 
                               font=('Segoe UI', 12), bg=self.colors['bg_secondary'],
                               fg=self.colors['text_primary'], insertbackground=self.colors['accent_cyan'])
        amount_entry.pack(side='left', padx=5)
        
        # Buttons
        btn_frame = tk.Frame(dialog, bg=self.colors['bg_primary'])
        btn_frame.pack(pady=20)
        
        def on_allocate():
            selected = goal_listbox.curselection()
            if not selected:
                messagebox.showwarning("Warning", "Please select a goal")
                return
                
            try:
                amount = float(amount_var.get())
                if amount <= 0:
                    messagebox.showwarning("Warning", "Please enter a positive amount")
                    return
                    
                if amount > self.cash_balance:
                    messagebox.showwarning("Warning", "Amount exceeds available cash")
                    return
                    
                idx = selected[0]
                goal = self.financial_goals[idx]
                
                # Transfer funds
                self.cash_balance -= amount
                self.financial_goals[idx]['current'] += amount
                
                # Save data
                self.save_data()
                
                # Update displays
                self.update_goals_display()
                self.update_dashboard()
                
                messagebox.showinfo("Success", f"${amount:.2f} allocated to '{goal['name']}'")
                dialog.destroy()
                
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid number")
        
        tk.Button(btn_frame, text="💰 ALLOCATE FUNDS", command=on_allocate,
                 bg=self.colors['warning'], fg=self.colors['bg_primary'],
                 font=('Segoe UI', 11, 'bold'), padx=15, pady=8, relief='flat').pack(side='left', padx=10)
        
        tk.Button(btn_frame, text="CANCEL", command=dialog.destroy,
                 bg=self.colors['bg_secondary'], fg=self.colors['text_primary'],
                 font=('Segoe UI', 11), padx=15, pady=8, relief='flat').pack(side='left', padx=10)
    
    def update_financial_goal(self):
        """Update an existing financial goal"""
        if not self.financial_goals:
            messagebox.showwarning("Warning", "No goals to update")
            return
            
        # Create dialog to select goal
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Goal to Update")
        dialog.geometry("400x300")
        dialog.configure(bg=self.colors['bg_primary'])
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (dialog.winfo_screenheight() // 2) - (300 // 2)
        dialog.geometry(f'400x300+{x}+{y}')
        
        tk.Label(dialog, text="Select Goal to Update", font=('Segoe UI', 16, 'bold'), 
                fg=self.colors['accent_purple'], bg=self.colors['bg_primary']).pack(pady=20)
        
        # Listbox for goals
        list_frame = tk.Frame(dialog, bg=self.colors['bg_primary'])
        list_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        scrollbar = tk.Scrollbar(list_frame)
        goal_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, 
                                 bg=self.colors['bg_secondary'], fg=self.colors['text_primary'],
                                 selectbackground=self.colors['accent_purple'])
        scrollbar.config(command=goal_listbox.yview)
        scrollbar.pack(side='right', fill='y')
        goal_listbox.pack(side='left', fill='both', expand=True)
        
        # Populate listbox
        for i, goal in enumerate(self.financial_goals):
            goal_listbox.insert(tk.END, f"{goal['name']} (${goal['current']:,.0f}/${goal['target']:,.0f})")
        
        def on_select():
            selection = goal_listbox.curselection()
            if selection:
                index = selection[0]
                dialog.destroy()
                self._create_goal_dialog("Update Financial Goal", index)
            else:
                messagebox.showwarning("Warning", "Please select a goal")
        
        # Buttons
        button_frame = tk.Frame(dialog, bg=self.colors['bg_primary'])
        button_frame.pack(pady=20)
        
        tk.Button(button_frame, text="Update", command=on_select,
                 bg=self.colors['success'], fg=self.colors['bg_primary'],
                 font=('Segoe UI', 11, 'bold'), padx=20, pady=5, relief='flat').pack(side='left', padx=10)
        
        tk.Button(button_frame, text="Cancel", command=dialog.destroy,
                 bg=self.colors['danger'], fg=self.colors['text_primary'],
                 font=('Segoe UI', 11, 'bold'), padx=20, pady=5, relief='flat').pack(side='left', padx=10)

    def _create_goal_dialog(self, title, goal_index):
        """Create dialog for adding or updating a goal"""
        # Create goal dialog
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.geometry("400x350")
        dialog.configure(bg=self.colors['bg_primary'])
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (dialog.winfo_screenheight() // 2) - (350 // 2)
        dialog.geometry(f'400x350+{x}+{y}')
        
        tk.Label(dialog, text=title, font=('Segoe UI', 16, 'bold'), 
                fg=self.colors['accent_purple'], bg=self.colors['bg_primary']).pack(pady=20)
        
        # Input fields
        input_frame = tk.Frame(dialog, bg=self.colors['bg_primary'])
        input_frame.pack(pady=10)
        
        # Goal Name
        tk.Label(input_frame, text="Goal Name:", font=('Segoe UI', 11), 
                fg=self.colors['text_primary'], bg=self.colors['bg_primary']).grid(row=0, column=0, sticky='w', pady=5)
        name_var = tk.StringVar()
        name_entry = tk.Entry(input_frame, textvariable=name_var, font=('Segoe UI', 11),
                bg=self.colors['bg_secondary'], fg=self.colors['text_primary'],
                insertbackground=self.colors['accent_cyan'], width=20)
        name_entry.grid(row=0, column=1, pady=5, padx=10)
        
        # Target Amount
        tk.Label(input_frame, text="Target ($):", font=('Segoe UI', 11), 
                fg=self.colors['text_primary'], bg=self.colors['bg_primary']).grid(row=1, column=0, sticky='w', pady=5)
        target_var = tk.StringVar()
        target_entry = tk.Entry(input_frame, textvariable=target_var, font=('Segoe UI', 11),
                bg=self.colors['bg_secondary'], fg=self.colors['text_primary'],
                insertbackground=self.colors['accent_cyan'], width=20)
        target_entry.grid(row=1, column=1, pady=5, padx=10)
        
        # Current Amount
        tk.Label(input_frame, text="Current ($):", font=('Segoe UI', 11), 
                fg=self.colors['text_primary'], bg=self.colors['bg_primary']).grid(row=2, column=0, sticky='w', pady=5)
        current_var = tk.StringVar(value="0")
        current_entry = tk.Entry(input_frame, textvariable=current_var, font=('Segoe UI', 11),
                bg=self.colors['bg_secondary'], fg=self.colors['text_primary'],
                insertbackground=self.colors['accent_cyan'], width=20)
        current_entry.grid(row=2, column=1, pady=5, padx=10)

        # Meaning / Type (optional)
        tk.Label(input_frame, text="Type/Meaning:", font=('Segoe UI', 11), 
            fg=self.colors['text_primary'], bg=self.colors['bg_primary']).grid(row=3, column=0, sticky='w', pady=5)
        meaning_var = tk.StringVar(value="Savings")
        meaning_combo = ttk.Combobox(input_frame, values=['Savings', 'Emergency', 'Debt', 'Investment', 'Other'], textvariable=meaning_var, width=17)
        meaning_combo.grid(row=3, column=1, pady=5, padx=10)
        
        # Pre-populate fields if updating
        if goal_index is not None:
            goal = self.financial_goals[goal_index]
            name_var.set(goal['name'])

            target_var.set(str(goal['target']))
            current_var.set(str(goal['current']))
            # Populate meaning if exists
            if 'meaning' in goal:
                meaning_var.set(goal.get('meaning', meaning_var.get()))
        
        def save_goal():
            name = name_var.get().strip()
            try:
                target = float(target_var.get())
                current = float(current_var.get())
                
                if name and target > 0:
                    goal = {
                        'name': name,
                        'target': target,
                        'current': current,
                        'meaning': meaning_var.get().strip() if meaning_var.get() else 'Other'
                    }
                    
                    if goal_index is not None:
                        # Update existing goal
                        self.financial_goals[goal_index] = goal
                        action = "updated"
                    else:
                        # Add new goal
                        self.financial_goals.append(goal)
                        action = "added"
                        
                    self.save_data()
                    self.update_goals_display()
                    dialog.destroy()
                    messagebox.showinfo("Success", f"Goal {action}: {name}")
                else:
                    messagebox.showerror("Error", "Please enter valid data")
            except ValueError:
                messagebox.showerror("Error", "Please enter valid numbers for amounts")
        
        # Buttons
        button_frame = tk.Frame(dialog, bg=self.colors['bg_primary'])
        button_frame.pack(pady=20)
        
        tk.Button(button_frame, text="Save", command=save_goal,
                 bg=self.colors['success'], fg=self.colors['bg_primary'],
                 font=('Segoe UI', 11, 'bold'), padx=20, pady=5, relief='flat').pack(side='left', padx=10)
        
        tk.Button(button_frame, text="Cancel", command=dialog.destroy,
                 bg=self.colors['danger'], fg=self.colors['text_primary'],
                 font=('Segoe UI', 11, 'bold'), padx=20, pady=5, relief='flat').pack(side='left', padx=10)

    def validate_stock_symbol(self, symbol):
        """Validate stock symbol and return company name if valid"""
        if not YFINANCE_AVAILABLE:
            return None, "yfinance not available"
            
        try:
            stock = yf.Ticker(symbol)
            info = stock.info
            company_name = info.get('longName', 'Unknown Company')
            return company_name, None
        except Exception as e:
            return None, str(e)

    def get_current_stock_price(self, symbol):
        """Get current stock price for a symbol"""
        if not YFINANCE_AVAILABLE:
            return None, "yfinance not available"
            
        try:
            stock = yf.Ticker(symbol)
            hist = stock.history(period="1d")
            
            if not hist.empty:
                current_price = hist['Close'].iloc[-1]
                return current_price, None
            else:
                return None, "No price data available"
        except Exception as e:
            return None, str(e)

    def update_portfolio_prices(self):
        """Update portfolio with current market prices, excluding CASH"""
        if not YFINANCE_AVAILABLE:
            messagebox.showerror("Error", "yfinance not available. Install with: pip install yfinance")
            return
            
        # Filter out non-CASH investments
        stock_portfolio = {symbol: data for symbol, data in self.portfolio.items() if symbol != "CASH"}
        
        if not stock_portfolio:
            messagebox.showwarning("Warning", "No stock investments in portfolio")
            return
            
        def update_prices():
            try:
                updated_count = 0
                failed_symbols = []
                
                for symbol in list(self.portfolio.keys()):  # Use list to avoid modification during iteration
                    if symbol == "CASH":
                        # Ensure CASH price is always 1.0
                        self.portfolio[symbol]['current_price'] = 1.0
                        self.portfolio[symbol]['avg_price'] = 1.0
                        continue
                        
                    try:
                        stock = yf.Ticker(symbol)
                        hist = stock.history(period="1d")
                        
                        if not hist.empty:
                            current_price = hist['Close'].iloc[-1]
                            self.portfolio[symbol]['current_price'] = current_price
                            updated_count += 1
                        else:
                            failed_symbols.append(f"{symbol}: No data (possibly delisted)")
                    except Exception as e:
                        failed_symbols.append(f"{symbol}: {str(e)}")
                
                # Ensure we always have CASH in portfolio with correct price
                if 'CASH' not in self.portfolio:
                    self.portfolio['CASH'] = {'shares': self.cash_balance, 'avg_price': 1.0, 'current_price': 1.0}
                
                self.root.after(0, lambda: self.update_portfolio_display())
                
                # Show detailed results
                message = f"Updated prices for {updated_count} investments"
                if failed_symbols:
                    message += f"\n\nFailed to update {len(failed_symbols)} symbols:\n" + "\n".join(failed_symbols)
                
                self.root.after(0, lambda: messagebox.showinfo("Update Prices", message))
                self.save_data()
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to update prices: {e}"))
        
        # Show processing message
        messagebox.showinfo("Update Prices", "Updating prices, please wait...")
        threading.Thread(target=update_prices, daemon=True).start()
        
    def update_portfolio_display(self):
        """Update portfolio display with current data"""
        try:
            # Update holdings display
            self.holdings_text.config(state='normal')
            self.summary_text.config(state='normal')
            
            self.holdings_text.delete('1.0', tk.END)
            self.summary_text.delete('1.0', tk.END)
            
            if not self.portfolio or (len(self.portfolio) == 1 and 'CASH' in self.portfolio and self.portfolio['CASH']['shares'] == 0):
                self.holdings_text.insert('1.0', "No investments yet. Click 'Add Investment' to get started!\n\n"
                                    "Example investments you can track:\n"
                                    "• Stocks (AAPL, GOOGL, MSFT, etc.)\n"
                                    "• ETFs (SPY, VTI, VEA, etc.)\n"
                                    "• Mutual Funds\n"
                                    "• Crypto (BTC, ETH, etc.)\n")
                
                self.summary_text.insert('1.0', "Portfolio Summary\n"
                                    "================\n\n"
                                    "Total Value: $0.00\n"
                                    "Total Invested: $0.00\n"
                                    "Gain/Loss: $0.00 (0.00%)\n\n"
                                    "Add investments to see your portfolio summary!")
                
                self.holdings_text.config(state='disabled')
                self.summary_text.config(state='disabled')
                return
            
            # Display holdings with more details
            holdings_text = "PORTFOLIO HOLDINGS\n"
            holdings_text += "================\n\n"
            
            total_value = 0
            total_invested = 0
            
            # Process each investment
            for symbol, data in self.portfolio.items():
                shares = data.get('shares', 0)
                avg_price = data.get('avg_price', 0)
                current_price = data.get('current_price', avg_price)
                
                # Special handling for CASH
                if symbol == 'CASH':
                    holdings_text += f"💵 CASH Balance: ${shares:,.2f}\n\n"
                    total_value += shares
                    total_invested += shares
                    continue
                
                # Calculate position values
                position_value = shares * current_price
                invested_value = shares * avg_price
                gain_loss = position_value - invested_value
                gain_loss_pct = (gain_loss / invested_value * 100) if invested_value > 0 else 0
                
                total_value += position_value
                total_invested += invested_value
                
                # Format display with color coding
                gain_color = self.colors['success'] if gain_loss >= 0 else self.colors['danger']
                holdings_text += f"{symbol}: {shares:,.4f} shares\n"
                holdings_text += f"  Avg Price: ${avg_price:,.2f}\n"
                holdings_text += f"  Current: ${current_price:,.2f}\n"
                holdings_text += f"  Value: ${position_value:,.2f}\n"
                holdings_text += f"  Gain/Loss: {gain_color}${gain_loss:,.2f} ({gain_loss_pct:+.2f}%){self.colors['text_primary']}\n\n"
            
            # Update the display widgets
            self.holdings_text.insert('1.0', holdings_text)
            
            # Calculate and display summary
            total_gain_loss = total_value - total_invested
            total_gain_loss_pct = (total_gain_loss / total_invested * 100) if total_invested > 0 else 0
            
            summary_color = self.colors['success'] if total_gain_loss >= 0 else self.colors['danger']
            summary_text = "Portfolio Summary\n================\n\n"
            summary_text += f"Total Value: ${total_value:,.2f}\n"
            summary_text += f"Total Invested: ${total_invested:,.2f}\n"
            summary_text += f"Total Gain/Loss: {summary_color}${total_gain_loss:,.2f} ({total_gain_loss_pct:+.2f}%){self.colors['text_primary']}"
            
            self.summary_text.insert('1.0', summary_text)
            
        except Exception as e:
            print(f"Error updating portfolio display: {e}")
            self.holdings_text.insert('1.0', "Error updating portfolio display. Please try again.")
            self.summary_text.insert('1.0', "Error updating portfolio summary.")
        
        finally:
            # Always ensure text widgets are disabled when done
            self.holdings_text.config(state='disabled')
            self.summary_text.config(state='disabled')
        
        total_value = 0
        total_invested = 0
        total_gain_loss = 0
        
        # Sort portfolio by value
        def get_position_value(item):
            symbol, data = item
            shares = data.get('shares', 0)
            current_price = data.get('current_price')
            if current_price is None:
                current_price = data.get('avg_price', 0)
            return shares * current_price

        # Sort portfolio by value, handling None values
        try:
            sorted_portfolio = sorted(self.portfolio.items(), 
                                    key=get_position_value,
                                    reverse=True)
        except Exception:
            # If sorting fails, use original order
            sorted_portfolio = list(self.portfolio.items())
        
        for symbol, data in sorted_portfolio:
            shares = data.get('shares', 0)
            avg_price = data.get('avg_price', 0)
            invested = shares * avg_price
            total_invested += invested
            
            # Get current price if available
            current_price = data.get('current_price', avg_price)
            current_value = shares * current_price
            total_value += current_value
            
            # Special handling for CASH
            if symbol == "CASH":
                holdings_text += f"CASH Balance: ${shares:,.2f}\n\n"
                continue
            
            gain_loss = current_value - invested
            gain_loss_pct = (gain_loss / invested * 100) if invested > 0 else 0
            
            # Color coding for gains/losses
            gain_color = self.colors['success'] if gain_loss >= 0 else self.colors['danger']
            
            holdings_text += f"{symbol}: {shares:,.4f} shares\n"
            holdings_text += f"  Avg Price: ${avg_price:,.2f}\n"
            holdings_text += f"  Current: ${current_price:,.2f}\n"
            holdings_text += f"  Value: ${current_value:,.2f}\n"
            holdings_text += f"  Gain/Loss: {gain_color}${gain_loss:,.2f} ({gain_loss_pct:+.2f}%){self.colors['text_primary']}\n\n"
        
        self.holdings_text.insert('1.0', holdings_text)
        self.holdings_text.config(state='disabled')
        
        # Update summary
        self.summary_text.config(state='normal')
        self.summary_text.delete('1.0', tk.END)
        
        total_gain_loss = total_value - total_invested
        total_gain_loss_pct = (total_gain_loss / total_invested * 100) if total_invested > 0 else 0
        
        # Color coding for overall portfolio
        portfolio_color = self.colors['success'] if total_gain_loss >= 0 else self.colors['danger']
        
        summary_text = "PORTFOLIO SUMMARY\n"
        summary_text += "================\n\n"
        summary_text += f"Total Value: ${total_value:,.2f}\n"
        summary_text += f"Total Invested: ${total_invested:,.2f}\n"
        summary_text += f"Gain/Loss: {portfolio_color}${total_gain_loss:,.2f} ({total_gain_loss_pct:+.2f}%){self.colors['text_primary']}\n\n"
        
        # Asset allocation (simplified)
        summary_text += "Asset Allocation:\n"
        if total_value > 0:
            # Sort by value for allocation display
            allocation_data = []
            for symbol, data in sorted_portfolio:
                shares = data['shares']
                current_price = data.get('current_price', data.get('avg_price', 0))
                current_value = shares * current_price
                allocation = (current_value / total_value) * 100
                allocation_data.append((symbol, allocation, current_value))
            
            # Display top allocations
            for symbol, allocation, value in allocation_data:
                summary_text += f"  {symbol}: {allocation:.1f}% (${value:,.2f})\n"
        else:
            summary_text += "  No investments\n"
        
        # Add cash information
        summary_text += f"\nCash Available: ${self.cash_balance:,.2f}\n"
        summary_text += f"Total Net Worth: ${self.calculate_net_worth():,.2f}\n"
        
        self.summary_text.insert('1.0', summary_text)

    def add_transaction_record(self, date_str, category, amount, description=""):
        """Append a transaction to transactions_df and update cash balance."""
        try:
            date = pd.to_datetime(date_str)
        except Exception:
            date = pd.to_datetime(datetime.now())

        new_transaction = pd.DataFrame({
            'date': [date],
            'category': [category],
            'amount': [amount],
            'description': [description]
        })

        if self.transactions_df is not None and not self.transactions_df.empty:
            self.transactions_df = pd.concat([self.transactions_df, new_transaction], ignore_index=True)
        else:
            self.transactions_df = new_transaction

        # Update cash balance and save
        self.cash_balance = self.transactions_df['amount'].sum()
        # Mark this as programmatic (not CSV-uploaded) so recent view shows programmatic transactions
        self.csv_loaded = False
        self.save_data()
        self.update_dashboard()
        
    def add_financial_goal(self):
        """Add a new financial goal"""
        # Create goal dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Financial Goal")
        dialog.geometry("450x450")
        dialog.configure(bg=self.colors['bg_primary'])
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (450 // 2)
        y = (dialog.winfo_screenheight() // 2) - (450 // 2)
        dialog.geometry(f'450x450+{x}+{y}')
        
        tk.Label(dialog, text="Add Financial Goal", font=('Segoe UI', 16, 'bold'), 
                fg=self.colors['accent_purple'], bg=self.colors['bg_primary']).pack(pady=20)
        
        # Display current cash balance
        tk.Label(dialog, text=f"Available Cash: ${self.cash_balance:,.2f}", font=('Segoe UI', 12), 
                fg=self.colors['success'], bg=self.colors['bg_primary']).pack(pady=5)
        
        # Input fields
        input_frame = tk.Frame(dialog, bg=self.colors['bg_primary'])
        input_frame.pack(pady=10)
        
        # Goal Name
        tk.Label(input_frame, text="Goal Name:", font=('Segoe UI', 11), 
                fg=self.colors['text_primary'], bg=self.colors['bg_primary']).grid(row=0, column=0, sticky='w', pady=5)
        name_var = tk.StringVar()
        tk.Entry(input_frame, textvariable=name_var, font=('Segoe UI', 11),
                bg=self.colors['bg_secondary'], fg=self.colors['text_primary'],
                insertbackground=self.colors['accent_cyan'], width=20).grid(row=0, column=1, pady=5, padx=10)
        
        # Target Amount
        tk.Label(input_frame, text="Target ($):", font=('Segoe UI', 11), 
                fg=self.colors['text_primary'], bg=self.colors['bg_primary']).grid(row=1, column=0, sticky='w', pady=5)
        target_var = tk.StringVar()
        tk.Entry(input_frame, textvariable=target_var, font=('Segoe UI', 11),
                bg=self.colors['bg_secondary'], fg=self.colors['text_primary'],
                insertbackground=self.colors['accent_cyan'], width=20).grid(row=1, column=1, pady=5, padx=10)
        
        # Initial Contribution
        tk.Label(input_frame, text="Initial Contribution ($):", font=('Segoe UI', 11), 
                fg=self.colors['text_primary'], bg=self.colors['bg_primary']).grid(row=2, column=0, sticky='w', pady=5)
        current_var = tk.StringVar(value="0")
        tk.Entry(input_frame, textvariable=current_var, font=('Segoe UI', 11),
                bg=self.colors['bg_secondary'], fg=self.colors['text_primary'],
                insertbackground=self.colors['accent_cyan'], width=20).grid(row=2, column=1, pady=5, padx=10)
        
        # Use Cash Balance Option
        use_cash_var = tk.BooleanVar(value=False)
        cash_frame = tk.Frame(input_frame, bg=self.colors['bg_primary'])
        cash_frame.grid(row=3, column=0, columnspan=2, sticky='w', pady=10)
        
        tk.Checkbutton(cash_frame, text="Use cash balance for initial contribution", 
                      variable=use_cash_var, font=('Segoe UI', 11),
                      fg=self.colors['text_primary'], bg=self.colors['bg_primary'],
                      selectcolor=self.colors['bg_secondary'],
                      command=lambda: current_var.set("0") if not use_cash_var.get() else None).pack(anchor='w')
        
        # Add note about cash balance
        note_frame = tk.Frame(dialog, bg=self.colors['bg_primary'])
        note_frame.pack(pady=5, fill='x', padx=20)
        
        tk.Label(note_frame, text="Note: Using cash balance will reduce your available cash.",
                font=('Segoe UI', 10, 'italic'), fg=self.colors['text_secondary'],
                bg=self.colors['bg_primary'], wraplength=400, justify='left').pack(anchor='w')
        
        # Meaning / Type
        tk.Label(input_frame, text="Type/Meaning:", font=('Segoe UI', 11), 
                fg=self.colors['text_primary'], bg=self.colors['bg_primary']).grid(row=3, column=0, sticky='w', pady=5)
        meaning_var = tk.StringVar(value="Savings")
        ttk.Combobox(input_frame, values=['Savings', 'Emergency', 'Debt', 'Investment', 'Other'], textvariable=meaning_var, width=17).grid(row=3, column=1, pady=5, padx=10)

        def save_goal():
            name = name_var.get().strip()
            try:
                target = float(target_var.get())
                current = float(current_var.get())
                use_cash = use_cash_var.get()
                meaning = meaning_var.get().strip() if meaning_var.get() else 'Other'
                
                if name and target > 0:
                    # Check if using cash balance
                    if use_cash and current > 0:
                        if current > self.cash_balance:
                            messagebox.showerror("Error", "Insufficient cash balance")
                            return
                        
                        # Deduct from cash balance
                        self.cash_balance -= current
                        
                        # Add transaction record
                        transaction = {
                            'date': datetime.now().strftime('%Y-%m-%d'),
                            'description': f"Initial contribution to {name}",
                            'amount': -current,
                            'category': 'Savings',
                            'account': 'Cash'
                        }
                        
                        if hasattr(self, 'transactions'):
                            self.transactions.append(transaction)
                    
                    goal = {
                        'name': name,
                        'target': target,
                        'current': current,
                        'meaning': meaning
                    }
                    self.financial_goals.append(goal)
                    self.save_data()
                    self.update_goals_display()
                    self.update_dashboard()  # Update cash balance display
                    dialog.destroy()
                    messagebox.showinfo("Success", f"Added goal: {name}")
                else:
                    messagebox.showerror("Error", "Please enter valid data")
            except ValueError:
                messagebox.showerror("Error", "Please enter valid numbers for amounts")
        
        # Buttons
        button_frame = tk.Frame(dialog, bg=self.colors['bg_primary'])
        button_frame.pack(pady=20)
        
        tk.Button(button_frame, text="Save", command=save_goal,
                 bg=self.colors['success'], fg=self.colors['bg_primary'],
                 font=('Segoe UI', 11, 'bold'), padx=20, pady=5, relief='flat').pack(side='left', padx=10)
        
        tk.Button(button_frame, text="Cancel", command=dialog.destroy,
                 bg=self.colors['danger'], fg=self.colors['text_primary'],
                 font=('Segoe UI', 11, 'bold'), padx=20, pady=5, relief='flat').pack(side='left', padx=10)
        
    def update_goals_display(self):
        """Update financial goals display with detailed information"""
        # Check if goals_listbox exists
        if not hasattr(self, 'goals_listbox') or self.goals_listbox is None:
            print("Error updating dashboard: 'FinanceDashboard' object has no attribute 'goals_listbox'")
            return
            
        # Clear the listbox
        self.goals_listbox.delete(0, tk.END)
        
        # Add action buttons for goals
        button_frame = tk.Frame(self.goals_frame, bg=self.colors['bg_primary'])
        button_frame.pack(side='bottom', fill='x', pady=10, padx=20)
        
        # Remove old buttons if they exist
        for widget in button_frame.winfo_children():
            widget.destroy()
            
        if not self.financial_goals:
            self.goals_listbox.insert(tk.END, "No financial goals yet. Click 'Add Goal' to get started!")
            self.goals_listbox.insert(tk.END, "")
            self.goals_listbox.insert(tk.END, "Example goals you can track:")
            self.goals_listbox.insert(tk.END, "• Emergency Fund")
            self.goals_listbox.insert(tk.END, "• House Down Payment")
            self.goals_listbox.insert(tk.END, "• Vacation Savings")
            self.goals_listbox.insert(tk.END, "• Retirement Fund")
            self.goals_listbox.insert(tk.END, "• Debt Payoff")
            return
        
        # Add header
        self.goals_listbox.insert(tk.END, "FINANCIAL GOALS TRACKER")
        self.goals_listbox.insert(tk.END, "======================")
        self.goals_listbox.insert(tk.END, "")
        
        # Sort goals by progress (closest to completion first)
        sorted_goals = sorted(self.financial_goals, 
                            key=lambda x: x['current'] / x['target'] if x['target'] > 0 else 0, 
                            reverse=True)
        
        # Add column headers
        self.goals_listbox.insert(tk.END, f"{'Goal':<25} {'Target':<15} {'Current':<15} {'Progress':<20}")
        self.goals_listbox.insert(tk.END, "-" * 80)
        
        # Add each goal as a separate item in the listbox - only add each goal once
        added_goals = set()  # Track which goals we've already added
        for i, goal in enumerate(sorted_goals):
            name = goal['name']
            
            # Skip if we've already added this goal
            if name in added_goals:
                continue
                
            added_goals.add(name)  # Mark this goal as added
            
            target = goal['target']
            current = goal['current']
            meaning = goal.get('meaning', '')
            progress = (current / target) * 100 if target > 0 else 0
            
            # Progress bar
            bar_length = 20
            filled_length = int(bar_length * progress // 100)
            bar = '█' * filled_length + '░' * (bar_length - filled_length)
            
            # Format the progress string (include meaning)
            meaning_suffix = f" [{meaning}]" if meaning else ""
            progress_str = f"{name:<22}{meaning_suffix:<10} ${target:<14,.0f} ${current:<14,.0f} {progress:>5.1f}% {bar}"
            
            # Add the goal to the listbox
            self.goals_listbox.insert(tk.END, progress_str)
        
        # Add summary statistics
        total_goals = len(added_goals)  # Count unique goals
        completed_goals = sum(1 for goal in self.financial_goals if goal['current'] >= goal['target'])
        total_target = sum(goal['target'] for goal in self.financial_goals)
        total_current = sum(goal['current'] for goal in self.financial_goals)
        overall_progress = (total_current / total_target * 100) if total_target > 0 else 0
        
        self.goals_listbox.insert(tk.END, "")
        self.goals_listbox.insert(tk.END, "=" * 80)
        self.goals_listbox.insert(tk.END, f"Total Goals: {total_goals} | Completed: {completed_goals} | Overall Progress: {overall_progress:.1f}%")
        self.goals_listbox.insert(tk.END, f"Total Target: ${total_target:,.0f} | Total Saved: ${total_current:,.0f}")
        
        # Add action buttons for goals
        tk.Button(button_frame, text="Edit Goal", command=self.edit_goal,
                 bg=self.colors['accent_cyan'], fg=self.colors['text_primary'],
                 font=('Segoe UI', 10, 'bold'), padx=15, pady=5, relief='flat').pack(side='left', padx=10)
        
        tk.Button(button_frame, text="Delete Goal", command=self.delete_goal,
                 bg=self.colors['danger'], fg=self.colors['text_primary'],
                 font=('Segoe UI', 10, 'bold'), padx=15, pady=5, relief='flat').pack(side='left', padx=10)
        
        tk.Button(button_frame, text="Contribute to Goal", command=self.contribute_to_goal,
                 bg=self.colors['success'], fg=self.colors['bg_primary'],
                 font=('Segoe UI', 10, 'bold'), padx=15, pady=5, relief='flat').pack(side='left', padx=10)
        
    def edit_goal(self):
        """Edit an existing financial goal"""
        # Get selected goal
        try:
            selected_index = self.goals_listbox.curselection()[0]
            selected_text = self.goals_listbox.get(selected_index)
            
            # Skip if header or summary
            if not selected_text or selected_text.startswith("=") or selected_text.startswith("FINANCIAL") or selected_text.startswith("Total"):
                messagebox.showinfo("Select Goal", "Please select a valid goal to edit")
                return
                
            # Extract goal name from the selected text
            goal_name = selected_text.split()[0]
            
            # Find the goal in the list
            goal_to_edit = None
            for goal in self.financial_goals:
                if goal['name'] == goal_name:
                    goal_to_edit = goal
                    break
                    
            if not goal_to_edit:
                messagebox.showinfo("Goal Not Found", "Could not find the selected goal")
                return
                
            # Create edit dialog
            dialog = tk.Toplevel(self.root)
            dialog.title("Edit Financial Goal")
            dialog.geometry("400x350")
            dialog.configure(bg=self.colors['bg_primary'])
            dialog.transient(self.root)
            dialog.grab_set()
            
            # Center dialog
            dialog.update_idletasks()
            x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
            y = (dialog.winfo_screenheight() // 2) - (350 // 2)
            dialog.geometry(f'400x350+{x}+{y}')
            
            tk.Label(dialog, text="Edit Financial Goal", font=('Segoe UI', 16, 'bold'), 
                    fg=self.colors['accent_purple'], bg=self.colors['bg_primary']).pack(pady=20)
            
            # Input fields
            input_frame = tk.Frame(dialog, bg=self.colors['bg_primary'])
            input_frame.pack(pady=10)
            
            # Goal Name
            tk.Label(input_frame, text="Goal Name:", font=('Segoe UI', 11), 
                    fg=self.colors['text_primary'], bg=self.colors['bg_primary']).grid(row=0, column=0, sticky='w', pady=5)
            name_var = tk.StringVar(value=goal_to_edit['name'])
            tk.Entry(input_frame, textvariable=name_var, font=('Segoe UI', 11),
                    bg=self.colors['bg_secondary'], fg=self.colors['text_primary'],
                    insertbackground=self.colors['accent_cyan'], width=20).grid(row=0, column=1, pady=5, padx=10)
            
            # Target Amount
            tk.Label(input_frame, text="Target ($):", font=('Segoe UI', 11), 
                    fg=self.colors['text_primary'], bg=self.colors['bg_primary']).grid(row=1, column=0, sticky='w', pady=5)
            target_var = tk.StringVar(value=str(goal_to_edit['target']))
            tk.Entry(input_frame, textvariable=target_var, font=('Segoe UI', 11),
                    bg=self.colors['bg_secondary'], fg=self.colors['text_primary'],
                    insertbackground=self.colors['accent_cyan'], width=20).grid(row=1, column=1, pady=5, padx=10)
            
            # Current Amount
            tk.Label(input_frame, text="Current ($):", font=('Segoe UI', 11), 
                    fg=self.colors['text_primary'], bg=self.colors['bg_primary']).grid(row=2, column=0, sticky='w', pady=5)
            current_var = tk.StringVar(value=str(goal_to_edit['current']))
            tk.Entry(input_frame, textvariable=current_var, font=('Segoe UI', 11),
                    bg=self.colors['bg_secondary'], fg=self.colors['text_primary'],
                    insertbackground=self.colors['accent_cyan'], width=20).grid(row=2, column=1, pady=5, padx=10)
            # Meaning / Type
            tk.Label(input_frame, text="Type/Meaning:", font=('Segoe UI', 11), 
                    fg=self.colors['text_primary'], bg=self.colors['bg_primary']).grid(row=3, column=0, sticky='w', pady=5)
            meaning_var = tk.StringVar(value=goal_to_edit.get('meaning', 'Savings'))
            ttk.Combobox(input_frame, values=['Savings', 'Emergency', 'Debt', 'Investment', 'Other'], textvariable=meaning_var, width=17).grid(row=3, column=1, pady=5, padx=10)
            
            def save_edited_goal():
                name = name_var.get().strip()
                try:
                    target = float(target_var.get())
                    current = float(current_var.get())
                    
                    if name and target > 0:
                        # Update the goal
                        goal_to_edit['name'] = name
                        goal_to_edit['target'] = target
                        goal_to_edit['current'] = current
                        # Update meaning if present
                        goal_to_edit['meaning'] = meaning_var.get().strip() if meaning_var.get() else goal_to_edit.get('meaning', 'Other')
                        
                        self.save_data()
                        self.update_goals_display()
                        dialog.destroy()
                        messagebox.showinfo("Success", f"Updated goal: {name}")
                    else:
                        messagebox.showerror("Error", "Please enter valid data")
                except ValueError:
                    messagebox.showerror("Error", "Please enter valid numbers for amounts")
            
            # Buttons
            button_frame = tk.Frame(dialog, bg=self.colors['bg_primary'])
            button_frame.pack(pady=20)
            
            tk.Button(button_frame, text="Save", command=save_edited_goal,
                     bg=self.colors['success'], fg=self.colors['bg_primary'],
                     font=('Segoe UI', 11, 'bold'), padx=20, pady=5, relief='flat').pack(side='left', padx=10)
            
            tk.Button(button_frame, text="Cancel", command=dialog.destroy,
                     bg=self.colors['danger'], fg=self.colors['text_primary'],
                     font=('Segoe UI', 11, 'bold'), padx=20, pady=5, relief='flat').pack(side='left', padx=10)
            
        except IndexError:
            messagebox.showinfo("Select Goal", "Please select a goal to edit")
    
    def delete_goal(self):
        """Delete a financial goal"""
        try:
            selected_index = self.goals_listbox.curselection()[0]
            selected_text = self.goals_listbox.get(selected_index)
            
            # Skip if header or summary
            if not selected_text or selected_text.startswith("=") or selected_text.startswith("FINANCIAL") or selected_text.startswith("Total"):
                messagebox.showinfo("Select Goal", "Please select a valid goal to delete")
                return
                
            # Extract goal name from the selected text
            goal_name = selected_text.split()[0]
            
            # Confirm deletion
            confirm = messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete the goal '{goal_name}'?")
            if not confirm:
                return
                
            # Find and remove the goal
            for i, goal in enumerate(self.financial_goals):
                if goal['name'] == goal_name:
                    del self.financial_goals[i]
                    break
                    
            self.save_data()
            self.update_goals_display()
            messagebox.showinfo("Success", f"Deleted goal: {goal_name}")
            
        except IndexError:
            messagebox.showinfo("Select Goal", "Please select a goal to delete")
    
    def contribute_to_goal(self):
        """Contribute to a financial goal from cash balance"""
        try:
            selected_index = self.goals_listbox.curselection()[0]
            selected_text = self.goals_listbox.get(selected_index)
            
            # Skip if header or summary
            if not selected_text or selected_text.startswith("=") or selected_text.startswith("FINANCIAL") or selected_text.startswith("Total"):
                messagebox.showinfo("Select Goal", "Please select a valid goal to contribute to")
                return
                
            # Extract goal name from the selected text
            goal_name = selected_text.split()[0]
            
            # Find the goal in the list
            goal_to_contribute = None
            for goal in self.financial_goals:
                if goal['name'] == goal_name:
                    goal_to_contribute = goal
                    break
                    
            if not goal_to_contribute:
                messagebox.showinfo("Goal Not Found", "Could not find the selected goal")
                return
                
            # Create contribution dialog
            dialog = tk.Toplevel(self.root)
            dialog.title("Contribute to Goal")
            dialog.geometry("400x300")
            dialog.configure(bg=self.colors['bg_primary'])
            dialog.transient(self.root)
            dialog.grab_set()
            
            # Center dialog
            dialog.update_idletasks()
            x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
            y = (dialog.winfo_screenheight() // 2) - (300 // 2)
            dialog.geometry(f'400x300+{x}+{y}')
            
            tk.Label(dialog, text=f"Contribute to: {goal_name}", font=('Segoe UI', 16, 'bold'), 
                    fg=self.colors['accent_purple'], bg=self.colors['bg_primary']).pack(pady=20)
            
            # Display current cash balance
            tk.Label(dialog, text=f"Available Cash: ${self.cash_balance:,.2f}", font=('Segoe UI', 12), 
                    fg=self.colors['success'], bg=self.colors['bg_primary']).pack(pady=5)
            
            # Input fields
            input_frame = tk.Frame(dialog, bg=self.colors['bg_primary'])
            input_frame.pack(pady=10)
            
            # Contribution Amount
            tk.Label(input_frame, text="Amount to Contribute ($):", font=('Segoe UI', 11), 
                    fg=self.colors['text_primary'], bg=self.colors['bg_primary']).grid(row=0, column=0, sticky='w', pady=5)
            amount_var = tk.StringVar()
            tk.Entry(input_frame, textvariable=amount_var, font=('Segoe UI', 11),
                    bg=self.colors['bg_secondary'], fg=self.colors['text_primary'],
                    insertbackground=self.colors['accent_cyan'], width=15).grid(row=0, column=1, pady=5, padx=10)
            
            def make_contribution():
                try:
                    amount = float(amount_var.get())
                    
                    if amount <= 0:
                        messagebox.showerror("Error", "Please enter a positive amount")
                        return
                        
                    if amount > self.cash_balance:
                        messagebox.showerror("Error", "Insufficient cash balance")
                        return
                        
                    # Update goal and cash balance
                    goal_to_contribute['current'] += amount
                    self.cash_balance -= amount
                    
                    # Add transaction record
                    transaction = {
                        'date': datetime.now().strftime('%Y-%m-%d'),
                        'description': f"Contribution to {goal_name}",
                        'amount': -amount,
                        'category': 'Savings',
                        'account': 'Cash'
                    }
                    
                    if hasattr(self, 'transactions'):
                        self.transactions.append(transaction)
                    
                    self.save_data()
                    self.update_goals_display()
                    self.update_dashboard()  # Update cash balance display
                    
                    dialog.destroy()
                    messagebox.showinfo("Success", f"Contributed ${amount:,.2f} to {goal_name}")
                    
                except ValueError:
                    messagebox.showerror("Error", "Please enter a valid number")
            
            # Buttons
            button_frame = tk.Frame(dialog, bg=self.colors['bg_primary'])
            button_frame.pack(pady=20)
            
            tk.Button(button_frame, text="Contribute", command=make_contribution,
                     bg=self.colors['success'], fg=self.colors['bg_primary'],
                     font=('Segoe UI', 11, 'bold'), padx=20, pady=5, relief='flat').pack(side='left', padx=10)
            
            tk.Button(button_frame, text="Cancel", command=dialog.destroy,
                     bg=self.colors['danger'], fg=self.colors['text_primary'],
                     font=('Segoe UI', 11, 'bold'), padx=20, pady=5, relief='flat').pack(side='left', padx=10)
            
        except IndexError:
            messagebox.showinfo("Select Goal", "Please select a goal to contribute to")
    
    def convert_currency(self):
        """Convert currency using API"""
        try:
            amount = float(self.amount_var.get())
            from_c = self.from_curr.get()
            to_c = self.to_curr.get()
            
            if from_c == to_c:
                self.currency_result.config(text=f"{amount} {from_c} = {amount} {to_c}")
                return
            
            def fetch():
                try:
                    url = f"https://open.er-api.com/v6/latest/{from_c}"
                    response = requests.get(url, timeout=10)
                    data = response.json()
                    
                    if data.get('result') == 'success':
                        rate = data['rates'].get(to_c)
                        if rate:
                            converted = amount * rate
                            result = f"{amount} {from_c} = {converted:.2f} {to_c}\nRate: 1 {from_c} = {rate:.4f} {to_c}"
                        else:
                            result = f"Rate not available for {to_c}"
                    else:
                        result = "Failed to fetch rate"
                    
                    self.root.after(0, lambda: self.currency_result.config(text=result))
                    
                except Exception as e:
                    error = f"Error: {e}"
                    self.root.after(0, lambda: self.currency_result.config(text=error))
            
            self.currency_result.config(text="Converting...")
            threading.Thread(target=fetch, daemon=True).start()
            
        except ValueError:
            self.currency_result.config(text="Enter valid amount")
    
    def show_pie_chart(self):
        """Show expense pie chart with hover tooltips"""
        if self.transactions_df is None:
            return
        
        # Clear chart area
        for widget in self.chart_frame.winfo_children():
            widget.destroy()
        
        # Get expense data
        expenses = self.transactions_df[self.transactions_df['amount'] < 0].copy()
        if expenses.empty:
            tk.Label(self.chart_frame, text="No expense data", fg=self.colors['text_primary'], bg=self.colors['bg_secondary']).pack()
            return
        
        expenses['amount'] = expenses['amount'].abs()
        category_totals = expenses.groupby('category')['amount'].sum()
        
        # Create chart with enhanced interactivity
        fig, ax = plt.subplots(figsize=(8, 6), facecolor='#34495e')
        ax.set_facecolor('#34495e')
        
        # Create pie chart with better styling
        colors = plt.cm.Set3(np.linspace(0, 1, len(category_totals)))
        wedges, texts, autotexts = ax.pie(category_totals.values, 
                                        labels=category_totals.index,
                                        autopct='%1.1f%%', startangle=90,
                                        colors=colors, explode=[0.05]*len(category_totals))
        
        ax.set_title('Expense Distribution by Category\n(Hover over slices for details)', 
                    color='white', fontsize=14, fontweight='bold', pad=20)
        
        # Style text
        for text in texts:
            text.set_color('white')
            text.set_fontsize(10)
            text.set_fontweight('bold')
        for autotext in autotexts:
            autotext.set_color('black')
            autotext.set_fontweight('bold')
            autotext.set_fontsize(9)
        
        # Add hover functionality with better positioning
        def on_hover(event):
            if event.inaxes == ax:
                for i, wedge in enumerate(wedges):
                    if wedge.contains_point([event.x, event.y]):
                        category = category_totals.index[i]
                        amount = category_totals.values[i]
                        percentage = (amount / category_totals.sum()) * 100
                        
                        # Create tooltip text positioned at bottom
                        tooltip_text = f'{category}: ${amount:,.2f} ({percentage:.1f}%)'
                        
                        # Position tooltip at bottom to avoid button overlap
                        ax.text(0.5, 0.02, tooltip_text, transform=ax.transAxes,
                               bbox=dict(boxstyle='round,pad=0.5', facecolor='black', alpha=0.8),
                               color='white', fontsize=12, fontweight='bold',
                               horizontalalignment='center', verticalalignment='bottom')
                        
                        fig.canvas.draw_idle()
                        return
                # Clear tooltip when not hovering over any slice
                for txt in ax.texts[:]:
                    if hasattr(txt, 'get_bbox_patch') and txt.get_bbox_patch():
                        txt.remove()
                fig.canvas.draw_idle()
        
        # Connect hover event
        fig.canvas.mpl_connect('motion_notify_event', on_hover)
        
        plt.tight_layout()
        
        # Embed in tkinter
        canvas = FigureCanvasTkAgg(fig, self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)
    
    def show_line_chart(self):
        """Show cash flow line chart with interactive hover tooltips"""
        if self.transactions_df is None:
            return
        
        # Clear chart area
        for widget in self.chart_frame.winfo_children():
            widget.destroy()
        
        df = self.transactions_df.copy().sort_values('date')
        df['cumulative'] = df['amount'].cumsum()
        
        # Create chart with enhanced styling
        fig, ax = plt.subplots(figsize=(10, 6), facecolor='#34495e')
        ax.set_facecolor('#34495e')
        
        # Plot line with markers
        line, = ax.plot(df['date'], df['cumulative'], 
                       color='#3498db', linewidth=3, marker='o', 
                       markersize=8, markerfacecolor='#3498db', 
                       markeredgecolor='white', markeredgewidth=2,
                       alpha=0.9)
        
        # Add zero line
        ax.axhline(y=0, color='#e74c3c', linestyle='--', alpha=0.7, linewidth=2)
        
        # Style the chart
        ax.set_title('Cumulative Cash Flow Over Time\n(Hover over points for details)', 
                    color='white', fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Date', color='white', fontsize=12, fontweight='bold')
        ax.set_ylabel('Cumulative Amount ($)', color='white', fontsize=12, fontweight='bold')
        
        # Style axes
        ax.tick_params(colors='white', labelsize=10)
        ax.grid(True, alpha=0.3, color='white')
        for spine in ax.spines.values():
            spine.set_color('white')
            spine.set_linewidth(1.5)
        
        # Format x-axis dates
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
        fig.autofmt_xdate(rotation=45)
        
        # Add interactive hover functionality with better positioning
        def on_hover(event):
            if event.inaxes == ax and event.xdata is not None:
                # Find closest point
                dates_num = mdates.date2num(df['date'])
                closest_idx = np.argmin(np.abs(dates_num - event.xdata))
                
                if closest_idx < len(df):
                    closest_date = df.iloc[closest_idx]['date']
                    closest_amount = df.iloc[closest_idx]['cumulative']
                    closest_transaction = df.iloc[closest_idx]['amount']
                    closest_category = df.iloc[closest_idx]['category']
                    
                    # Create tooltip text
                    date_str = closest_date.strftime('%Y-%m-%d')
                    tooltip_text = f'Date: {date_str} | Balance: ${closest_amount:,.2f}\nTransaction: {closest_category} ${closest_transaction:,.2f}'
                    
                    # Position tooltip to avoid overlap with title
                    ax.text(0.02, 0.02, tooltip_text, transform=ax.transAxes,
                           bbox=dict(boxstyle='round,pad=0.5', facecolor='black', alpha=0.8),
                           color='white', fontsize=10, fontweight='bold',
                           verticalalignment='bottom')
                    
                    # Highlight the point
                    if hasattr(ax, '_hover_point'):
                        ax._hover_point.remove()
                    
                    ax._hover_point = ax.plot(closest_date, closest_amount, 
                                            'o', markersize=12, color='#f39c12', 
                                            markeredgecolor='white', markeredgewidth=3)[0]
                    
                    fig.canvas.draw_idle()
        
        def on_leave(event):
            # Remove tooltip when mouse leaves
            # Clear any text annotations
            for txt in ax.texts[:]:
                if hasattr(txt, 'get_bbox_patch') and txt.get_bbox_patch():
                    txt.remove()
            
            # Remove highlight point
            if hasattr(ax, '_hover_point'):
                ax._hover_point.remove()
                delattr(ax, '_hover_point')
            
            fig.canvas.draw_idle()
        
        # Connect events
        fig.canvas.mpl_connect('motion_notify_event', on_hover)
        fig.canvas.mpl_connect('axes_leave_event', on_leave)
        
        plt.tight_layout()
        
        # Embed in tkinter
        canvas = FigureCanvasTkAgg(fig, self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)

    def export_portfolio_data(self):
        """Export portfolio data to CSV"""
        if not self.portfolio:
            messagebox.showwarning("Warning", "No portfolio data to export")
            return
            
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")],
                title="Export Portfolio Data"
            )
            
            if not file_path:
                return
                
            # Create DataFrame from portfolio
            data = []
            for symbol, details in self.portfolio.items():
                data.append({
                    'Symbol': symbol,
                    'Shares': details['shares'],
                    'Average Price': details['avg_price'],
                    'Current Value': details['shares'] * details['avg_price']
                })
                
            df = pd.DataFrame(data)
            df.to_csv(file_path, index=False)
            
            messagebox.showinfo("Success", f"Portfolio data exported to {file_path}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export portfolio data: {e}")


def main():
    root = tk.Tk()
    app = FinanceDashboard(root)
    
    # Center window with premium sizing
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (1200 // 2)
    y = (root.winfo_screenheight() // 2) - (800 // 2)
    root.geometry(f'1200x800+{x}+{y}')
    
    # Set app icon and properties
    root.resizable(True, True)
    root.minsize(1000, 600)
    
    root.mainloop()

if __name__ == "__main__":
    main()
