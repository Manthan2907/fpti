"""
Modern Transaction Analyzer - Enhanced Python Version
Beautiful UI with rounded corners, gradient colors, and proper spacing
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import seaborn as sns
from PIL import Image, ImageTk, ImageDraw
import os
from matplotlib.widgets import Cursor
import matplotlib.patches as patches

# Set beautiful color scheme
plt.style.use('default')
sns.set_palette("husl")

class ModernTransactionAnalyzer:
    def __init__(self, root):
        self.root = root
        self.setup_window()
        self.setup_styles()
        self.create_widgets()
        self.df = self.create_sample_data()
        self.filtered_df = self.df.copy()  # Initialize filtered_df
        self.update_all_displays()  # Initial display update
    def clean_transaction_data(self, df):
        """
        Clean transaction data - handle NaNs, convert dates
        Demonstrates pandas data cleaning concepts
        """
        print("🧹 CLEANING DATA:")
        print(f"Initial rows: {len(df)}")
        print(f"Columns: {list(df.columns)}")
        
        # Check if required columns exist
        required_columns = ['Date', 'Amount']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            print(f"Missing required columns: {missing_columns}")
            # Try to find similar column names
            for col in missing_columns:
                similar_cols = [c for c in df.columns if col.lower() in c.lower() or c.lower() in col.lower()]
                if similar_cols:
                    print(f"Found similar column for {col}: {similar_cols[0]}")
                    df = df.rename(columns={similar_cols[0]: col})
        
        print(f"Missing dates: {df['Date'].isna().sum() if 'Date' in df.columns else 'Date column missing'}")
        print(f"Missing amounts: {df['Amount'].isna().sum() if 'Amount' in df.columns else 'Amount column missing'}")
        
        # Handle missing dates - drop these records
        if 'Date' in df.columns:
            df = df.dropna(subset=['Date'])
            print(f"After removing missing dates: {len(df)}")
            
            # Convert dates with error handling
            try:
                df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
                df = df.dropna(subset=['Date'])  # Remove invalid dates
                print(f"After date conversion: {len(df)}")
            except Exception as e:
                print(f"Date conversion error: {e}")
                return pd.DataFrame()  # Return empty DataFrame if date conversion fails
        
        # Handle missing amounts - could fill with 0 or drop
        if 'Amount' in df.columns:
            initial_len = len(df)
            df = df.dropna(subset=['Amount'])
            print(f"After removing missing amounts: {len(df)} (removed {initial_len - len(df)})")
            
            # Convert amounts to numeric
            try:
                df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
                df = df.dropna(subset=['Amount'])
            except Exception as e:
                print(f"Amount conversion error: {e}")
        
        # Fill missing categories with 'Uncategorized'
        df['Category'] = df['Category'].fillna('Uncategorized')
        
        # Fill missing accounts with 'Unknown'
        df['Account'] = df['Account'].fillna('Unknown')
        
        # Create Type column using apply
        df['Type'] = df['Amount'].apply(lambda x: 'Income' if x > 0 else 'Expense')
        
        # Sort by date and reset index
        df = df.sort_values('Date').reset_index(drop=True)
        
        print(f"Final cleaned rows: {len(df)}")
        print("✅ Data cleaning complete!")
        
        return df
    
    def calculate_monthly_analysis(self):
        """
        Calculate monthly income and expenses by category using groupby
        Demonstrates pandas groupby operations
        """
        df = self.filtered_df.copy()
        
        # Check if required columns exist
        if 'Date' not in df.columns or 'Amount' not in df.columns:
            print("Missing required columns for analysis")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
        try:
            # Ensure Date is datetime
            df['Date'] = pd.to_datetime(df['Date'])
            
            # Set date as index for resampling
            df_indexed = df.set_index('Date')
            
            # Create month-year column for grouping
            df_indexed['Month'] = df_indexed.index.to_period('M')
            
            # GROUP BY 1: Monthly totals by income/expense type
            monthly_totals = df_indexed.groupby(['Month', 'Type'])['Amount'].agg(['sum', 'count', 'mean']).round(2)
            print("📊 MONTHLY TOTALS BY TYPE:")
            print(monthly_totals.head(10))
            print()
            
            # GROUP BY 2: Monthly expenses by category
            expenses = df_indexed[df_indexed['Amount'] < 0].copy()
            expenses['Amount'] = expenses['Amount'].abs()  # Make positive for easier analysis
            
            monthly_category_expenses = expenses.groupby(['Month', 'Category'])['Amount'].agg([
                'sum', 'count', 'mean'
            ]).round(2)
            # Rename columns for clarity
            monthly_category_expenses.columns = ['total', 'count', 'avg_transaction']
            
            print("💸 MONTHLY EXPENSES BY CATEGORY:")
            print(monthly_category_expenses.head(15))
            print()
            
            # GROUP BY 3: Account analysis
            account_analysis = df_indexed.groupby(['Account', 'Type'])['Amount'].agg(['sum', 'count']).round(2)
            print("🏦 ACCOUNT ANALYSIS:")
            print(account_analysis)
            print()
            
            return monthly_totals, monthly_category_expenses, account_analysis
            
        except Exception as e:
            print(f"Error in monthly analysis: {e}")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    def calculate_rolling_averages(self):
        """
        Calculate rolling average spending over time
        Demonstrates datetime indexing and rolling operations
        """
        df = self.filtered_df.copy()
        
        # Check if required columns exist
        if 'Date' not in df.columns or 'Amount' not in df.columns:
            print("Missing required columns for rolling averages")
            return pd.DataFrame()
        
        try:
            # Ensure Date is datetime
            df['Date'] = pd.to_datetime(df['Date'])
            df_indexed = df.set_index('Date')
            
            # Daily spending (expenses only, made positive)
            daily_expenses = df_indexed[df_indexed['Amount'] < 0]['Amount'].abs().resample('D').sum()
            
            # Calculate different rolling averages
            rolling_data = pd.DataFrame({
                'daily_spending': daily_expenses,
                'rolling_7day': daily_expenses.rolling(window=7, min_periods=1).mean(),
                'rolling_30day': daily_expenses.rolling(window=30, min_periods=1).mean(),
                'rolling_std': daily_expenses.rolling(window=7, min_periods=1).std()
            }).round(2)
            
            # Remove zero-spending days for cleaner analysis
            rolling_data = rolling_data[rolling_data['daily_spending'] > 0]
            
            print("📈 ROLLING AVERAGE ANALYSIS:")
            print(rolling_data.head(10))
            if len(rolling_data) > 0:
                print(f"Average daily spending: ${rolling_data['daily_spending'].mean():.2f}")
                print(f"7-day rolling average range: ${rolling_data['rolling_7day'].min():.2f} - ${rolling_data['rolling_7day'].max():.2f}")
            print()
            
            return rolling_data
        
        except Exception as e:
            print(f"Error in rolling averages calculation: {e}")
            return pd.DataFrame()
    
    def identify_top_spending_categories(self):
        """
        Identify top 3 spending categories with detailed analysis
        """
        expenses = self.filtered_df[self.filtered_df['Amount'] < 0].copy()
        expenses['Amount'] = expenses['Amount'].abs()
        
        # GROUP BY category with multiple aggregations
        category_analysis = expenses.groupby('Category')['Amount'].agg([
            'sum',           # Total spent
            'count',         # Number of transactions
            'mean',          # Average transaction
            'median',        # Median transaction
            'std'            # Standard deviation
        ]).round(2)
        
        # Sort by total spending
        category_analysis = category_analysis.sort_values('sum', ascending=False)
        
        print("🏆 TOP SPENDING CATEGORIES ANALYSIS:")
        print("=" * 60)
        for i, (category, data) in enumerate(category_analysis.head(3).iterrows()):
            print(f"{i+1}. {category}")
            print(f"   💰 Total Spent: ${data['sum']:,.2f}")
            print(f"   🧾 Transactions: {data['count']}")
            print(f"   📊 Avg per transaction: ${data['mean']:,.2f}")
            print(f"   📈 Median transaction: ${data['median']:,.2f}")
            if not pd.isna(data['std']):
                print(f"   📉 Std deviation: ${data['std']:,.2f}")
            print()
        
        return category_analysis.head(3)
    
    def merge_with_budget_data(self):
        """
        Demonstrate DataFrame merging with budget data
        """
        # Create sample budget data
        budget_data = {
            'Category': ['Housing', 'Food & Dining', 'Transportation', 'Entertainment', 
                        'Groceries', 'Utilities', 'Shopping', 'Health & Fitness'],
            'Monthly_Budget': [2000, 400, 300, 150, 500, 200, 300, 100],
            'Budget_Type': ['Fixed', 'Variable', 'Variable', 'Discretionary',
                           'Variable', 'Fixed', 'Discretionary', 'Fixed']
        }
        budget_df = pd.DataFrame(budget_data)
        
        # Calculate actual monthly spending by category
        expenses = self.filtered_df[self.filtered_df['Amount'] < 0].copy()
        expenses['Amount'] = expenses['Amount'].abs()
        expenses['Month'] = expenses['Date'].dt.to_period('M')
        
        actual_spending = expenses.groupby(['Month', 'Category'])['Amount'].sum().reset_index()
        
        # Get latest month for comparison
        latest_month = actual_spending['Month'].max()
        latest_spending = actual_spending[actual_spending['Month'] == latest_month]
        
        # MERGE DataFrames - demonstrating pandas merge
        budget_vs_actual = budget_df.merge(
            latest_spending[['Category', 'Amount']], 
            on='Category', 
            how='left'
        )
        budget_vs_actual['Amount'] = budget_vs_actual['Amount'].fillna(0)
        budget_vs_actual['Variance'] = budget_vs_actual['Monthly_Budget'] - budget_vs_actual['Amount']
        budget_vs_actual['Variance_Pct'] = (budget_vs_actual['Variance'] / budget_vs_actual['Monthly_Budget'] * 100).round(1)
        
        print("💼 BUDGET vs ACTUAL ANALYSIS (Latest Month):")
        print("=" * 70)
        for _, row in budget_vs_actual.iterrows():
            status = "✅ Under" if row['Variance'] > 0 else "⚠️ Over"
            print(f"{row['Category']:15} | Budget: ${row['Monthly_Budget']:6.0f} | Actual: ${row['Amount']:6.2f} | {status} by ${abs(row['Variance']):6.2f} ({row['Variance_Pct']:+5.1f}%)")
        
        return budget_vs_actual
        
    def setup_window(self):
        self.root.title("💰 Transaction Analyzer Pro")
        self.root.geometry("1400x900")  # Reduced from 1600x1000 for better fit
        self.root.configure(bg='#f8fafc')
        self.root.minsize(1200, 800)  # Set minimum size
        
        # Center window
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (1400 // 2)
        y = (self.root.winfo_screenheight() // 2) - (900 // 2)
        self.root.geometry(f"1400x900+{x}+{y}")
        
    def setup_styles(self):
        # Color palette
        self.colors = {
            'primary': '#3b82f6',
            'secondary': '#8b5cf6', 
            'success': '#10b981',
            'warning': '#f59e0b',
            'danger': '#ef4444',
            'info': '#06b6d4',
            'light': '#f8fafc',
            'white': '#ffffff',
            'dark': '#1e293b',
            'muted': '#64748b'
        }
        
        # Configure ttk styles
        style = ttk.Style()
        style.theme_use('clam')
        
        # Button styles
        style.configure('Primary.TButton',
                       background=self.colors['primary'],
                       foreground='white',
                       padding=(20, 10),
                       font=('Inter', 10, 'bold'))
        
        style.configure('Success.TButton',
                       background=self.colors['success'],
                       foreground='white',
                       padding=(15, 8),
                       font=('Inter', 9, 'bold'))
        
        # Frame styles
        style.configure('Card.TFrame',
                       background=self.colors['white'],
                       relief='flat',
                       borderwidth=0)
        
    def create_rounded_rectangle(self, width, height, radius, color):
        """Create a rounded rectangle image for modern UI elements"""
        image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Convert hex color to RGB
        color_rgb = tuple(int(color[i:i+2], 16) for i in (1, 3, 5))
        
        # Draw rounded rectangle
        draw.rounded_rectangle([0, 0, width-1, height-1], radius=radius, fill=color_rgb)
        return ImageTk.PhotoImage(image)
        
    def create_widgets(self):
        # Main container with padding — make it scrollable using a Canvas + vertical scrollbar
        container = ttk.Frame(self.root)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Canvas that will host the scrolling area
        canvas = tk.Canvas(container, bg=self.colors['white'], highlightthickness=0)
        v_scroll = ttk.Scrollbar(container, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=v_scroll.set)

        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # The frame that holds all actual UI widgets — placed inside the canvas
        main_frame = ttk.Frame(canvas, style='Card.TFrame')
        self._main_canvas = canvas
        # create_window returns an id we can later use to resize the inner frame to canvas width
        self._main_frame_window = canvas.create_window((0, 0), window=main_frame, anchor='nw')

        # Keep the scrollregion updated when the inner frame changes size
        def _on_frame_config(event):
            try:
                canvas.configure(scrollregion=canvas.bbox('all'))
            except Exception:
                pass
        main_frame.bind('<Configure>', _on_frame_config)

        # Ensure the inner frame width always matches the canvas width
        def _on_canvas_config(event):
            try:
                canvas.itemconfig(self._main_frame_window, width=event.width)
            except Exception:
                pass
        canvas.bind('<Configure>', _on_canvas_config)

        # Mouse wheel scrolling (Windows / Mac / X11 fallbacks)
        def _on_mousewheel_windows(event):
            # event.delta is a multiple of 120 on Windows
            canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')

        def _on_mousewheel_linux(event):
            # event.num == 4 (up) or 5 (down)
            if event.num == 4:
                canvas.yview_scroll(-1, 'units')
            elif event.num == 5:
                canvas.yview_scroll(1, 'units')

        # Bind/unbind mousewheel only when pointer is over the canvas to avoid interfering with other widgets
        def _bind_mousewheel(event=None):
            try:
                canvas.bind_all('<MouseWheel>', _on_mousewheel_windows)
                canvas.bind_all('<Button-4>', _on_mousewheel_linux)
                canvas.bind_all('<Button-5>', _on_mousewheel_linux)
            except Exception:
                pass

        def _unbind_mousewheel(event=None):
            try:
                canvas.unbind_all('<MouseWheel>')
                canvas.unbind_all('<Button-4>')
                canvas.unbind_all('<Button-5>')
            except Exception:
                pass

        # When mouse enters the canvas area, enable wheel scrolling; disable when it leaves
        canvas.bind('<Enter>', _bind_mousewheel)
        canvas.bind('<Leave>', _unbind_mousewheel)

        # Initialize scrollregion after widgets are created — we'll call update_idletasks later to ensure sizes are known
        
        # Header
        self.create_header(main_frame)
        
        # Stats cards row
        self.create_stats_section(main_frame)
        
        # Main content area
        content_frame = ttk.Frame(main_frame, style='Card.TFrame')
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(20, 0))
        
        # Left panel (controls) - Fixed width
        left_panel = ttk.Frame(content_frame, style='Card.TFrame')
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_panel.configure(width=280)  # Reduced width
        left_panel.pack_propagate(False)
        
        self.create_controls_panel(left_panel)
        
        # Center panel (charts) - Fixed width to prevent expansion
        center_panel = ttk.Frame(content_frame, style='Card.TFrame')
        center_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        center_panel.configure(width=700)  # Fixed width to contain charts
        
        self.create_charts_panel(center_panel)
        
        # Right panel (insights & table) - Fixed width
        right_panel = ttk.Frame(content_frame, style='Card.TFrame')
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH)
        right_panel.configure(width=350)  # Reduced width
        right_panel.pack_propagate(False)
        
        self.create_insights_panel(right_panel)
        # Ensure the canvas scrollregion covers the whole inner content now that UI is built
        try:
            # let geometry settle
            self.root.update_idletasks()
            self._main_canvas.configure(scrollregion=self._main_canvas.bbox('all'))
        except Exception:
            pass
        
    def create_header(self, parent):
        header_frame = ttk.Frame(parent, style='Card.TFrame')
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Title with emoji and gradient effect simulation
        title_frame = ttk.Frame(header_frame, style='Card.TFrame')
        title_frame.pack()
        
        title_label = tk.Label(title_frame, 
                              text="💰 Transaction Analyzer Pro",
                              font=('Inter', 28, 'bold'),
                              fg=self.colors['primary'],
                              bg=self.colors['white'])
        title_label.pack()
        
        subtitle_label = tk.Label(title_frame,
                                text="Advanced financial analytics with beautiful visualizations",
                                font=('Inter', 12),
                                fg=self.colors['muted'],
                                bg=self.colors['white'])
        subtitle_label.pack(pady=(5, 0))
        
    def create_stats_section(self, parent):
        stats_frame = ttk.Frame(parent, style='Card.TFrame')
        stats_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Create 5 stat cards with proper spacing
        self.stat_vars = {
            'income': tk.StringVar(value="$0.00"),
            'expenses': tk.StringVar(value="$0.00"), 
            'net': tk.StringVar(value="$0.00"),
            'transactions': tk.StringVar(value="0"),
            'categories': tk.StringVar(value="0")
        }
        
        stats_data = [
            ("📈", "Total Income", self.stat_vars['income'], self.colors['success']),
            ("📉", "Total Expenses", self.stat_vars['expenses'], self.colors['danger']),
            ("💰", "Net Income", self.stat_vars['net'], self.colors['primary']),
            ("🧾", "Transactions", self.stat_vars['transactions'], self.colors['info']),
            ("📊", "Categories", self.stat_vars['categories'], self.colors['secondary'])
        ]
        
        for i, (icon, label, var, color) in enumerate(stats_data):
            card_frame = tk.Frame(stats_frame, bg=self.colors['white'], 
                                 relief='solid', bd=1, padx=15, pady=15)
            card_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
            
            # Icon
            icon_label = tk.Label(card_frame, text=icon, font=('Inter', 24),
                                 bg=self.colors['white'], fg=color)
            icon_label.pack()
            
            # Value (larger font, better spacing)
            value_label = tk.Label(card_frame, textvariable=var,
                                  font=('Inter', 16, 'bold'),
                                  bg=self.colors['white'], fg=color)
            value_label.pack(pady=(5, 2))
            
            # Label
            label_widget = tk.Label(card_frame, text=label,
                                   font=('Inter', 10),
                                   bg=self.colors['white'], fg=self.colors['muted'])
            label_widget.pack()
            
    def create_controls_panel(self, parent):
        # File operations
        file_frame = ttk.LabelFrame(parent, text="📁 Data Management", padding=15)
        file_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Button(file_frame, text="📤 Upload CSV", style='Primary.TButton',
                  command=self.upload_csv).pack(fill=tk.X, pady=2)
        
        ttk.Button(file_frame, text="🎲 Load Sample Data", style='Success.TButton',
                  command=self.load_sample_data).pack(fill=tk.X, pady=2)
        
        ttk.Button(file_frame, text="💾 Export Data", 
                  command=self.export_data).pack(fill=tk.X, pady=2)
        
        # Filters
        filter_frame = ttk.LabelFrame(parent, text="🔍 Filters", padding=15)
        filter_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Date range
        tk.Label(filter_frame, text="📅 Date Range:", font=('Inter', 10, 'bold')).pack(anchor=tk.W)
        
        date_frame = ttk.Frame(filter_frame)
        date_frame.pack(fill=tk.X, pady=5)
        
        self.date_from = ttk.Entry(date_frame, width=12)
        self.date_from.pack(side=tk.LEFT, padx=(0, 5))
        self.date_from.insert(0, "2024-01-01")
        
        tk.Label(date_frame, text="to").pack(side=tk.LEFT, padx=5)
        
        self.date_to = ttk.Entry(date_frame, width=12)
        self.date_to.pack(side=tk.LEFT, padx=(5, 0))
        self.date_to.insert(0, "2024-12-31")
        
        # Search
        tk.Label(filter_frame, text="🔎 Search:", font=('Inter', 10, 'bold')).pack(anchor=tk.W, pady=(10, 0))
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(filter_frame, textvariable=self.search_var)
        search_entry.pack(fill=tk.X, pady=5)
        
        # Filter buttons
        button_frame = ttk.Frame(filter_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="Apply", command=self.apply_filters).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Clear", command=self.clear_filters).pack(side=tk.LEFT)
        
    def create_charts_panel(self, parent):
        # Chart notebook for multiple tabs
        self.chart_notebook = ttk.Notebook(parent)
        self.chart_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Monthly overview tab
        monthly_frame = ttk.Frame(self.chart_notebook)
        self.chart_notebook.add(monthly_frame, text="📊 Monthly Overview")
        
        # Create frame for monthly chart
        monthly_chart_frame = ttk.Frame(monthly_frame)
        monthly_chart_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Initialize monthly chart
        self.setup_monthly_chart(monthly_chart_frame)
        
        # Category breakdown tab
        category_frame = ttk.Frame(self.chart_notebook)
        self.chart_notebook.add(category_frame, text="🥧 Categories")
        
        # Create frame for category chart
        category_chart_frame = ttk.Frame(category_frame)
        category_chart_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Initialize category chart
        self.setup_category_chart(category_chart_frame)
        
        # Trends tab
        trends_frame = ttk.Frame(self.chart_notebook)
        self.chart_notebook.add(trends_frame, text="📈 Trends")
        
        # Create frame for trends chart
        trends_chart_frame = ttk.Frame(trends_frame)
        trends_chart_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Initialize trends chart
        self.setup_trends_chart(trends_chart_frame)
        
    def setup_monthly_chart(self, parent):
        """Setup monthly chart with proper isolation"""
        # Destroy any existing canvas
        for widget in parent.winfo_children():
            widget.destroy()
            
        # Create new figure with better size management
        self.monthly_fig = plt.Figure(figsize=(7, 4), facecolor='white', tight_layout=True)
        self.monthly_ax = self.monthly_fig.add_subplot(111)
        
        # Create canvas
        self.monthly_canvas = FigureCanvasTkAgg(self.monthly_fig, parent)
        self.monthly_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Add hover functionality
        self.setup_monthly_hover()
        
        # Initialize with empty chart
        self.monthly_ax.text(0.5, 0.5, 'Load data to view chart', 
                           horizontalalignment='center', verticalalignment='center',
                           transform=self.monthly_ax.transAxes, fontsize=12)
        self.monthly_canvas.draw()
        
    def setup_category_chart(self, parent):
        """Setup category chart with proper isolation"""
        # Destroy any existing canvas
        for widget in parent.winfo_children():
            widget.destroy()
            
        # Create new figure with better size management
        self.category_fig = plt.Figure(figsize=(7, 4), facecolor='white', tight_layout=True)
        self.category_ax = self.category_fig.add_subplot(111)
        
        # Create canvas
        self.category_canvas = FigureCanvasTkAgg(self.category_fig, parent)
        self.category_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Add hover functionality
        self.setup_category_hover()
        
        # Initialize with empty chart
        self.category_ax.text(0.5, 0.5, 'Load data to view chart', 
                            horizontalalignment='center', verticalalignment='center',
                            transform=self.category_ax.transAxes, fontsize=12)
        self.category_canvas.draw()
        
    def setup_trends_chart(self, parent):
        """Setup trends chart with proper isolation"""
        # Destroy any existing canvas
        for widget in parent.winfo_children():
            widget.destroy()
            
        # Create new figure with better size management
        self.trends_fig = plt.Figure(figsize=(7, 4), facecolor='white', tight_layout=True)
        self.trends_ax = self.trends_fig.add_subplot(111)
        
        # Create canvas
        self.trends_canvas = FigureCanvasTkAgg(self.trends_fig, parent)
        self.trends_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Add hover functionality
        self.setup_trends_hover()
        
        # Add crosshair cursor for better interaction
        self.trends_cursor = Cursor(self.trends_ax, useblit=True, color='gray', linewidth=0.5, alpha=0.7)
        
        # Initialize with empty chart
        self.trends_ax.text(0.5, 0.5, 'Load data to view chart', 
                          horizontalalignment='center', verticalalignment='center',
                          transform=self.trends_ax.transAxes, fontsize=12)
        self.trends_canvas.draw()
        
    def create_insights_panel(self, parent):
        # Insights
        insights_frame = ttk.LabelFrame(parent, text="💡 Financial Insights", padding=15)
        insights_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.insights_text = tk.Text(insights_frame, height=8, width=40, wrap=tk.WORD,
                                    font=('Inter', 9), bg='#f8fafc', relief='flat')
        insights_scrollbar = ttk.Scrollbar(insights_frame, orient="vertical", command=self.insights_text.yview)
        self.insights_text.configure(yscrollcommand=insights_scrollbar.set)
        
        self.insights_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        insights_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Transaction table
        table_frame = ttk.LabelFrame(parent, text="📋 Recent Transactions", padding=15)
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create treeview with better column sizing
        columns = ("Date", "Description", "Amount", "Category")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=12)
        
        # Configure columns with proper widths
        self.tree.heading("Date", text="Date")
        self.tree.column("Date", width=60, anchor=tk.CENTER)
        
        self.tree.heading("Description", text="Description")
        self.tree.column("Description", width=120, anchor=tk.W)
        
        self.tree.heading("Amount", text="Amount")
        self.tree.column("Amount", width=120, anchor=tk.E)
        
        self.tree.heading("Category", text="Category")
        self.tree.column("Category", width=80, anchor=tk.CENTER)
        
        # Scrollbars for table
        tree_scroll_y = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        tree_scroll_x = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        
    def create_sample_data(self):
        """Create realistic sample transaction data with some missing values for cleaning demonstration"""
        data = [
            {"Date": "2024-01-16", "Description": "Starbucks Coffee", "Amount": -5.75, "Category": "Food & Dining", "Account": "Credit Card"},
            {"Date": "2024-01-17", "Description": "Whole Foods Market", "Amount": -127.83, "Category": "Groceries", "Account": "Checking"},
            {"Date": "2024-01-18", "Description": "Netflix Subscription", "Amount": -15.99, "Category": "Entertainment", "Account": "Credit Card"},
            {"Date": None, "Description": "Bad Date Transaction", "Amount": -10.50, "Category": "Food & Dining", "Account": "Cash"},  # NaN date for cleaning
            {"Date": "2024-01-20", "Description": "Freelance Payment", "Amount": 1200.00, "Category": "Income", "Account": "Checking"},
            {"Date": "2024-01-21", "Description": "Electric Bill", "Amount": None, "Category": "Utilities", "Account": "Checking"},  # NaN amount
            {"Date": "2024-01-23", "Description": "Amazon Purchase", "Amount": -67.99, "Category": "Shopping", "Account": "Credit Card"},
            {"Date": "2024-01-24", "Description": "Stock Dividend", "Amount": 85.50, "Category": "Investment", "Account": "Investment"},
            {"Date": "2024-01-25", "Description": "Uber Ride", "Amount": -18.75, "Category": "Transportation", "Account": "Credit Card"},
            {"Date": "2024-01-28", "Description": "Gym Membership", "Amount": -49.99, "Category": "Health & Fitness", "Account": "Checking"},
            {"Date": "2024-02-01", "Description": "Salary Deposit", "Amount": 4500.00, "Category": "Salary", "Account": "Checking"},
            {"Date": "2024-02-02", "Description": "Rent Payment", "Amount": -1800.00, "Category": "Housing", "Account": "Checking"},
            {"Date": "2024-02-03", "Description": "Pharmacy", "Amount": -23.67, "Category": "Health", "Account": "Credit Card"},
            {"Date": "2024-02-05", "Description": "Gas Station", "Amount": -45.32, "Category": "Transportation", "Account": "Credit Card"},
            {"Date": "2024-02-08", "Description": "Restaurant", "Amount": -78.45, "Category": "Food & Dining", "Account": "Credit Card"},
            {"Date": "2024-02-10", "Description": "Freelance Project", "Amount": 650.00, "Category": "Income", "Account": "Checking"},
            {"Date": "2024-02-12", "Description": "Spotify Premium", "Amount": -9.99, "Category": "Entertainment", "Account": "Credit Card"},
            {"Date": "2024-02-15", "Description": "Grocery Shopping", "Amount": -89.23, "Category": "Groceries", "Account": "Checking"},
            {"Date": "2024-02-18", "Description": "Investment Return", "Amount": 234.67, "Category": "Investment", "Account": "Investment"},
            {"Date": "2024-03-01", "Description": "Salary Deposit", "Amount": 4500.00, "Category": "Salary", "Account": "Checking"},
            {"Date": "2024-03-02", "Description": "Rent Payment", "Amount": -1800.00, "Category": "Housing", "Account": "Checking"},
            {"Date": "2024-03-05", "Description": "Costco Shopping", "Amount": -156.78, "Category": "Groceries", "Account": "Credit Card"},
            {"Date": "2024-03-08", "Description": "Movie Theater", "Amount": -28.50, "Category": "Entertainment", "Account": "Credit Card"},
            {"Date": "2024-03-12", "Description": "Car Repair", "Amount": -450.00, "Category": "Transportation", "Account": "Checking"},
            {"Date": "2024-03-15", "Description": "Bonus Payment", "Amount": 800.00, "Category": "Income", "Account": "Checking"},
        ]
        
        df = pd.DataFrame(data)
        return self.clean_transaction_data(df)
        
    def update_all_displays(self):
        """Update all UI elements with current data"""
        self.update_stats()
        self.update_charts()
        self.update_table()
        self.update_insights()
        
    def update_stats(self):
        """Update the statistics cards with proper formatting"""
        df = self.filtered_df
        
        total_income = df[df['Amount'] > 0]['Amount'].sum()
        total_expenses = abs(df[df['Amount'] < 0]['Amount'].sum())
        net_income = total_income - total_expenses
        num_transactions = len(df)
        num_categories = df['Category'].nunique()
        
        # Update with better formatting and no overlap
        self.stat_vars['income'].set(f"${total_income:,.2f}")
        self.stat_vars['expenses'].set(f"${total_expenses:,.2f}")
        self.stat_vars['net'].set(f"${net_income:,.2f}")
        self.stat_vars['transactions'].set(f"{num_transactions:,}")
        self.stat_vars['categories'].set(f"{num_categories}")
        
    def update_charts(self):
        """Update all charts with modern styling"""
        # Clear each axis completely and redraw
        try:
            self.monthly_ax.clear()
            self.category_ax.clear()
            self.trends_ax.clear()
            
            # Update individual charts
            self.update_monthly_chart()
            self.update_category_chart()
            self.update_trends_chart()
            
        except Exception as e:
            print(f"Error updating charts: {e}")
            # Reinitialize charts if there's an error
            self.reinitialize_charts()
    
    def reinitialize_charts(self):
        """Reinitialize all charts from scratch"""
        try:
            # Get the parent frames
            monthly_parent = self.monthly_canvas.get_tk_widget().master
            category_parent = self.category_canvas.get_tk_widget().master
            trends_parent = self.trends_canvas.get_tk_widget().master
            
            # Reinitialize each chart with hover functionality
            self.setup_monthly_chart(monthly_parent)
            self.setup_category_chart(category_parent)
            self.setup_trends_chart(trends_parent)
            
            # Update with current data
            self.update_monthly_chart()
            self.update_category_chart()
            self.update_trends_chart()
            
        except Exception as e:
            print(f"Error reinitializing charts: {e}")
        
    def update_monthly_chart(self):
        """Create beautiful monthly income vs expenses chart"""
        df = self.filtered_df.copy()
        if len(df) == 0:
            self.monthly_ax.text(0.5, 0.5, 'No data available', 
                               horizontalalignment='center', verticalalignment='center',
                               transform=self.monthly_ax.transAxes, fontsize=14)
            self.monthly_canvas.draw()
            return
        
        # Check if Date column exists and is properly formatted
        if 'Date' not in df.columns:
            self.monthly_ax.text(0.5, 0.5, 'Date column not found', 
                               horizontalalignment='center', verticalalignment='center',
                               transform=self.monthly_ax.transAxes, fontsize=14)
            self.monthly_canvas.draw()
            return
            
        # Ensure Date column is datetime
        try:
            df['Date'] = pd.to_datetime(df['Date'])
        except:
            self.monthly_ax.text(0.5, 0.5, 'Invalid date format', 
                               horizontalalignment='center', verticalalignment='center',
                               transform=self.monthly_ax.transAxes, fontsize=14)
            self.monthly_canvas.draw()
            return
            
        df_indexed = df.set_index('Date')
        
        # Monthly aggregation
        monthly_income = df_indexed[df_indexed['Amount'] > 0]['Amount'].resample('M').sum()
        monthly_expenses = abs(df_indexed[df_indexed['Amount'] < 0]['Amount'].resample('M').sum())
        
        if len(monthly_income) > 0 and len(monthly_expenses) > 0:
            # Ensure both series have the same index
            all_months = monthly_income.index.union(monthly_expenses.index)
            monthly_income = monthly_income.reindex(all_months, fill_value=0)
            monthly_expenses = monthly_expenses.reindex(all_months, fill_value=0)
            
            # Store data for hover functionality
            self.monthly_months = [d.strftime('%b %Y') for d in all_months]
            
            x = np.arange(len(all_months))
            width = 0.35
            
            # Create beautiful bars and store references
            self.monthly_income_bars = self.monthly_ax.bar(x - width/2, monthly_income.values, width, 
                                       label='Income', color=self.colors['success'], 
                                       alpha=0.8, edgecolor='white', linewidth=2)
            self.monthly_expense_bars = self.monthly_ax.bar(x + width/2, monthly_expenses.values, width,
                                       label='Expenses', color=self.colors['danger'],
                                       alpha=0.8, edgecolor='white', linewidth=2)
            
            # ... existing code ...
            
            # Add value labels on bars
            for bar in self.monthly_income_bars:
                height = bar.get_height()
                if height > 0:
                    self.monthly_ax.annotate(f'${height:,.0f}',
                                           xy=(bar.get_x() + bar.get_width() / 2, height),
                                           xytext=(0, 3), textcoords="offset points",
                                           ha='center', va='bottom', fontsize=8, fontweight='bold')
            
            for bar in self.monthly_expense_bars:
                height = bar.get_height()
                if height > 0:
                    self.monthly_ax.annotate(f'${height:,.0f}',
                                           xy=(bar.get_x() + bar.get_width() / 2, height),
                                           xytext=(0, 3), textcoords="offset points",
                                           ha='center', va='bottom', fontsize=8, fontweight='bold')
            
            self.monthly_ax.set_xticks(x)
            self.monthly_ax.set_xticklabels(self.monthly_months, rotation=0)
            
            self.monthly_ax.set_title('Monthly Income vs Expenses', fontsize=12, fontweight='bold', pad=10)
            self.monthly_ax.set_ylabel('Amount ($)', fontweight='bold')
            self.monthly_ax.legend(frameon=True, loc='upper left')
            self.monthly_ax.grid(True, alpha=0.3, linestyle='--')
            self.monthly_ax.spines['top'].set_visible(False)
            self.monthly_ax.spines['right'].set_visible(False)
        
        # Ensure tight layout and redraw
        self.monthly_fig.tight_layout()
        self.monthly_canvas.draw()
        self.monthly_canvas.flush_events()
        
    def update_category_chart(self):
        """Create beautiful enhanced category breakdown pie chart"""
        self.category_ax.clear()
        
        expenses = self.filtered_df[self.filtered_df['Amount'] < 0]
        if len(expenses) > 0:
            category_spending = expenses.groupby('Category')['Amount'].sum().abs().sort_values(ascending=False)
            
            # Take top 6 categories and combine others for better readability
            top_categories = category_spending.head(6)
            others = category_spending.iloc[6:].sum()
            if others > 0:
                top_categories['Others'] = others
            
            # Store data for hover functionality
            self.category_data = top_categories
            
            # Enhanced beautiful colors with better contrast
            colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FECA57', '#FF9FF3', '#54A0FF', '#5F27CD']
            colors = colors[:len(top_categories)]
            
            # Create enhanced pie chart with modern styling and store wedge references
            self.category_wedges, texts, autotexts = self.category_ax.pie(
                top_categories.values, 
                labels=top_categories.index,
                autopct=lambda pct: f'${top_categories.values[int(pct/100*len(top_categories))]:.0f}\n({pct:.1f}%)',
                colors=colors,
                startangle=90,
                wedgeprops=dict(width=0.8, edgecolor='white', linewidth=3),
                textprops={'fontsize': 9, 'fontweight': 'bold'},
                pctdistance=0.85,
                labeldistance=1.1
            )
            
            # Enhance text appearance with better positioning
            for i, (text, autotext) in enumerate(zip(texts, autotexts)):
                text.set_fontsize(8)
                text.set_fontweight('bold')
                autotext.set_color('white')
                autotext.set_fontweight('bold')
                autotext.set_fontsize(7)
                
            # Add a circle at the center for donut effect
            centre_circle = plt.Circle((0,0), 0.40, fc='white', linewidth=2, edgecolor='#E8E8E8')
            self.category_ax.add_artist(centre_circle)
            
            # Add center text with total
            total_expenses = top_categories.sum()
            self.category_ax.text(0, 0, f'Total\n${total_expenses:,.0f}', 
                                horizontalalignment='center', verticalalignment='center',
                                fontsize=10, fontweight='bold', color='#2C3E50')
        else:
            self.category_ax.text(0.5, 0.5, 'No expense data available', 
                                horizontalalignment='center', verticalalignment='center',
                                transform=self.category_ax.transAxes, fontsize=12)
        
        self.category_ax.set_title('💸 Expense Distribution by Category', fontsize=12, fontweight='bold', pad=15)
        
        # Ensure tight layout and redraw
        self.category_fig.tight_layout()
        self.category_canvas.draw()
        self.category_canvas.flush_events()
        

    def demonstrate_pandas_concepts(self):
        """
        Demonstrate all required pandas concepts
        """
        print("\n" + "="*80)
        print("🐼 PANDAS CONCEPTS DEMONSTRATION")
        print("="*80)
        
        # 1. Monthly analysis using groupby
        monthly_totals, monthly_category, account_analysis = self.calculate_monthly_analysis()
        
        # 2. Rolling averages with datetime indexing
        rolling_data = self.calculate_rolling_averages()
        
        # 3. Top spending categories
        top_categories = self.identify_top_spending_categories()
        
        # 4. DataFrame merging
        budget_comparison = self.merge_with_budget_data()
        
        print("="*80)
        print("✅ All pandas concepts demonstrated!")
        print("="*80 + "\n")
        
        return {
            'monthly_totals': monthly_totals,
            'monthly_category': monthly_category,
            'rolling_data': rolling_data,
            'top_categories': top_categories,
            'budget_comparison': budget_comparison
        }
        
    def update_trends_chart(self):
        """Create enhanced spending trends over time with rolling averages and statistics"""
        self.trends_ax.clear()
        
        df = self.filtered_df.copy()
        
        # Check if Date column exists and has data
        if len(df) == 0 or 'Date' not in df.columns:
            self.trends_ax.text(0.5, 0.5, 'No data available', 
                              horizontalalignment='center', verticalalignment='center',
                              transform=self.trends_ax.transAxes, fontsize=12)
            self.trends_canvas.draw()
            self.trends_canvas.flush_events()
            return
        
        # Ensure Date column is datetime
        try:
            df['Date'] = pd.to_datetime(df['Date'])
        except:
            self.trends_ax.text(0.5, 0.5, 'Invalid date format', 
                              horizontalalignment='center', verticalalignment='center',
                              transform=self.trends_ax.transAxes, fontsize=12)
            self.trends_canvas.draw()
            self.trends_canvas.flush_events()
            return
            
        df_indexed = df.set_index('Date')
        
        # Daily spending (expenses only)
        daily_spending = abs(df_indexed[df_indexed['Amount'] < 0]['Amount'].resample('D').sum())
        
        # Store data for hover functionality
        self.trends_data = daily_spending
        
        if len(daily_spending) > 0:
            # Enhanced plot with gradient fill
            self.trends_ax.fill_between(daily_spending.index, daily_spending.values, 
                                       alpha=0.3, color='#FF6B6B', label='Daily Spending')
            self.trends_ax.plot(daily_spending.index, daily_spending.values, 
                               color='#FF6B6B', linewidth=2, alpha=0.8, marker='o', markersize=3)
            
            # Calculate and plot multiple rolling averages
            rolling_stats = {}
            
            if len(daily_spending) >= 7:
                ma7 = daily_spending.rolling(7, min_periods=1).mean()
                rolling_stats['7-day'] = ma7.iloc[-1] if len(ma7) > 0 else 0
                self.trends_ax.plot(daily_spending.index, ma7.values, 
                                   color='#4ECDC4', linewidth=3, 
                                   linestyle='-', label=f'7-Day Avg: ${rolling_stats["7-day"]:.2f}', alpha=0.9)
            
            if len(daily_spending) >= 14:
                ma14 = daily_spending.rolling(14, min_periods=1).mean()
                rolling_stats['14-day'] = ma14.iloc[-1] if len(ma14) > 0 else 0
                self.trends_ax.plot(daily_spending.index, ma14.values, 
                                   color='#45B7D1', linewidth=3, 
                                   linestyle='--', label=f'14-Day Avg: ${rolling_stats["14-day"]:.2f}', alpha=0.9)
            
            if len(daily_spending) >= 30:
                ma30 = daily_spending.rolling(30, min_periods=1).mean()
                rolling_stats['30-day'] = ma30.iloc[-1] if len(ma30) > 0 else 0
                self.trends_ax.plot(daily_spending.index, ma30.values, 
                                   color='#96CEB4', linewidth=3, 
                                   linestyle='-.', label=f'30-Day Avg: ${rolling_stats["30-day"]:.2f}', alpha=0.9)
            
            # Add statistical information as text
            stats_text = self.calculate_spending_stats(daily_spending, rolling_stats)
            
            # Position stats text in the upper right
            self.trends_ax.text(0.98, 0.98, stats_text, 
                              transform=self.trends_ax.transAxes,
                              fontsize=8, fontweight='bold',
                              verticalalignment='top', horizontalalignment='right',
                              bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.8, edgecolor='gray'))
            
            # Enhanced legend with better positioning
            legend = self.trends_ax.legend(loc='upper left', frameon=True, fancybox=True, shadow=True)
            legend.get_frame().set_facecolor('white')
            legend.get_frame().set_alpha(0.9)
            
            # Add grid for better readability
            self.trends_ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
            
        else:
            self.trends_ax.text(0.5, 0.5, 'No spending data available', 
                              horizontalalignment='center', verticalalignment='center',
                              transform=self.trends_ax.transAxes, fontsize=12)
        
        self.trends_ax.set_title('📈 Daily Spending Trends with Rolling Averages', fontsize=12, fontweight='bold', pad=15)
        self.trends_ax.set_ylabel('Amount ($)', fontweight='bold')
        self.trends_ax.spines['top'].set_visible(False)
        self.trends_ax.spines['right'].set_visible(False)
        
        # Ensure tight layout and redraw
        self.trends_fig.tight_layout()
        self.trends_canvas.draw()
        self.trends_canvas.flush_events()
    
    def setup_monthly_hover(self):
        """Setup hover functionality for monthly chart"""
        def on_hover_monthly(event):
            if event.inaxes == self.monthly_ax:
                # Find the closest bar
                for i, (income_bar, expense_bar) in enumerate(zip(self.monthly_income_bars, self.monthly_expense_bars)):
                    if income_bar.contains(event)[0]:
                        # Show income value
                        value = income_bar.get_height()
                        month = self.monthly_months[i] if hasattr(self, 'monthly_months') else f"Month {i+1}"
                        self.show_tooltip(event.x, event.y, f"{month}\nIncome: ${value:,.2f}")
                        return
                    elif expense_bar.contains(event)[0]:
                        # Show expense value
                        value = expense_bar.get_height()
                        month = self.monthly_months[i] if hasattr(self, 'monthly_months') else f"Month {i+1}"
                        self.show_tooltip(event.x, event.y, f"{month}\nExpenses: ${value:,.2f}")
                        return
                self.hide_tooltip()
            else:
                self.hide_tooltip()
        
        self.monthly_canvas.mpl_connect('motion_notify_event', on_hover_monthly)
    
    def setup_category_hover(self):
        """Setup hover functionality for category pie chart"""
        def on_hover_category(event):
            if event.inaxes == self.category_ax and hasattr(self, 'category_wedges'):
                for i, wedge in enumerate(self.category_wedges):
                    if wedge.contains(event)[0]:
                        # Get category and value
                        category = list(self.category_data.index)[i] if hasattr(self, 'category_data') else f"Category {i+1}"
                        value = list(self.category_data.values)[i] if hasattr(self, 'category_data') else 0
                        percentage = (value / self.category_data.sum() * 100) if hasattr(self, 'category_data') else 0
                        self.show_tooltip(event.x, event.y, f"{category}\n${value:,.2f} ({percentage:.1f}%)")
                        return
                self.hide_tooltip()
            else:
                self.hide_tooltip()
        
        self.category_canvas.mpl_connect('motion_notify_event', on_hover_category)
    
    def setup_trends_hover(self):
        """Setup hover functionality for trends chart"""
        def on_hover_trends(event):
            if event.inaxes == self.trends_ax and hasattr(self, 'trends_data'):
                if event.xdata is not None and event.ydata is not None:
                    # Find closest data point
                    try:
                        x_date = mdates.num2date(event.xdata)
                        closest_date = min(self.trends_data.index, key=lambda x: abs((x - x_date.replace(tzinfo=None)).total_seconds()))
                        
                        # Get values for that date
                        daily_value = self.trends_data.loc[closest_date] if closest_date in self.trends_data.index else 0
                        
                        # Format date nicely
                        date_str = closest_date.strftime('%Y-%m-%d')
                        self.show_tooltip(event.x, event.y, f"{date_str}\nDaily Spending: ${daily_value:.2f}")
                        return
                    except:
                        pass
                self.hide_tooltip()
            else:
                self.hide_tooltip()
        
        self.trends_canvas.mpl_connect('motion_notify_event', on_hover_trends)
    
    def show_tooltip(self, x, y, text):
        """Show tooltip at specified position"""
        if hasattr(self, 'tooltip'):
            self.tooltip.destroy()
        
        self.tooltip = tk.Toplevel(self.root)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x+10}+{y+10}")
        
        label = tk.Label(self.tooltip, text=text, 
                        background='#2C3E50', foreground='white',
                        font=('Inter', 9, 'bold'), padx=8, pady=4,
                        relief='solid', borderwidth=1)
        label.pack()
        
        # Auto-hide tooltip after 3 seconds
        self.root.after(3000, self.hide_tooltip)
    
    def hide_tooltip(self):
        """Hide tooltip if it exists"""
        if hasattr(self, 'tooltip'):
            self.tooltip.destroy()
            delattr(self, 'tooltip')
    
    def calculate_spending_stats(self, daily_spending, rolling_stats):
        """Calculate comprehensive spending statistics for display"""
        stats_lines = []
        
        # Basic statistics
        total_spending = daily_spending.sum()
        avg_daily = daily_spending.mean()
        max_day = daily_spending.max()
        min_day = daily_spending[daily_spending > 0].min() if (daily_spending > 0).any() else 0
        
        stats_lines.append(f"📊 SPENDING STATS")
        stats_lines.append(f"💰 Total: ${total_spending:,.0f}")
        stats_lines.append(f"📅 Daily Avg: ${avg_daily:.2f}")
        stats_lines.append(f"📈 Max Day: ${max_day:.2f}")
        stats_lines.append(f"📉 Min Day: ${min_day:.2f}")
        stats_lines.append("")
        
        # Rolling averages
        if rolling_stats:
            stats_lines.append("🔄 ROLLING AVERAGES:")
            for period, value in rolling_stats.items():
                stats_lines.append(f"• {period}: ${value:.2f}")
        
        return "\n".join(stats_lines)
        
    def update_insights(self):
        """Generate and display financial insights with pandas analysis"""
        self.insights_text.delete(1.0, tk.END)
        
        df = self.filtered_df
        if len(df) == 0:
            self.insights_text.insert(tk.END, "📊 No data to analyze\n\nLoad some transactions to see insights!")
            return
        
        insights = []
        
        # CASH FLOW ANALYSIS
        total_income = df[df['Amount'] > 0]['Amount'].sum()
        total_expenses = abs(df[df['Amount'] < 0]['Amount'].sum())
        net_cash_flow = total_income - total_expenses
        
        insights.append("💰 CASH FLOW ANALYSIS")
        insights.append("-" * 30)
        insights.append(f"📈 Cash Inflow: ${total_income:,.2f}")
        insights.append(f"📉 Cash Outflow: ${total_expenses:,.2f}")
        insights.append(f"🔄 Net Cash Flow: ${net_cash_flow:,.2f}")
        cash_flow_status = "Positive" if net_cash_flow > 0 else "Negative"
        insights.append(f"📊 Status: {cash_flow_status}")
        insights.append("")
        
        # TOP 3 SPENDING CATEGORIES
        expenses = df[df['Amount'] < 0].copy()
        if len(expenses) > 0:
            top_categories = expenses.groupby('Category')['Amount'].sum().abs().sort_values(ascending=False).head(3)
            insights.append("🏆 TOP 3 SPENDING CATEGORIES")
            insights.append("-" * 30)
            for i, (category, amount) in enumerate(top_categories.items()):
                pct = (amount / total_expenses) * 100
                insights.append(f"{i+1}. {category}: ${amount:,.2f} ({pct:.1f}%)")
            insights.append("")
        
        # EXPENSE CATEGORIZATION INSIGHTS
        category_stats = expenses.groupby('Category').agg({
            'Amount': ['count', 'sum', 'mean']
        }).round(2) if len(expenses) > 0 else pd.DataFrame()
        
        if not category_stats.empty:
            insights.append("📊 EXPENSE CATEGORIZATION")
            insights.append("-" * 30)
            insights.append(f"📋 Categories: {len(category_stats)}")
            insights.append(f"🔢 Total Transactions: {len(expenses)}")
            insights.append(f"💵 Average Transaction: ${expenses['Amount'].abs().mean():.2f}")
            insights.append("")
        
        # ROLLING AVERAGE ANALYSIS WITH DETAILED STATS
        if len(df) >= 7:
            df_sorted = df.sort_values('Date')
            
            # Calculate rolling averages for expenses with error handling
            try:
                # Ensure Date column is datetime
                df_sorted['Date'] = pd.to_datetime(df_sorted['Date'])
                
                # Create a copy with Date as index for resampling
                df_expenses = df_sorted[df_sorted['Amount'] < 0].copy()
                if len(df_expenses) > 0:
                    df_expenses['Amount'] = df_expenses['Amount'].abs()
                    df_expenses_indexed = df_expenses.set_index('Date')
                    daily_expenses = df_expenses_indexed['Amount'].resample('D').sum()
                else:
                    daily_expenses = pd.Series(dtype=float)
            except Exception as e:
                print(f"Error in rolling average calculation: {e}")
                daily_expenses = pd.Series(dtype=float)
            
            if len(daily_expenses) > 0:
                insights.append("📈 ROLLING AVERAGE ANALYSIS")
                insights.append("-" * 30)
                
                # 7-day rolling average
                if len(daily_expenses) >= 7:
                    ma7 = daily_expenses.rolling(7, min_periods=1).mean()
                    current_7day = ma7.iloc[-1]
                    previous_7day = ma7.iloc[-8] if len(ma7) >= 8 else ma7.iloc[0]
                    change_7day = current_7day - previous_7day
                    
                    insights.append(f"🔄 7-Day Rolling Avg: ${current_7day:.2f}")
                    trend_7 = "⬆️" if change_7day > 0 else "⬇️"
                    insights.append(f"   Week-over-week: {trend_7} ${abs(change_7day):.2f}")
                
                # 14-day rolling average
                if len(daily_expenses) >= 14:
                    ma14 = daily_expenses.rolling(14, min_periods=1).mean()
                    current_14day = ma14.iloc[-1]
                    insights.append(f"📅 14-Day Rolling Avg: ${current_14day:.2f}")
                
                # 30-day rolling average
                if len(daily_expenses) >= 30:
                    ma30 = daily_expenses.rolling(30, min_periods=1).mean()
                    current_30day = ma30.iloc[-1]
                    insights.append(f"📆 30-Day Rolling Avg: ${current_30day:.2f}")
                
                # Volatility analysis
                volatility = daily_expenses.rolling(7, min_periods=1).std().iloc[-1]
                insights.append(f"🌊 Spending Volatility: ${volatility:.2f}")
                
                # Spending consistency score
                consistency = 100 - (volatility / current_7day * 100) if current_7day > 0 else 0
                insights.append(f"🎯 Consistency Score: {consistency:.1f}%")
                
                insights.append("")
            
            # Weekly trend comparison
            recent_week = df_sorted.tail(7)['Amount'].sum()
            first_week = df_sorted.head(7)['Amount'].sum()
            
            insights.append("📈 WEEKLY TREND COMPARISON")
            insights.append("-" * 30)
            insights.append(f"💰 Recent Week Net: ${recent_week:.2f}")
            insights.append(f"📅 First Week Net: ${first_week:.2f}")
            
            if recent_week > first_week:
                insights.append("📊 Overall Trend: Improving ⬆️")
            else:
                insights.append("📊 Overall Trend: Declining ⬇️")
            
            # Monthly trend
            monthly_data = df.set_index('Date')['Amount'].resample('M').sum()
            if len(monthly_data) >= 2:
                trend = "Increasing ⬆️" if monthly_data.iloc[-1] > monthly_data.iloc[-2] else "Decreasing ⬇️"
                insights.append(f"📈 Monthly Trend: {trend}")
            
            insights.append("")
        
        # SPENDING PATTERN INSIGHTS
        expenses = df[df['Amount'] < 0].copy()
        if len(expenses) > 0:
            expenses['Amount'] = expenses['Amount'].abs()
            insights.append("🔍 SPENDING PATTERNS")
            insights.append("-" * 30)
            
            # Day of week analysis
            expenses['DayOfWeek'] = expenses['Date'].dt.day_name()
            daily_avg = expenses.groupby('DayOfWeek')['Amount'].mean()
            if len(daily_avg) > 0:
                highest_day = daily_avg.idxmax()
                lowest_day = daily_avg.idxmin()
                
                insights.append(f"📈 Highest Spending Day: {highest_day}")
                insights.append(f"   Average: ${daily_avg[highest_day]:.2f}")
                insights.append(f"📉 Lowest Spending Day: {lowest_day}")
                insights.append(f"   Average: ${daily_avg[lowest_day]:.2f}")
            
            # Transaction size analysis
            large_transactions = expenses[expenses['Amount'] > expenses['Amount'].quantile(0.9)]
            insights.append(f"💳 Large Transactions (>90%): {len(large_transactions)}")
            if len(large_transactions) > 0:
                insights.append(f"   Average Amount: ${large_transactions['Amount'].mean():.2f}")
        
        insight_text = '\n'.join(insights)
        self.insights_text.insert(tk.END, insight_text)
        
    def update_table(self):
        """Update transaction table with recent transactions"""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # Add recent transactions (last 20)
        recent_transactions = self.filtered_df.tail(20)
        for _, row in recent_transactions.iterrows():
            date_str = row['Date'].strftime('%m/%d')
            amount_str = f"${row['Amount']:,.2f}"
            description = row['Description'][:25] + "..." if len(row['Description']) > 25 else row['Description']
            
            # Color code by amount
            tag = 'income' if row['Amount'] > 0 else 'expense'
            
            self.tree.insert('', 0, values=(date_str, description, amount_str, row['Category']), tags=(tag,))
        
        # Configure tags for colored rows
        self.tree.tag_configure('income', foreground=self.colors['success'])
        self.tree.tag_configure('expense', foreground=self.colors['danger'])
        
    def upload_csv(self):
        """Upload and process CSV file with comprehensive pandas operations"""
        file_path = filedialog.askopenfilename(
            title="Select CSV file",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                print(f"\n📂 READING CSV: {file_path}")
                # READ CSV INTO DATAFRAME
                raw_df = pd.read_csv(file_path)
                print(f"Raw data shape: {raw_df.shape}")
                print(f"Columns: {list(raw_df.columns)}")
                
                # Check for required columns and suggest mappings
                required_cols = {'Date': ['date', 'transaction_date', 'trans_date', 'datetime'],
                               'Amount': ['amount', 'value', 'transaction_amount', 'sum'],
                               'Description': ['description', 'desc', 'memo', 'details', 'transaction_details'],
                               'Category': ['category', 'cat', 'type', 'expense_type']}
                
                # Auto-map column names
                column_mapping = {}
                for req_col, possible_names in required_cols.items():
                    if req_col not in raw_df.columns:
                        for col in raw_df.columns:
                            if col.lower() in [name.lower() for name in possible_names]:
                                column_mapping[col] = req_col
                                print(f"Auto-mapped '{col}' -> '{req_col}'")
                                break
                
                # Apply column mapping
                if column_mapping:
                    raw_df = raw_df.rename(columns=column_mapping)
                    print(f"Columns after mapping: {list(raw_df.columns)}")
                
                # CLEAN THE DATA - demonstrate data cleaning
                self.df = self.clean_transaction_data(raw_df)
                
                if len(self.df) == 0:
                    messagebox.showerror("Error", "No valid data found after cleaning. Please check your CSV format.")
                    return
                
                self.filtered_df = self.df.copy()
                
                # Clear existing charts before updating
                try:
                    self.monthly_ax.clear()
                    self.category_ax.clear()
                    self.trends_ax.clear()
                except:
                    # If axes don't exist, reinitialize
                    self.reinitialize_charts()
                
                # DEMONSTRATE PANDAS CONCEPTS
                self.demonstrate_pandas_concepts()
                
                # Update all displays
                self.update_all_displays()
                messagebox.showinfo("Success", f"Successfully loaded and analyzed {len(self.df)} transactions!\n\nCheck console for detailed pandas analysis.")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load CSV: {str(e)}")
                print(f"Error details: {e}")
    
    def load_sample_data(self):
        """Load sample data"""
        self.df = self.create_sample_data()
        self.filtered_df = self.df.copy()
        
        # Clear existing charts before updating
        try:
            self.monthly_ax.clear()
            self.category_ax.clear()
            self.trends_ax.clear()
        except:
            # If axes don't exist, reinitialize
            self.reinitialize_charts()
        
        # Run financial analysis demonstrations
        self.demonstrate_pandas_concepts()
        
        self.update_all_displays()
        messagebox.showinfo("Sample Data", "Sample transaction data loaded successfully!")
    
    def export_data(self):
        """Export current filtered data to CSV"""
        if len(self.filtered_df) == 0:
            messagebox.showwarning("No Data", "No data to export")
            return
            
        file_path = filedialog.asksaveasfilename(
            title="Save CSV file",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                self.filtered_df.to_csv(file_path, index=False)
                messagebox.showinfo("Success", f"Data exported successfully to {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export: {str(e)}")
    
    def apply_filters(self):
        """Apply date and search filters"""
        try:
            filtered = self.df.copy()
            
            # Date filters
            date_from = self.date_from.get().strip()
            date_to = self.date_to.get().strip()
            
            if date_from:
                from_date = pd.to_datetime(date_from)
                filtered = filtered[filtered['Date'] >= from_date]
            
            if date_to:
                to_date = pd.to_datetime(date_to)
                filtered = filtered[filtered['Date'] <= to_date]
            
            # Search filter
            search_text = self.search_var.get().strip().lower()
            if search_text:
                mask = (
                    filtered['Description'].astype(str).str.lower().str.contains(search_text, na=False) |
                    filtered['Category'].astype(str).str.lower().str.contains(search_text, na=False)
                )
                filtered = filtered[mask]
            
            self.filtered_df = filtered
            self.update_all_displays()
            
            messagebox.showinfo("Filters Applied", f"Showing {len(self.filtered_df)} transactions")
            
        except Exception as e:
            messagebox.showerror("Filter Error", f"Error applying filters: {str(e)}")
    
    def clear_filters(self):
        """Clear all filters"""
        self.date_from.delete(0, tk.END)
        self.date_from.insert(0, "2024-01-01")
        self.date_to.delete(0, tk.END)
        self.date_to.insert(0, "2024-12-31")
        self.search_var.set("")
        
        self.filtered_df = self.df.copy()
        self.update_all_displays()
        messagebox.showinfo("Filters Cleared", "All filters have been cleared")

def main():
    """Main function to run the application"""
    root = tk.Tk()
    
    # Handle window closing properly
    def on_closing():
        try:
            plt.close('all')  # Close all matplotlib figures
        except:
            pass
        root.quit()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    app = ModernTransactionAnalyzer(root)
    
    # Add some style enhancements
    root.configure(bg='#f8fafc')
    
    # Make window resizable but set minimum size
    root.minsize(1200, 800)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        plt.close('all')

if __name__ == "__main__":
    main()