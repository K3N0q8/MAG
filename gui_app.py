import sys
import time
import os # For checking environment variables

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QVBoxLayout,
    QWidget,
    QPushButton,
    QHBoxLayout,
    QGroupBox,
    QFormLayout,
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
    QTextEdit,
    QTabWidget,
    QMessageBox
)
from PyQt6.QtGui import QAction, QCloseEvent, QColor, QTextCursor
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QThread

# Add this at the top with other imports
# User needs to: pip install pyqtgraph
import pyqtgraph as pg

# Attempt to import bot components
try:
    from oanda_connector import OANDAConnector
    from strategy import Strategy
    from order_manager import OrderManager
except ImportError as e:
    print(f"Error: Failed to import one or more bot components: {e}")
    print("Please ensure oanda_connector.py, strategy.py, and order_manager.py are in the Python path.")
    # Define dummy classes if imports fail, so the GUI can still partially load for dev purposes
    class OANDAConnector: pass
    class Strategy: pass
    class OrderManager: pass
    # A real application might handle this more gracefully or prevent startup


# --- Bot Configuration ---
DEFAULT_BOT_CONFIG = {
    "INSTRUMENT": "EUR_USD",
    "CANDLE_GRANULARITY": "M1",
    "SMA_SHORT_WINDOW": 5,
    "SMA_LONG_WINDOW": 15, # Changed from 10 to 15 to match previous HISTORICAL_DATA_COUNT logic
    "ORDER_UNITS": 100,
    "STOP_LOSS_PIPS": 20,
    "TAKE_PROFIT_PIPS": 40,
    "LOOP_SLEEP_SECONDS": 30 # Shorter for GUI updates, can be adjusted
    # HISTORICAL_DATA_COUNT will be derived
}


