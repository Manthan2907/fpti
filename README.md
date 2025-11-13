# Ultimate Personal Finance Dashboard

## Overview
This project is a modern, full-featured personal finance dashboard built with Python and Tkinter. It provides a unified interface to track your cash, investments, real estate, credit cards, loans, and bank accounts, with persistent storage and real-world financial logic. The dashboard is designed for extensibility, beautiful UI, and practical daily use.

## Features
- **Unified Dashboard**: View cash, portfolio, net worth, loans, and recent transactions at a glance.
- **Bank Account Management**: Create bank accounts, deposit/withdraw, open fixed deposits (FDs), and take loans from specific accounts.
- **Portfolio Tracking**: Add, sell, and manage investments (stocks, funds, etc.) with real-time price updates (if yfinance is installed).
- **Real Estate**: Add, edit, and track properties as part of your net worth.
- **Credit Card Management**: Add, pay, and remove credit cards. Track balances, limits, and interest.
- **Loan Management**: Take loans from bank accounts, repay, and track interest.
- **Fixed Deposits (FDs)**: Open FDs from bank accounts, accrue interest, and track maturity.
- **Transaction Logging**: All actions (buy/sell, property, FD, loan, etc.) are logged and visible in the dashboard.
- **Budgeting & Goals**: Set, track, and visualize financial goals.
- **CSV Import/Export**: Upload sample data or export your portfolio.
- **Persistent Storage**: All data is saved in `finance_data.json` and restored on restart.
- **Modern UI**: Glassmorphism, color themes, and responsive layout for a premium experience.

## Sample Data Files
The project includes several CSV files for demo/testing:
- `1st.csv`
- `debt_tracking.csv`
- `family_budget.csv`
- `income_sources.csv`
- `investment_tracking.csv`
- `personal_finance_transcations.csv`
- `recurring_bills.csv`
- `student_budget.csv`
- `test_transactions.csv`
- `transactions_example.csv`

You can upload these via the dashboard to quickly populate the app with realistic data.

## How to Use
1. **Install Requirements**: Python 3.8+ and Tkinter. (Optional: `yfinance` for live stock prices, `pandas` for CSV support.)
2. **Run the App**: `python working.py`
3. **Explore Tabs**:
   - **Dashboard**: Overview of all finances.
   - **Expenses & Income**: Upload CSVs, add manual transactions.
   - **Portfolio**: Manage investments.
   - **Goals**: Set and track financial goals.
   - **Credit Cards**: Manage cards and payments.
   - **Bank Accounts**: Create accounts, open FDs, take loans.
   - **Real Estate**: Add and manage properties.
   - **Charts**: Visualize spending and cash flow.
   - **Bank Sync (Plaid)**: Placeholder for future real bank integration.
4. **Save & Restore**: All changes are saved automatically to `finance_data.json`.

## File Structure
- `working.py` — Main application file (Tkinter GUI, all logic)
- `finance_data.json` — Persistent data storage
- `*.csv` — Sample data files for import
- `README.md` — This documentation

## Extending & Reporting
- The code is modular and ready for further extension (AI insights, more analytics, cloud sync, etc.).
- You can upload this README to a notebook LLM/report generator for automated documentation or analysis.

## Screenshots
- (Add your own screenshots here for visual reference)

## License
MIT License. Free for personal and educational use.

---
**Created with ❤️ for real-world personal finance management.**


## Advanced Usage & Customization
- **Custom Themes**: Edit the `colors` dictionary in `working.py` to change the app’s look and feel.
- **Add New Asset Types**: Extend the `FinanceDashboard` class to support new financial products or analytics.
- **Integrate Real Bank Data**: The Plaid tab is a placeholder for future API integration. You can add Plaid or other APIs for real bank sync.
- **Automated Reports**: Use the built-in report generator or export data for analysis in Excel, Jupyter, or other tools.

## Troubleshooting
- **App Won’t Start**: Ensure Python 3.8+ and Tkinter are installed. Run `python working.py` from the project folder.
- **Data Not Saving**: Check write permissions for `finance_data.json`. All changes should save automatically.
- **Missing Features**: Some advanced features (live prices, Plaid sync) require optional packages or future updates.
- **UI Issues**: If the UI looks odd, try resizing the window or updating your Python/Tkinter installation.

## Contributing
Pull requests and suggestions are welcome! Please open an issue for bugs or feature requests. For major changes, discuss them first.

## Credits
- Inspired by real-world finance apps and dashboards.
- Uses open-source libraries: Tkinter, Pandas, Matplotlib, YFinance (optional).

## Contact
For questions or support, open an issue or contact the author via GitHub.