class BotWorker(QObject):
    """
    Worker class to run the trading bot logic in a separate thread.
    """
    log_message = pyqtSignal(str)
    account_summary_updated = pyqtSignal(dict)
    open_positions_signal = pyqtSignal(list)
    trade_history_signal = pyqtSignal(list)
    equity_curve_signal = pyqtSignal(list)
    trade_executed = pyqtSignal(str)
    error_occurred = pyqtSignal(str) # For general errors to be logged
    critical_error_occurred = pyqtSignal(str) # For critical errors to show a dialog
    finished = pyqtSignal()

    def __init__(self, config):
        super().__init__()
        self._is_running = True
        self.config = config
        
        # Derive HISTORICAL_DATA_COUNT
        self.hist_count = self.config["SMA_LONG_WINDOW"] + 10

        # Bot components will be initialized in run() to be thread-local
        self.connector = None
        self.strategy = None
        self.order_manager = None

        # For equity curve
        self.equity_data_points = []
        self.time_counter = 0


    def run(self):
        """Main bot logic loop."""
        self.log_message.emit("Bot worker started.")

        # Critical check for API keys
        if not os.getenv("OANDA_API_KEY") or not os.getenv("OANDA_ACCOUNT_ID"):
            msg = "CRITICAL: OANDA_API_KEY or OANDA_ACCOUNT_ID not found in environment variables."
            self.critical_error_occurred.emit(msg)
            # self.error_occurred.emit(msg) # critical_error_occurred will also call handle_error
            self.finished.emit()
            return

        try:
            self.log_message.emit("Initializing OANDAConnector...")
            self.connector = OANDAConnector()
            if not self.connector.client:
                msg = "Failed to initialize OANDAConnector client (e.g., API key invalid or network issue)."
                self.critical_error_occurred.emit(msg)
                self.finished.emit()
                return
            
            self.log_message.emit("Testing OANDA API connection...")
            if not self.connector.test_connection():
                msg = "OANDA API connection test failed. Please check credentials and network."
                self.critical_error_occurred.emit(msg)
                self.finished.emit()
                return
            self.log_message.emit("OANDA API connection successful.")

            self.log_message.emit("Initializing Strategy...")
            self.strategy = Strategy(
                short_window=self.config["SMA_SHORT_WINDOW"], 
                long_window=self.config["SMA_LONG_WINDOW"]
            )

            self.log_message.emit("Initializing OrderManager...")
            self.order_manager = OrderManager(
                oanda_connector=self.connector,
                default_units=self.config["ORDER_UNITS"],
                default_sl_pips=self.config["STOP_LOSS_PIPS"],
                default_tp_pips=self.config["TAKE_PROFIT_PIPS"]
            )
            self.log_message.emit("All bot components initialized successfully.")

            # Fetch initial trade history after setup
            self.log_message.emit("Fetching initial trade history...")
            trade_history = self.connector.get_trade_history(count=50) # Fetch recent 50 trades
            if trade_history is not None:
                self.trade_history_signal.emit(trade_history)
            else:
                self.log_message.emit("Could not fetch initial trade history.")

        except ValueError as ve: # From Strategy or OrderManager init
            self.error_occurred.emit(f"Configuration Error during initialization: {ve}")
            self.finished.emit()
            return
        except Exception as e:
            self.error_occurred.emit(f"An unexpected error occurred during bot initialization: {e}")
            self.finished.emit()
            return

        while self._is_running:
            current_instrument = self.config["INSTRUMENT"]
            self.log_message.emit(f"--- New Iteration for {current_instrument} ---")

            hist_params = {
                "count": self.hist_count, 
                "granularity": self.config["CANDLE_GRANULARITY"], 
                "price": "M"
            }
            self.log_message.emit(f"Fetching historical data: {current_instrument}, Params: {hist_params}")
            historical_df = self.connector.get_historical_data(current_instrument, params=hist_params)

            if historical_df is None or historical_df.empty:
                self.log_message.emit(f"Could not fetch historical data for {current_instrument}. Skipping.")
                time.sleep(self.config["LOOP_SLEEP_SECONDS"])
                continue

            self.log_message.emit("Generating trading signal...")
            signal = self.strategy.generate_signal(historical_df)
            self.log_message.emit(f"Generated signal for {current_instrument}: {signal}")

            if signal in ['BUY', 'SELL']:
                self.log_message.emit(f"Attempting to place {signal} order for {current_instrument}.")
                order_response = self.order_manager.create_market_order(current_instrument, signal)
                if order_response:
                    # Simplified trade execution message
                    trade_msg = f"Order for {current_instrument} ({signal}): "
                    if 'orderFillTransaction' in order_response:
                        trade_msg += f"FILLED. TxID: {order_response['orderFillTransaction']['id']}"
                    elif 'orderCreateTransaction' in order_response:
                        trade_msg += f"CREATED. TxID: {order_response['orderCreateTransaction']['id']}"
                    elif 'orderCancelTransaction' in order_response:
                        trade_msg += f"CANCELED. Reason: {order_response['orderCancelTransaction'].get('reason')}"
                    else:
                        trade_msg += "Response received, structure not fully recognized."
                    self.trade_executed.emit(trade_msg)
                else:
                    self.error_occurred.emit(f"Failed to place {signal} order for {current_instrument} or no response.")
            
            # Fetch and emit account summary
            if self._is_running:
                summary = self.connector.get_account_summary()
                if summary:
                    self.account_summary_updated.emit(summary)
                    try:
                        equity_value = float(summary.get('NAV', 0.0)) # NAV is equity
                        self.equity_data_points.append((self.time_counter, equity_value))
                        self.time_counter += 1
                        # Emit a copy of the list to avoid issues if it's modified elsewhere
                        self.equity_curve_signal.emit(list(self.equity_data_points)) 
                    except ValueError:
                        self.log_message.emit("Could not parse NAV for equity curve.")
                else:
                    self.log_message.emit("Could not fetch account summary in this iteration.")

            # Fetch and emit open positions
            if self._is_running:
                open_positions = self.connector.get_open_positions() # Should return a list
                if open_positions is not None: # Check if it's None (error) or empty list
                    self.open_positions_signal.emit(open_positions)
                else:
                    self.log_message.emit("Could not fetch open positions in this iteration (returned None).")

            self.log_message.emit(f"Iteration complete. Sleeping for {self.config['LOOP_SLEEP_SECONDS']} seconds...")
            
            # Check stop flag frequently within the sleep period for faster shutdown
            for _ in range(self.config["LOOP_SLEEP_SECONDS"]):
                if not self._is_running:
                    break
                time.sleep(1)
            
            if not self._is_running:
                break # Exit main while loop

        self.log_message.emit("Bot worker stopping.")
        self.finished.emit()

    def stop(self):
        self.log_message.emit("Stop signal received by bot worker.")
        self._is_running = False

class MainWindow(QMainWindow):
    """
    Main window for the FX Trading Bot GUI.
    """
    def __init__(self):
        super().__init__()

        self.setWindowTitle("FX Trading Bot")
        self.setGeometry(100, 100, 800, 600)

        self.bot_thread = None
        self.bot_worker = None

        # Initialize labels for Account Summary Panel
        self.balance_label = None
        self.equity_label = None
        self.margin_avail_label = None
        self.unrealized_pl_label = None
        self.open_trades_label = None
        self.account_currency_label = None

        self.open_positions_table = None
        self.trade_history_table = None
        self.log_viewer_text_edit = None
        self.equity_plot_widget = None
        self.equity_curve_item = None
        self.config_labels = {} 
        self.tab_widget = None


        self._create_menu_bar()
        self._create_status_bar()
        self._setup_central_widget() # This will now include account summary and buttons

        self.show()

    def _create_menu_bar(self):
        """Creates the menu bar for the main window."""
        menu_bar = self.menuBar()

        # File Menu
        file_menu = menu_bar.addMenu("&File") # The & creates a mnemonic (Alt+F)

        exit_action = QAction("&Exit", self)
        exit_action.setStatusTip("Exit application") # Shows in status bar on hover
        exit_action.triggered.connect(self.close) # Connect action to close window
        file_menu.addAction(exit_action)

        # You can add more menus (e.g., "Settings", "Help") here

    def _create_status_bar(self):
        """Creates the status bar for the main window."""
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")

    def _setup_central_widget(self):
        """Sets up the central widget with controls."""
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        # Overall layout for the central widget will be a QVBoxLayout
        # It will contain the control buttons and then the QTabWidget
        overall_layout = QVBoxLayout(central_widget)

        # Control buttons layout (remains at the top)
        button_layout = QHBoxLayout()
        self.start_bot_button = QPushButton("Start Bot")
        self.start_bot_button.clicked.connect(self.start_bot)
        button_layout.addWidget(self.start_bot_button)

        self.stop_bot_button = QPushButton("Stop Bot")
        self.stop_bot_button.clicked.connect(self.stop_bot)
        self.stop_bot_button.setEnabled(False)
        button_layout.addWidget(self.stop_bot_button)
        overall_layout.addLayout(button_layout)

        # Tab Widget
        self.tab_widget = QTabWidget()
        
        # --- Tab 1: Dashboard ---
        dashboard_page_widget = QWidget()
        dashboard_layout = QVBoxLayout(dashboard_page_widget)

        config_group = QGroupBox("Current Bot Configuration")
        config_form_layout = QFormLayout()
        for key, value in DEFAULT_BOT_CONFIG.items():
            key_label = QLabel(f"{key}:")
            value_label = QLabel(str(value))
            config_form_layout.addRow(key_label, value_label)
            self.config_labels[key] = value_label
        config_group.setLayout(config_form_layout)
        dashboard_layout.addWidget(config_group)

        account_summary_group = QGroupBox("Account Summary")
        form_layout = QFormLayout()
        self.balance_label = QLabel("N/A")
        self.equity_label = QLabel("N/A")
        self.margin_avail_label = QLabel("N/A")
        self.unrealized_pl_label = QLabel("N/A")
        self.open_trades_label = QLabel("N/A")
        self.account_currency_label = QLabel("N/A")
        form_layout.addRow("Currency:", self.account_currency_label)
        form_layout.addRow("Balance:", self.balance_label)
        form_layout.addRow("Equity (NAV):", self.equity_label)
        form_layout.addRow("Margin Available:", self.margin_avail_label)
        form_layout.addRow("Unrealized P/L:", self.unrealized_pl_label)
        form_layout.addRow("Open Trades:", self.open_trades_label)
        account_summary_group.setLayout(form_layout)
        dashboard_layout.addWidget(account_summary_group)

        open_positions_group = QGroupBox("Open Positions")
        positions_layout = QVBoxLayout()
        self.open_positions_table = QTableWidget()
        self.open_positions_table.setColumnCount(5)
        self.open_positions_table.setHorizontalHeaderLabels(["ID", "Instrument", "Units", "Open Price", "Unrealized P/L"])
        self.open_positions_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.open_positions_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.open_positions_table.setAlternatingRowColors(True)
        self.open_positions_table.horizontalHeader().setStretchLastSection(True)
        positions_layout.addWidget(self.open_positions_table)
        open_positions_group.setLayout(positions_layout)
        dashboard_layout.addWidget(open_positions_group)

        trade_history_group = QGroupBox("Trade History (Last 50)")
        history_layout = QVBoxLayout()
        self.trade_history_table = QTableWidget()
        self.trade_history_table.setColumnCount(8)
        self.trade_history_table.setHorizontalHeaderLabels(["ID", "Instrument", "Units", "Open Price", "Close Price", "Realized P/L", "Open Time", "Close Time"])
        self.trade_history_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.trade_history_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.trade_history_table.setAlternatingRowColors(True)
        self.trade_history_table.setColumnWidth(0, 70); self.trade_history_table.setColumnWidth(1, 100); self.trade_history_table.setColumnWidth(5, 100); self.trade_history_table.setColumnWidth(6, 150); self.trade_history_table.setColumnWidth(7, 150)
        history_layout.addWidget(self.trade_history_table)
        trade_history_group.setLayout(history_layout)
        dashboard_layout.addWidget(trade_history_group)
        
        dashboard_layout.addStretch(1) # Add stretch at the end of dashboard layout
        self.tab_widget.addTab(dashboard_page_widget, "Dashboard")

        # --- Tab 2: Charts & Logs ---
        charts_logs_page_widget = QWidget()
        charts_logs_layout = QVBoxLayout(charts_logs_page_widget) # Main layout for this tab

        performance_chart_group = QGroupBox("Performance Chart")
        chart_layout_inner = QVBoxLayout() # Layout for inside the groupbox
        self.equity_plot_widget = pg.PlotWidget()
        self.equity_plot_widget.setBackground('w'); self.equity_plot_widget.setLabel('left', 'Equity ($)'); self.equity_plot_widget.setLabel('bottom', 'Time (Updates)'); self.equity_plot_widget.setTitle('Equity Curve'); self.equity_plot_widget.showGrid(x=True, y=True); self.equity_plot_widget.enableAutoRange('xy', True)
        self.equity_curve_item = self.equity_plot_widget.plot(pen=pg.mkPen('g', width=2))
        chart_layout_inner.addWidget(self.equity_plot_widget)
        performance_chart_group.setLayout(chart_layout_inner)
        charts_logs_layout.addWidget(performance_chart_group, 1) # Give chart more stretch factor

        log_viewer_group = QGroupBox("Event Logs")
        log_layout_inner = QVBoxLayout()
        self.log_viewer_text_edit = QTextEdit()
        self.log_viewer_text_edit.setReadOnly(True); self.log_viewer_text_edit.setMinimumHeight(150)
        log_layout_inner.addWidget(self.log_viewer_text_edit)
        log_viewer_group.setLayout(log_layout_inner)
        charts_logs_layout.addWidget(log_viewer_group, 1) # Give logs some stretch factor
        
        self.tab_widget.addTab(charts_logs_page_widget, "Charts & Logs")

        overall_layout.addWidget(self.tab_widget) # Add tab widget to the overall layout
        central_widget.setLayout(overall_layout)


    def start_bot(self):
        if self.bot_thread is not None and self.bot_thread.isRunning():
            self.status_bar.showMessage("Bot is already running.")
            return

        # Pre-flight check for API keys
        if not os.getenv("OANDA_API_KEY") or not os.getenv("OANDA_ACCOUNT_ID"):
            QMessageBox.critical(self, "Critical Error", 
                                 "OANDA_API_KEY or OANDA_ACCOUNT_ID not found in environment variables. "
                                 "Please set them before starting the bot.")
            self.status_bar.showMessage("Bot start failed: Missing API credentials.", 5000)
            return

        self.status_bar.showMessage("Bot starting...")
        self.start_bot_button.setEnabled(False)
        self.stop_bot_button.setEnabled(True)
        if self.log_viewer_text_edit:
            self.log_viewer_text_edit.clear()
            self.log_viewer_text_edit.append("Bot starting...")
        
        if self.equity_curve_item:
            self.equity_curve_item.setData([], [])

        self.bot_thread = QThread()
        self.bot_worker = BotWorker(config=DEFAULT_BOT_CONFIG.copy())
        self.bot_worker.moveToThread(self.bot_thread)

        # Connect signals
        self.bot_worker.log_message.connect(self.handle_log_message)
        self.bot_worker.account_summary_updated.connect(self.handle_account_summary)
        self.bot_worker.open_positions_signal.connect(self.handle_open_positions_update)
        self.bot_worker.trade_history_signal.connect(self.handle_trade_history_update)
        self.bot_worker.equity_curve_signal.connect(self.handle_equity_curve_update)
        self.bot_worker.trade_executed.connect(self.handle_trade_executed)
        self.bot_worker.error_occurred.connect(self.handle_error) # General errors
        self.bot_worker.critical_error_occurred.connect(self.handle_critical_error) # Critical errors
        self.bot_worker.finished.connect(self.on_bot_finished)
        self.bot_thread.started.connect(self.bot_worker.run)

        self.bot_thread.start()

    def stop_bot(self):
        if self.bot_worker:
            self.status_bar.showMessage("Bot stopping...")
            self.bot_worker.stop()
            # UI update for button states will be handled in on_bot_finished
        else:
            self.status_bar.showMessage("Bot is not running.")

    def on_bot_finished(self):
        self.status_bar.showMessage("Bot stopped.")
        self.start_bot_button.setEnabled(True)
        self.stop_bot_button.setEnabled(False)

        if self.bot_thread:
            self.bot_thread.quit()
            self.bot_thread.wait(5000) # Wait up to 5s for thread to finish
            if not self.bot_thread.isFinished():
                print("Warning: Bot thread did not finish cleanly. Terminating.") # Should not happen often
                self.bot_thread.terminate() # Force terminate if stuck
                self.bot_thread.wait()

        self.bot_thread = None
        self.bot_worker = None # Allow it to be garbage collected

    # --- Placeholder Slots for Bot Signals ---
    def handle_log_message(self, message):
        print(f"GUI Log: {message}") # For console debugging
        if self.log_viewer_text_edit:
            self.log_viewer_text_edit.append(message)
            self.log_viewer_text_edit.moveCursor(QTextCursor.MoveOperation.End)
        self.status_bar.showMessage(message, 3000) # Show message in status bar for 3s

    def handle_account_summary(self, summary_data):
        currency = summary_data.get('currency', '')
        
        balance = summary_data.get('balance', 'N/A')
        nav = summary_data.get('NAV', 'N/A') # NAV is Net Asset Value (Equity)
        margin_available = summary_data.get('marginAvailable', 'N/A')
        unrealized_pl = summary_data.get('unrealizedPL', 'N/A')
        open_trades = summary_data.get('openTradeCount', 'N/A')

        self.account_currency_label.setText(str(currency))
        
        try: # Format currency values nicely
            self.balance_label.setText(f"{float(balance):.2f} {currency}" if balance != 'N/A' else "N/A")
            self.equity_label.setText(f"{float(nav):.2f} {currency}" if nav != 'N/A' else "N/A")
            self.margin_avail_label.setText(f"{float(margin_available):.2f} {currency}" if margin_available != 'N/A' else "N/A")
            self.unrealized_pl_label.setText(f"{float(unrealized_pl):.2f} {currency}" if unrealized_pl != 'N/A' else "N/A")
        except ValueError: # Handle cases where conversion might fail for "N/A" or unexpected strings
            self.balance_label.setText(str(balance))
            self.equity_label.setText(str(nav))
            self.margin_avail_label.setText(str(margin_available))
            self.unrealized_pl_label.setText(str(unrealized_pl))

        self.open_trades_label.setText(str(open_trades))
        
        # Update status bar as well, perhaps with NAV as it's a key figure
        self.status_bar.showMessage(f"Equity: {self.equity_label.text()} | Open Trades: {open_trades}", 5000)

    def handle_open_positions_update(self, positions_data_list):
        if self.open_positions_table is None:
            return

        self.open_positions_table.setRowCount(0) # Clear existing rows
        
        if not positions_data_list: # Handle case where there are no open positions
            # Optionally, display a message in the table or a label
            # For now, just ensuring it's empty is fine.
            return

        for row_idx, pos_data in enumerate(positions_data_list):
            self.open_positions_table.insertRow(row_idx)
            
            # Create QTableWidgetItems for each piece of data
            id_item = QTableWidgetItem(str(pos_data.get('id', 'N/A')))
            instrument_item = QTableWidgetItem(str(pos_data.get('instrument', 'N/A')))
            units_item = QTableWidgetItem(str(pos_data.get('currentUnits', 'N/A')))
            open_price_item = QTableWidgetItem(str(pos_data.get('price', 'N/A')))
            
            unrealized_pl_str = str(pos_data.get('unrealizedPL', '0.00'))
            unrealized_pl_item = QTableWidgetItem(unrealized_pl_str)
            
            # Color-code P/L
            try:
                pl_value = float(unrealized_pl_str)
                if pl_value > 0:
                    unrealized_pl_item.setForeground(QColor("green"))
                elif pl_value < 0:
                    unrealized_pl_item.setForeground(QColor("red"))
                # else: keep default color (black)
            except ValueError:
                pass # Could not convert to float, keep default color

            # Set items in the table
            self.open_positions_table.setItem(row_idx, 0, id_item)
            self.open_positions_table.setItem(row_idx, 1, instrument_item)
            self.open_positions_table.setItem(row_idx, 2, units_item)
            self.open_positions_table.setItem(row_idx, 3, open_price_item)
            self.open_positions_table.setItem(row_idx, 4, unrealized_pl_item)
            
        # Optional: Resize columns to content
        # self.open_positions_table.resizeColumnsToContents()


    def handle_trade_executed(self, trade_info):
        print(f"GUI Trade Executed: {trade_info}")
        self.handle_log_message(f"Trade: {trade_info}") # Also add to main log
        # Potentially trigger a refresh of trade history here if desired
        # if self.bot_worker and self.bot_thread and self.bot_thread.isRunning():
        #     # This would require adding a method to BotWorker to request history refresh
        #     # For now, history is only fetched at startup.
        #     pass


    def handle_trade_history_update(self, history_data_list):
        if self.trade_history_table is None:
            return
        
        self.trade_history_table.setRowCount(0) # Clear existing rows

        if not history_data_list:
            return

        for row_idx, trade_data in enumerate(history_data_list):
            self.trade_history_table.insertRow(row_idx)

            # Fields: "ID", "Instrument", "Units", "Open Price", "Close Price", "Realized P/L", "Open Time", "Close Time"
            id_item = QTableWidgetItem(str(trade_data.get('id', 'N/A')))
            instrument_item = QTableWidgetItem(str(trade_data.get('instrument', 'N/A')))
            units_item = QTableWidgetItem(str(trade_data.get('initialUnits', 'N/A'))) # Using initialUnits
            open_price_item = QTableWidgetItem(str(trade_data.get('price', 'N/A'))) # Open price
            close_price_item = QTableWidgetItem(str(trade_data.get('averageClosePrice', 'N/A')))
            
            realized_pl_str = str(trade_data.get('realizedPL', '0.00'))
            realized_pl_item = QTableWidgetItem(realized_pl_str)
            
            open_time_item = QTableWidgetItem(str(trade_data.get('openTime', 'N/A')))
            close_time_item = QTableWidgetItem(str(trade_data.get('closeTime', 'N/A')))

            # Color-code Realized P/L
            try:
                pl_value = float(realized_pl_str)
                if pl_value > 0:
                    realized_pl_item.setForeground(QColor("green"))
                elif pl_value < 0:
                    realized_pl_item.setForeground(QColor("red"))
            except ValueError:
                pass 

            self.trade_history_table.setItem(row_idx, 0, id_item)
            self.trade_history_table.setItem(row_idx, 1, instrument_item)
            self.trade_history_table.setItem(row_idx, 2, units_item)
            self.trade_history_table.setItem(row_idx, 3, open_price_item)
            self.trade_history_table.setItem(row_idx, 4, close_price_item)
            self.trade_history_table.setItem(row_idx, 5, realized_pl_item)
            self.trade_history_table.setItem(row_idx, 6, open_time_item)
            self.trade_history_table.setItem(row_idx, 7, close_time_item)
        
        # Optional: self.trade_history_table.resizeColumnsToContents()

    def handle_equity_curve_update(self, equity_points_list):
        if self.equity_curve_item:
            x_values = [point[0] for point in equity_points_list]
            y_values = [point[1] for point in equity_points_list]
            self.equity_curve_item.setData(x_values, y_values)

    def handle_error(self, error_message):
        print(f"GUI Log (Error): {error_message}") # Keep console log for all errors
        if self.log_viewer_text_edit:
            self.log_viewer_text_edit.append(f"<font color='red'>ERROR: {error_message}</font>")
            self.log_viewer_text_edit.moveCursor(QTextCursor.MoveOperation.End)
        self.status_bar.showMessage(f"Error: {error_message}", 5000) # Show in status bar

    def handle_critical_error(self, message):
        QMessageBox.critical(self, "Critical Bot Error", message)
        self.handle_error(message) # Also log it to the text view
        # Potentially disable start button or other UI elements if bot cannot recover
        # self.start_bot_button.setEnabled(false); # Example, might be better handled in on_bot_finished


    def closeEvent(self, event: QCloseEvent):
        """Handle the window close event."""
        if self.bot_thread and self.bot_thread.isRunning():
            self.handle_log_message("Window close requested. Stopping bot...")
            self.stop_bot()
            # Give some time for the bot to stop
            if self.bot_thread: # Check if it became None due to quick stop
                 self.bot_thread.wait(3000) # Wait up to 3 seconds
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Apply basic stylesheet
    app.setStyleSheet("""
        QGroupBox { 
            font-weight: bold; 
            margin-top: 1ex; 
        }
        QGroupBox::title { 
            subcontrol-origin: margin; 
            left: 7px; 
            padding: 0 5px 0 5px; 
        }
        QTabWidget::pane { /* The tab widget frame */
            border-top: 2px solid #C2C7CB;
        }
        QTabBar::tab {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                        stop: 0 #E1E1E1, stop: 0.4 #DDDDDD,
                                        stop: 0.5 #D8D8D8, stop: 1.0 #D3D3D3);
            border: 1px solid #C4C4C3;
            border-bottom-color: #C2C7CB; /* same as pane border */
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            min-width: 8ex;
            padding: 5px;
        }
        QTabBar::tab:selected, QTabBar::tab:hover {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                        stop: 0 #fafafa, stop: 0.4 #f4f4f4,
                                        stop: 0.5 #e7e7e7, stop: 1.0 #fafafa);
        }
        QTabBar::tab:selected {
            border-color: #9B9B9B;
            border-bottom-color: #C2C7CB; /* same as pane border */
        }
    """)

    if 'OANDAConnector' not in globals() or OANDAConnector is None:
        QMessageBox.critical(None, "Application Startup Error", 
                             "Critical Error: OANDAConnector class not found or not imported correctly. "
                             "Please ensure all bot components are in the Python path.")
        sys.exit(1)

    window = MainWindow()
    sys.exit(app.exec())
```
