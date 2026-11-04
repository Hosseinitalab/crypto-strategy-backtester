import sys
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtWidgets import QGroupBox, QFormLayout, QTabWidget, QMessageBox
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout
from PyQt5.QtWidgets import QLabel, QPushButton, QComboBox, QLineEdit, QListWidget
from PyQt5.QtWidgets import QFrame, QGridLayout, QSizePolicy, QSpacerItem
from strategies import *
import pickle
import re


class StrategyWindow:

    _CANDLE_TYPE = ["Open", "Close", "High", "Low"]

    def __init__(self):

        self._tab = QWidget()
        self._report_area = None
        self._report_graph = None
        self._report_detail = None

    def _clear_report(self):

        if self._report_area is None:
            return

        # Clear previous graph widgets
        while self._report_graph.count():
            item = self._report_graph.takeAt(0)
            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

        # Clear previous report-detail widgets
        while self._report_detail.count():
            item = self._report_detail.takeAt(0)
            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

    def _create_metric_card(self, title, value, accent="#3478E5",
                            subtitle=None, prominent=False):
        """Create a styled card for one backtest metric."""

        card = QFrame()
        card.setObjectName("metricCard")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(5)

        title_label = QLabel(title)
        title_label.setStyleSheet("""
            color: #64748B;
            font-size: 11px;
            font-weight: 600;
            border: none;
            background: transparent;
        """)

        value_label = QLabel(str(value))
        value_label.setWordWrap(True)
        value_label.setStyleSheet(f"""
            color: {accent};
            font-size: {"20px" if prominent else "15px"};
            font-weight: bold;
            border: none;
            background: transparent;
        """)

        layout.addWidget(title_label)
        layout.addWidget(value_label)

        if subtitle is not None:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setWordWrap(True)
            subtitle_label.setStyleSheet("""
                color: #64748B;
                font-size: 10px;
                border: none;
                background: transparent;
            """)
            layout.addWidget(subtitle_label)

        card.setStyleSheet("""
            QFrame#metricCard {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
            }
        """)

        return card

    def _create_final_results_panel(self, statistics):
        """Build the final backtest results dashboard."""

        panel = QFrame()
        panel.setObjectName("resultsPanel")

        panel.setStyleSheet("""
            QFrame#resultsPanel {
                background-color: #F4F7FB;
                border: 1px solid #DCE5F0;
                border-radius: 12px;
            }
        """)

        main_layout = QVBoxLayout(panel)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # ---------- Header ----------
        header = QFrame()
        header.setObjectName("resultsHeader")
        header.setStyleSheet("""
            QFrame#resultsHeader {
                background-color: #203E68;
                border-radius: 8px;
            }
        """)

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 12, 12, 12)

        title = QLabel("🏆  Final Results")
        title.setStyleSheet("""
            color: white;
            font-size: 16px;
            font-weight: bold;
            border: none;
            background: transparent;
        """)

        header_layout.addWidget(title)
        main_layout.addWidget(header)

        # ---------- Calculate displayed values ----------
        initial = statistics["initial-capital"]
        final = statistics["capital"]
        profit = final - initial
        total_return = statistics["total-return"]
        total_trades = statistics["total-trade"]
        winning = statistics["winning-trade"]
        losing = statistics["losing-trade"]
        win_rate = statistics["win-rate"]

        profit_color = "#16834A" if profit >= 0 else "#D12F45"
        profit_sign = "+" if profit > 0 else ""

        # ---------- Main metric cards ----------
        grid = QGridLayout()
        grid.setSpacing(8)

        cards = [
            self._create_metric_card(
                "FINAL CAPITAL",
                f"${final:,.2f}",
                accent="#203E68",
                subtitle=f"{total_return:+.2f}%",
                prominent=True
            ),
            self._create_metric_card(
                "PROFIT / LOSS",
                f"{profit_sign}${abs(profit):,.2f}"
                if profit >= 0 else f"-${abs(profit):,.2f}",
                accent=profit_color,
                subtitle="Net result",
                prominent=True
            ),
            self._create_metric_card(
                "INITIAL CAPITAL",
                f"${initial:,.2f}",
                accent="#168D8D"
            ),
            self._create_metric_card(
                "TOTAL TRADES",
                str(total_trades),
                accent="#3478E5",
                subtitle=f"{winning} wins · {losing} losses"
            ),
            self._create_metric_card(
                "TOTAL RETURN",
                f"{total_return:.2f}%",
                accent="#168D8D"
            ),
            self._create_metric_card(
                "WIN RATE",
                f"{win_rate:.2f}%",
                accent="#3478E5"
            ),
        ]

        for index, card in enumerate(cards):
            row = index // 2
            column = index % 2
            grid.addWidget(card, row, column)

        main_layout.addLayout(grid)
        main_layout.addStretch()

        return panel

  
class MovingAverageWindow(StrategyWindow):

    def __init__(self, trading_gui):

        super().__init__()
        self._trading_gui = trading_gui
        self.__init_widgets()
        self.__setup()

    def __init_widgets(self):

        # Edit Widgets
        self._window_edit = None
        self._shorter_sma_edit = None
        self._longer_sma_edit = None

        # ComboBox Widget
        self._add_sma_candle_combo = None
        self._trade_candle_combo = None

        
        # Button Widget
        self._add_sma_button = None
        self._trade_button = None

        # List Widget
        self._sma_list = None

    def __setup(self):

        master_layout     = QVBoxLayout()
        right_vbox        = QVBoxLayout()
        left_vbox         = QVBoxLayout()
        upper_hbox        = QHBoxLayout()
        self._report_area = QHBoxLayout()

        ###################### Upper Hbox ######################

        # Left Vbox
        hbox   = QHBoxLayout()
        lgroup = QGroupBox("Add SMA")
        lform  = QFormLayout()
        lform.setRowWrapPolicy(QFormLayout.WrapAllRows)

        window_label    = QLabel("Window")
        candle_label    = QLabel("Candle Type")

        self._window_edit   = QLineEdit()
        
        self._add_sma_candle_combo   = QComboBox()
        self._add_sma_candle_combo.addItems(self._CANDLE_TYPE)

        lform.addRow(window_label, self._window_edit)
        lform.addRow(candle_label, self._add_sma_candle_combo)

        self._sma_list = QListWidget()
        hbox.addWidget(self._sma_list)

        self._add_sma_button = QPushButton("Add SMA")
        self._add_sma_button.clicked.connect(self.__add_sma)
        hbox.addWidget(self._add_sma_button)

        lform.addRow(hbox)
        lgroup.setLayout(lform)
        left_vbox.addWidget(lgroup)
        upper_hbox.addLayout(left_vbox)

        # Right Vbox
        hbox2  = QHBoxLayout()
        rgroup = QGroupBox("Strategy Setup")
        rform  = QFormLayout()
        rform.setRowWrapPolicy(QFormLayout.WrapAllRows)

        shorter_window_label    = QLabel("Shorter SMA Window")
        longer_window_label     = QLabel("Longer SMA Window")
        trade_candle_label      = QLabel("Candle Type")

        self._shorter_sma_edit = QLineEdit()
        self._longer_sma_edit  = QLineEdit()

        self._shorter_sma_edit.setPlaceholderText("Enter Shorter SMA Window")
        self._longer_sma_edit.setPlaceholderText("Enter Longer SMA Window")

        self._trade_candle_combo = QComboBox()
        self._trade_candle_combo.addItems(self._CANDLE_TYPE)
        self._trade_candle_combo.setCurrentText("Close")

        rform.addRow(shorter_window_label, self._shorter_sma_edit)
        rform.addRow(longer_window_label, self._longer_sma_edit)
        rform.addRow(trade_candle_label, self._trade_candle_combo)

        hbox2.addStretch()
        self._trade_button = QPushButton("Start Trading")
        hbox2.addWidget(self._trade_button)
        self._trade_button.clicked.connect(self.__trade)
        rform.addRow(hbox2)

        rgroup.setLayout(rform)
        right_vbox.addWidget(rgroup)
        upper_hbox.addLayout(right_vbox)

        master_layout.addLayout(upper_hbox, 1)

        ###################### Lower Hbox ######################
        self._report_graph = QVBoxLayout()
        self._report_detail = QVBoxLayout()
        self._report_area.addLayout(self._report_graph, 3)
        self._report_area.addLayout(self._report_detail, 1)
        master_layout.addLayout(self._report_area, 3)
        self._tab.setLayout(master_layout)

    def __add_sma(self):

        window = self._window_edit.text().strip()
        self._window_edit.setText(window)

        if not window:
            QMessageBox.warning(self._tab, "Warning", "SMA window cannot be empty.")
            # clear previous reports
            self._clear_report()
            return False

        try:
            window = int(window)
            if window <= 0:
                # clear previous reports
                self._clear_report()
                raise ValueError
            
        except ValueError:
            QMessageBox.warning(self._tab, "Warning", "SMA window must be a positive integer.")
            # clear previous reports
            self._clear_report()
            return False

        candle_type = self._add_sma_candle_combo.currentText()
        item = f"{candle_type}-{window}"

        for i in range(self._sma_list.count()):
            if self._sma_list.item(i).text() == item:
                # clear previous reports
                self._clear_report()
                return False

        self._sma_list.addItem(item)

    def __trade(self):

        # clear previous reports
        self._clear_report()

        if not self.__check_fields():
            return 
        
        if self._trading_gui._src is None:
            QMessageBox.warning(self._tab, "Warning", "Trading met with failure! There is no data so check the Binance.")
            return

        if self._trading_gui._initial_capital is None:
            QMessageBox.warning(self._tab, "Warning", "Trading met with failure! Check Settings.")
            return

        candle = self._trade_candle_combo.currentText()
        shorter_window = int(float(self._shorter_sma_edit.text().strip()))
        longer_window = int(float(self._longer_sma_edit.text().strip()))
        windows = (shorter_window, longer_window)

        strategy = MovingAverage(self._trading_gui._src)

        sma_list = [self._sma_list.item(i).text() for i in range(self._sma_list.count())]
        sma_dict = {
            "Close": [],
            "Open":  [],
            "Low":   [],
            "High":  []
        }

        for i in sma_list:
            candle_type, window = i.split("-")
            window = int(window)
            sma_dict[candle_type].append(window)

        if not strategy.add_sma(sma_dict):
            QMessageBox.warning(self._tab, "Warning", "Trading met with failure! there is no SMA Window.")
            return

        s = strategy.trade(price=candle,
                           windows=windows,
                           margin_portion=self._trading_gui._margin,
                           initial_capital=self._trading_gui._initial_capital,
                           tp=self._trading_gui._tp,
                           sl=self._trading_gui._sl,
                           commission_rate=self._trading_gui._commission_rate)
        
        if not s:
            QMessageBox.warning(self._tab, "Warning", "Trading met with failure.")
            return

        QMessageBox.information(self._tab, "Warning", "Trading successfully finished.")
        canvas = FigureCanvasQTAgg(strategy._report_graph())

        self._report_graph.addWidget(canvas)

        # Display the final results dashboard
        results_panel = self._create_final_results_panel(strategy._statistics)
        self._report_detail.addWidget(results_panel)

    def __check_fields(self):

        window_format = r"^\d+$"
        shorter_sma = self._shorter_sma_edit.text().strip()
        longer_sma = self._longer_sma_edit.text().strip()

        # shorter sma window
        if not shorter_sma:
            QMessageBox.warning(self._tab, "Warning", "Shorter SMA Window can not be empty")
            return False

        if not re.search(window_format, shorter_sma):
            QMessageBox.warning(self._tab, "Warning", "Shorter SMA Window must be a positive interger number")
            return False

        # longer sma window
        if not longer_sma:
            QMessageBox.warning(self._tab, "Warning", "Longer SMA Window can not be empty")
            return False

        if not re.search(window_format, longer_sma):
            QMessageBox.warning(self._tab, "Warning", "Longer SMA Window must be a positive interger number")
            return False

        if int(shorter_sma) >= int(longer_sma):
            QMessageBox.warning(self._tab, "Warning", "Longer SMA Window must be greater than Shorter SMA Window")
            return False

        return True


class RSIWindow(StrategyWindow):

    def __init__(self, trading_gui):

        super().__init__()
        self._trading_gui = trading_gui
        self.__init_widgets()
        self.__setup()

    def __init_widgets(self):

        # Edit Widgets
        self._sma_edit = None
        self._window_edit = None
        self._overbought_edit = None
        self._oversold_edit = None

        # ComboBox Widget
        self._add_sma_candle_combo = None
        self._trade_candle_combo = None

        # Button Widget
        self._add_sma_button = None
        self._trade_button = None

        # List Widget
        self._sma_list = None

    def __setup(self):

        master_layout     = QVBoxLayout()
        right_vbox        = QVBoxLayout()
        left_vbox         = QVBoxLayout()
        upper_hbox        = QHBoxLayout()
        self._report_area = QHBoxLayout()

        ###################### Upper Hbox ######################

        # Left Vbox
        hbox   = QHBoxLayout()
        lgroup = QGroupBox("Add SMA")
        lform  = QFormLayout()
        lform.setRowWrapPolicy(QFormLayout.WrapAllRows)

        window_label    = QLabel("Window")
        candle_label    = QLabel("Candle Type")

        self._window_edit   = QLineEdit()
        
        self._add_sma_candle_combo   = QComboBox()
        self._add_sma_candle_combo.addItems(self._CANDLE_TYPE)

        lform.addRow(window_label, self._window_edit)
        lform.addRow(candle_label, self._add_sma_candle_combo)

        self._sma_list = QListWidget()
        hbox.addWidget(self._sma_list)

        self._add_sma_button = QPushButton("Add SMA")
        self._add_sma_button.clicked.connect(self.__add_sma)
        hbox.addWidget(self._add_sma_button)

        lform.addRow(hbox)
        lgroup.setLayout(lform)
        left_vbox.addWidget(lgroup)
        upper_hbox.addLayout(left_vbox)

        # Right Vbox
        hbox2  = QHBoxLayout()
        rgroup = QGroupBox("Strategy Setup")
        rform  = QFormLayout()
        rform.setRowWrapPolicy(QFormLayout.WrapAllRows)
        overbought_label     = QLabel("Overbought Level")
        oversold_label       = QLabel("Oversold Level")
        sma_window_label     = QLabel("SMA Window")
        trade_candle_label   = QLabel("Candle Type")

        self._overbought_edit    = QLineEdit("70")
        self._oversold_edit      = QLineEdit("30")
        self._sma_edit           = QLineEdit("14")

        self._overbought_edit.setPlaceholderText("Enter Overbought Level")
        self._oversold_edit.setPlaceholderText("Enter Oversold Level")
        self._sma_edit.setPlaceholderText("Enter SMA Window")

        self._trade_candle_combo = QComboBox()
        self._trade_candle_combo.addItems(self._CANDLE_TYPE)
        self._trade_candle_combo.setCurrentText("Close")

        rform.addRow(overbought_label, self._overbought_edit)
        rform.addRow(oversold_label, self._oversold_edit)
        rform.addRow(sma_window_label, self._sma_edit)
        rform.addRow(trade_candle_label, self._trade_candle_combo)

        hbox2.addStretch()
        self._trade_button = QPushButton("Start Trading")
        hbox2.addWidget(self._trade_button)
        self._trade_button.clicked.connect(self.__trade)
        rform.addRow(hbox2)

        rgroup.setLayout(rform)
        right_vbox.addWidget(rgroup)
        upper_hbox.addLayout(right_vbox)

        master_layout.addLayout(upper_hbox, 1)

        ###################### Lower Hbox ######################
        self._report_graph = QVBoxLayout()
        self._report_detail = QVBoxLayout()
        self._report_area.addLayout(self._report_graph, 3)
        self._report_area.addLayout(self._report_detail, 1)
        master_layout.addLayout(self._report_area, 3)
        self._tab.setLayout(master_layout)

    def __add_sma(self):

        window = self._window_edit.text().strip()
        self._window_edit.setText(window)

        if not window:
            QMessageBox.warning(self._tab, "Warning", "SMA window cannot be empty.")
            # clear previous reports
            self._clear_report()
            return False

        try:
            window = int(window)
            if window <= 0:
                # clear previous reports
                self._clear_report()
                raise ValueError
            
        except ValueError:
            QMessageBox.warning(self._tab, "Warning", "SMA window must be a positive integer.")
            # clear previous reports
            self._clear_report()
            return False

        candle_type = self._add_sma_candle_combo.currentText()
        item = f"{candle_type}-{window}"

        for i in range(self._sma_list.count()):
            if self._sma_list.item(i).text() == item:
                # clear previous reports
                self._clear_report()
                return False

        self._sma_list.addItem(item)

    def __trade(self):

        # clear previous reports
        self._clear_report()

        if not self.__check_fields():
            return 
        
        if self._trading_gui._src is None:
            QMessageBox.warning(self._tab, "Warning", "Trading met with failure! There is no data so check the Binance.")
            return

        if self._trading_gui._initial_capital is None:
            QMessageBox.warning(self._tab, "Warning", "Trading met with failure! Check Settings.")
            return

        overbought = float(self._overbought_edit.text())
        oversold   = float(self._oversold_edit.text())
        window     = int(self._sma_edit.text())
        candle     = self._trade_candle_combo.currentText()

        strategy = RSI(self._trading_gui._src)

        sma_list = [self._sma_list.item(i).text() for i in range(self._sma_list.count())]
        sma_dict = {
            "Close": [],
            "Open":  [],
            "Low":   [],
            "High":  []
        }

        for i in sma_list:
            candle_type, window = i.split("-")
            window = int(window)
            sma_dict[candle_type].append(window)

        if not strategy.add_rsi(price=candle, window=window):
            QMessageBox.warning(self._tab, "Warning", "Trading met with failure! there is no SMA Window.")
            return

        s = strategy.trade(price=candle,
                           window=window,
                           overbought_level=overbought,
                           oversold_level=oversold,
                           margin_portion=self._trading_gui._margin,
                           initial_capital=self._trading_gui._initial_capital,
                           tp=self._trading_gui._tp,
                           sl=self._trading_gui._sl,
                           commission_rate=self._trading_gui._commission_rate)
        
        if not s:
            QMessageBox.warning(self._tab, "Warning", "Trading met with failure.")
            return

        QMessageBox.information(self._tab, "Warning", "Trading successfully finished.")
        canvas = FigureCanvasQTAgg(strategy._report_graph())

        self._report_graph.addWidget(canvas)

        # Display the final results dashboard
        results_panel = self._create_final_results_panel(strategy._statistics)
        self._report_detail.addWidget(results_panel)

    def __check_fields(self):

        window_format = r"^\d+$"
        sma = self._sma_edit.text().strip()
        overbought = self._overbought_edit.text().strip()
        oversold = self._oversold_edit.text().strip()

        # sma window
        if not sma:
            QMessageBox.warning(self._tab, "Warning", "SMA Window can not be empty")
            return False

        if not re.search(window_format, sma):
            QMessageBox.warning(self._tab, "Warning", "SMA Window must be a positive interger number")
            return False

        # overbought
        if not overbought:
            QMessageBox.warning(self._tab, "Warning", "Overbought Level can not be empty")
            return False

        if not re.search(window_format, overbought):
            QMessageBox.warning(self._tab, "Warning", "Overbought Level must be a positive interger number")
            return False
        
        # oversold
        if not oversold:
            QMessageBox.warning(self._tab, "Warning", "Oversold Level can not be empty")
            return False

        if not re.search(window_format, oversold):
            QMessageBox.warning(self._tab, "Warning", "Oversold Level must be a positive interger number")
            return False

        if int(oversold) >= int(overbought):
            QMessageBox.warning(self._tab, "Warning", "Overbought Level must be greater than Oversold Level")
            return False
        
        return True


class MACDWindow(StrategyWindow):

    def __init__(self, trading_gui):

        super().__init__()
        self._trading_gui = trading_gui
        self.__init_widgets()
        self.__setup()

    def __init_widgets(self):

        # Edit Widgets
        self._slow_ema_edit = None
        self._fast_ema_edit = None
        self._signal_ema_edit = None

        # ComboBox Widget
        self._trade_candle_combo = None

        # Button Widget
        self._trade_button = None

    def __setup(self):

        master_layout     = QVBoxLayout()
        hbox              = QHBoxLayout()
        self._report_area = QHBoxLayout()

        ###################### Upper Hbox ######################

        hbox2  = QHBoxLayout()
        group = QGroupBox("Strategy Setup")
        form  = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.WrapAllRows)
        slow_ema_label      = QLabel("Slow EMA Window")
        fast_ema_label      = QLabel("Fast EMA Window")
        signal_ema_label    = QLabel("Signal EMA Window")
        trade_candle_label  = QLabel("Candle Type")

        self._slow_ema_edit    = QLineEdit("26")
        self._fast_ema_edit    = QLineEdit("12")
        self._signal_ema_edit  = QLineEdit("9")

        self._slow_ema_edit.setPlaceholderText("Enter Slow EMA Window")
        self._fast_ema_edit.setPlaceholderText("Enter Fast EMA Window")
        self._signal_ema_edit.setPlaceholderText("Enter Signal EMA Window")

        self._trade_candle_combo = QComboBox()
        self._trade_candle_combo.addItems(self._CANDLE_TYPE)
        self._trade_candle_combo.setCurrentText("Close")

        form.addRow(slow_ema_label, self._slow_ema_edit)
        form.addRow(fast_ema_label, self._fast_ema_edit)
        form.addRow(signal_ema_label, self._signal_ema_edit)
        form.addRow(trade_candle_label, self._trade_candle_combo)

        hbox2.addStretch()
        self._trade_button = QPushButton("Start Trading")
        hbox2.addWidget(self._trade_button)
        self._trade_button.clicked.connect(self.__trade)
        form.addRow(hbox2)

        group.setLayout(form)
        hbox.addWidget(group)

        master_layout.addLayout(hbox)

        ###################### Lower Hbox ######################
        self._report_graph = QVBoxLayout()
        self._report_detail = QVBoxLayout()
        self._report_area.addLayout(self._report_graph, 3)
        self._report_area.addLayout(self._report_detail, 1)
        master_layout.addLayout(self._report_area, 3)
        self._tab.setLayout(master_layout)

    def __trade(self):  

        # clear previous reports
        self._clear_report()

        if not self.__check_fields():
            return 
        
        if self._trading_gui._src is None:
            QMessageBox.warning(self._tab, "Warning", "Trading met with failure! There is no data so check the Binance.")
            return

        if self._trading_gui._initial_capital is None:
            QMessageBox.warning(self._tab, "Warning", "Trading met with failure! Check Settings.")
            return

        slow_ema     = int(self._slow_ema_edit.text())
        fast_ema     = int(self._fast_ema_edit.text())
        signal_ema   = int(self._signal_ema_edit.text())

        candle = self._trade_candle_combo.currentText()

        strategy = MACD(self._trading_gui._src)

        s = strategy.trade(price=candle,
                           slow_ema=slow_ema,
                           fast_ema=fast_ema,
                           signal_ema=signal_ema,
                           margin_portion=self._trading_gui._margin,
                           initial_capital=self._trading_gui._initial_capital,
                           tp=self._trading_gui._tp,
                           sl=self._trading_gui._sl,
                           commission_rate=self._trading_gui._commission_rate)

        if not s:
            QMessageBox.warning(self._tab, "Warning", "Trading met with failure.")
            return

        QMessageBox.information(self._tab, "Warning", "Trading successfully finished.")
        canvas = FigureCanvasQTAgg(strategy._report_graph())

        self._report_graph.addWidget(canvas)

        # Display the final results dashboard
        results_panel = self._create_final_results_panel(strategy._statistics)
        self._report_detail.addWidget(results_panel)

    def __check_fields(self):

        window_format = r"^\d+$"
        slow_ema = self._slow_ema_edit.text().strip()
        fast_ema = self._fast_ema_edit.text().strip()
        signal_ema = self._signal_ema_edit.text().strip()

        # Slow EMA window
        if not slow_ema:
            QMessageBox.warning(self._tab, "Warning", "Slow EMA Window can not be empty")
            return False

        if not re.search(window_format, slow_ema):
            QMessageBox.warning(self._tab, "Warning", "Slow EMA Window must be a positive interger number")
            return False

        # Fast EMA window
        if not fast_ema:
            QMessageBox.warning(self._tab, "Warning", "Fast EMA Window can not be empty")
            return False

        if not re.search(window_format, fast_ema):
            QMessageBox.warning(self._tab, "Warning", "Fast EMA Window must be a positive interger number")
            return False

        # Signal EMA window
        if not signal_ema:
            QMessageBox.warning(self._tab, "Warning", "Signal EMA Window can not be empty")
            return False

        if not re.search(window_format, signal_ema):
            QMessageBox.warning(self._tab, "Warning", "Signal EMA Window must be a positive interger number")
            return False
        
        if int(slow_ema) <= int(fast_ema):
            QMessageBox.warning(self._tab, "Warning", "Slow EMA Window must be greater than Fast EMA Window")
            return False
        
        return True


class BollingerWindow(StrategyWindow):

    def __init__(self, trading_gui):

        super().__init__()
        self._trading_gui = trading_gui
        self.__init_widgets()
        self.__setup()

    def __init_widgets(self):
        
        # Edit Widgets
        self._add_std_dev_edit = None
        self._add_sma_edit = None
        self._trade_std_dev_edit = None
        self._trade_band_edit = None

        # ComboBox Widget
        self._add_sma_candle_combo = None
        self._trade_candle_combo = None

        # Button Widget
        self._add_sma_button = None
        self._trade_button = None

        # List Widget
        self._band_list = None

    def __setup(self):

        master_layout     = QVBoxLayout()
        right_vbox        = QVBoxLayout()
        left_vbox         = QVBoxLayout()
        upper_hbox        = QHBoxLayout()
        self._report_area = QHBoxLayout()

        ###################### Upper Hbox ######################

        # Left Vbox
        hbox   = QHBoxLayout()
        lgroup = QGroupBox("Add Bollinger SMA")
        lform  = QFormLayout()
        lform.setRowWrapPolicy(QFormLayout.WrapAllRows)

        std_dev_label   = QLabel("Standard Deviations")
        window_label    = QLabel("Window")
        candle_label    = QLabel("Candle Type")

        self._add_std_dev_edit = QLineEdit("2")
        self._add_sma_edit     = QLineEdit()

        self._add_sma_candle_combo   = QComboBox()
        self._add_sma_candle_combo.addItems(self._CANDLE_TYPE)

        lform.addRow(std_dev_label, self._add_std_dev_edit)
        lform.addRow(window_label, self._add_sma_edit)
        lform.addRow(candle_label, self._add_sma_candle_combo)

        self._band_list = QListWidget()
        hbox.addWidget(self._band_list)

        self._add_sma_button = QPushButton("Add Bollinger SMA")
        self._add_sma_button.clicked.connect(self.__add_bands)
        hbox.addWidget(self._add_sma_button)

        lform.addRow(hbox)
        lgroup.setLayout(lform)
        left_vbox.addWidget(lgroup)
        upper_hbox.addLayout(left_vbox)

        # Right Vbox
        hbox2  = QHBoxLayout()
        rgroup = QGroupBox("Strategy Setup")
        rform  = QFormLayout()
        rform.setRowWrapPolicy(QFormLayout.WrapAllRows)
        band_label           = QLabel("Band Window")
        trade_candle_label   = QLabel("Candle Type")
        trade_std_dev_label  = QLabel("Standard Deviations")
        
        self._trade_std_dev_edit   = QLineEdit("2")
        self._trade_band_edit      = QLineEdit("20")

        self._trade_std_dev_edit.setPlaceholderText("Enter Number of Standard Deviations")
        self._trade_band_edit.setPlaceholderText("Enter Band Window")

        self._trade_candle_combo = QComboBox()
        self._trade_candle_combo.addItems(self._CANDLE_TYPE)
        self._trade_candle_combo.setCurrentText("Close")

        rform.addRow(trade_std_dev_label, self._trade_std_dev_edit)
        rform.addRow(band_label, self._trade_band_edit)
        rform.addRow(trade_candle_label, self._trade_candle_combo)
        hbox2.addStretch()
        self._trade_button = QPushButton("Start Trading")
        hbox2.addWidget(self._trade_button)
        self._trade_button.clicked.connect(self.__trade)
        rform.addRow(hbox2)

        rgroup.setLayout(rform)
        right_vbox.addWidget(rgroup)
        upper_hbox.addLayout(right_vbox)

        master_layout.addLayout(upper_hbox, 1)

        ###################### Lower Hbox ######################
        self._report_graph = QVBoxLayout()
        self._report_detail = QVBoxLayout()
        self._report_area.addLayout(self._report_graph, 3)
        self._report_area.addLayout(self._report_detail, 1)
        master_layout.addLayout(self._report_area, 3)
        self._tab.setLayout(master_layout)

    def __add_bands(self):

        window = self._add_sma_edit.text().strip()
        self._add_sma_edit.setText(window)

        std_dev = self._add_std_dev_edit.text().strip()
        self._add_std_dev_edit.setText(std_dev)

        if not std_dev:
            QMessageBox.warning(self._tab, "Warning", "Standard Deviation cannot be empty.")
            # clear previous reports
            self._clear_report()
            return False

        if not window:
            QMessageBox.warning(self._tab, "Warning", "SMA window cannot be empty.")
            # clear previous reports
            self._clear_report()
            return False

        try:
            window = int(window)
            if window <= 0:
                # clear previous reports
                self._clear_report()
                raise ValueError
            
        except ValueError:
            QMessageBox.warning(self._tab, "Warning", "SMA window must be a positive integer.")
            # clear previous reports
            self._clear_report()
            return False

        try:
            std_dev = int(std_dev)
            if std_dev <= 0:
                # clear previous reports
                self._clear_report()
                raise ValueError

        except ValueError:
            QMessageBox.warning(self._tab, "Warning", "Standard Deviation must be a positive integer.")
            # clear previous reports
            self._clear_report()
            return False

        candle_type = self._add_sma_candle_combo.currentText()
        std_dev = self._add_std_dev_edit.text()
        item = f"{candle_type}-{window}-{std_dev}"

        for i in range(self._band_list.count()):
            if self._band_list.item(i).text() == item:
                # clear previous reports
                self._clear_report()
                return False

        self._band_list.addItem(item)

    def __trade(self):

        # clear previous reports
        self._clear_report()

        if not self.__check_fields():
            return 
        
        if self._trading_gui._src is None:
            QMessageBox.warning(self._tab, "Warning", "Trading met with failure! There is no data so check the Binance.")
            return

        if self._trading_gui._initial_capital is None:
            QMessageBox.warning(self._tab, "Warning", "Trading met with failure! Check Settings.")
            return

        window     = int(self._trade_band_edit.text())
        std_dev    = int(self._trade_std_dev_edit.text())
        candle     = self._trade_candle_combo.currentText()

        strategy = BollingerBand(self._trading_gui._src)

        band_list = [self._band_list.item(i).text().strip() for i in range(self._band_list.count())]

        chosen_band = f"{candle}-{window}-{std_dev}"
        if chosen_band not in band_list:
            QMessageBox.warning(self._tab, "Warning", f"Trading met with failure! there is no {chosen_band} Bollinger SMA Band.")
            return
        
        if not band_list:
            QMessageBox.warning(self._tab, "Warning", "Trading met with failure! There is no Bollinger SMA.")
            return

        column_names = strategy._data.columns

        for i in band_list:
            candle_type, window, std_dev = i.split("-")
            window = int(window)
            std_dev = int(std_dev)

            if f"SMA-{candle_type}{window}-Dev{std_dev}" not in column_names: 
                if not strategy.add_bands(price=candle, window=window, num_std_dev=std_dev):
                    QMessageBox.warning(self._tab, "Warning", "Trading met with failure! there is no SMA Window.")
                    return

        s = strategy.trade(price=candle,
                           window=window,
                           num_std_dev=std_dev,
                           margin_portion=self._trading_gui._margin,
                           initial_capital=self._trading_gui._initial_capital,
                           tp=self._trading_gui._tp,
                           sl=self._trading_gui._sl,
                           commission_rate=self._trading_gui._commission_rate)
        
        if not s:
            QMessageBox.warning(self._tab, "Warning", "Trading met with failure.")
            return

        QMessageBox.information(self._tab, "Warning", "Trading successfully finished.")
        canvas = FigureCanvasQTAgg(strategy._report_graph())

        self._report_graph.addWidget(canvas)

        # Display the final results dashboard
        results_panel = self._create_final_results_panel(strategy._statistics)
        self._report_detail.addWidget(results_panel)

    def __check_fields(self):

        window_format = r"^\d+$"
        std_dev = self._trade_std_dev_edit.text().strip()
        band = self._trade_band_edit.text().strip()

        # standard deviation
        if not std_dev:
            QMessageBox.warning(self._tab, "Warning", "Standard Deviation can not be empty")
            return False
        
        if not re.search(window_format, std_dev):
            QMessageBox.warning(self._tab, "Warning", "Standard Deviation must be a positive interger number")
            return False

        if float(std_dev) <= 0:
            QMessageBox.warning(self._tab, "Warning", "Standard Deviation must be a positive number")
            return False    

        # band window
        if not band:
            QMessageBox.warning(self._tab, "Warning", "Band Window can not be empty")
            return False

        if not re.search(window_format, band):
            QMessageBox.warning(self._tab, "Warning", "Band Window must be a positive interger number")
            return False

        if int(band) <= 0:
            QMessageBox.warning(self._tab, "Warning", "Band Window must be a positive integer number")
            return False
        
        return True
    

class DonchianWindow(StrategyWindow):

    def __init__(self, trading_gui):
        
        super().__init__()
        self._trading_gui = trading_gui
        self.__init_widgets()
        self.__setup()

    def __init_widgets(self):

        # Edit Widgets
        self._add_channel_edit = None
        self._trade_channel_edit = None

        # ComboBox Widget
        self._trade_candle_combo = None

        # Button Widget
        self._add_channel_button = None
        self._trade_button = None

        # List Widget
        self._channel_list = None

    def __setup(self):
        
        master_layout     = QVBoxLayout()
        right_vbox        = QVBoxLayout()
        left_vbox         = QVBoxLayout()
        upper_hbox        = QHBoxLayout()
        self._report_area = QHBoxLayout()

        ###################### Upper Hbox ######################

        # Left Vbox
        hbox   = QHBoxLayout()
        lgroup = QGroupBox("Add Channel")
        lform  = QFormLayout()
        lform.setRowWrapPolicy(QFormLayout.WrapAllRows)

        window_label    = QLabel("Window")

        self._add_channel_edit   = QLineEdit()
        
        self._add_channel_candle_combo   = QComboBox()
        self._add_channel_candle_combo.addItems(self._CANDLE_TYPE)

        lform.addRow(window_label, self._add_channel_edit)

        self._channel_list = QListWidget()
        hbox.addWidget(self._channel_list)

        self._add_channel_button = QPushButton("Add Channel")
        self._add_channel_button.clicked.connect(self.__add_channels)
        hbox.addWidget(self._add_channel_button)

        lform.addRow(hbox)
        lgroup.setLayout(lform)
        left_vbox.addWidget(lgroup)
        upper_hbox.addLayout(left_vbox)

        # Right Vbox
        hbox2  = QHBoxLayout()
        rgroup = QGroupBox("Strategy Setup")
        rform  = QFormLayout()
        rform.setRowWrapPolicy(QFormLayout.WrapAllRows)
        channel_window_label = QLabel("Channel Window")
        trade_candle_label = QLabel("Candle Type")

        self._trade_channel_edit    = QLineEdit("14")

        self._trade_channel_edit.setPlaceholderText("Enter Channel Window")

        self._trade_candle_combo = QComboBox()
        self._trade_candle_combo.addItems(self._CANDLE_TYPE)
        self._trade_candle_combo.setCurrentText("Close")

        rform.addRow(channel_window_label, self._trade_channel_edit)
        rform.addRow(trade_candle_label, self._trade_candle_combo)


        hbox2.addStretch()
        self._trade_button = QPushButton("Start Trading")
        hbox2.addWidget(self._trade_button)
        self._trade_button.clicked.connect(self.__trade)
        rform.addRow(hbox2)

        rgroup.setLayout(rform)
        right_vbox.addWidget(rgroup)
        upper_hbox.addLayout(right_vbox)

        master_layout.addLayout(upper_hbox, 1)

        ###################### Lower Hbox ######################
        self._report_graph = QVBoxLayout()
        self._report_detail = QVBoxLayout()
        self._report_area.addLayout(self._report_graph, 3)
        self._report_area.addLayout(self._report_detail, 1)
        master_layout.addLayout(self._report_area, 3)
        self._tab.setLayout(master_layout)

    def __add_channels(self):

        channel = self._add_channel_edit.text().strip()
        self._add_channel_edit.setText(channel)

        if not channel:
            QMessageBox.warning(self._tab, "Warning", "Channel cannot be empty.")
            # clear previous reports
            self._clear_report()
            return False

        try:
            window = int(channel)
            if window <= 0:
                # clear previous reports
                self._clear_report()
                raise ValueError
            
        except ValueError:
            QMessageBox.warning(self._tab, "Warning", "Channel window must be a positive integer.")
            # clear previous reports
            self._clear_report()
            return False

        item = f"{window}"

        for i in range(self._channel_list.count()):
            if self._channel_list.item(i).text() == item:
                # clear previous reports
                self._clear_report()
                return False

        self._channel_list.addItem(item)
    
    def __trade(self):

        # clear previous reports
        self._clear_report()

        if not self.__check_fields():
            return 
        
        if self._trading_gui._src is None:
            QMessageBox.warning(self._tab, "Warning", "Trading met with failure! There is no data so check the Binance.")
            return

        if self._trading_gui._initial_capital is None:
            QMessageBox.warning(self._tab, "Warning", "Trading met with failure! Check Settings.")
            return

        trade_channel  = int(self._trade_channel_edit.text())
        candle         = self._trade_candle_combo.currentText()

        strategy = DonchianChannel(self._trading_gui._src)

        channel_list = [self._channel_list.item(i).text().strip() for i in range(self._channel_list.count())]

        if not channel_list:
            QMessageBox.warning(self._tab, "Warning", "Trading met with failure! there is no Donchian Channel Window.")
            return

        total_channels = self._channel_list.count()
        for i in range(total_channels):
            window = int(self._channel_list.item(i).text().strip())
            channel_name = f"MiddleChannel-{window}"
            
            if channel_name not in strategy._data.columns:               
                if not strategy.add_channels(window=window):
                    QMessageBox.warning(self._tab, "Warning", "Trading met with failure! there is no Donchian Channel Window.")
                    return

        s = strategy.trade(price=candle,
                           window=trade_channel,
                           margin_portion=self._trading_gui._margin,
                           initial_capital=self._trading_gui._initial_capital,
                           tp=self._trading_gui._tp,
                           sl=self._trading_gui._sl,
                           commission_rate=self._trading_gui._commission_rate)
        
        if not s:
            QMessageBox.warning(self._tab, "Warning", "Trading met with failure.")
            return

        QMessageBox.information(self._tab, "Warning", "Trading successfully finished.")
        canvas = FigureCanvasQTAgg(strategy._report_graph())

        self._report_graph.addWidget(canvas)

        # Display the final results dashboard
        results_panel = self._create_final_results_panel(strategy._statistics)
        self._report_detail.addWidget(results_panel)

    def __check_fields(self):

        window_format = r"^\d+$"
        channel = self._trade_channel_edit.text().strip()

        # channel window
        if not channel:
            QMessageBox.warning(self._tab, "Warning", "Channel Window can not be empty")
            return False

        if not re.search(window_format, channel):
            QMessageBox.warning(self._tab, "Warning", "Channel Window must be a positive integer number")
            return False

        if int(channel) <= 0:
            QMessageBox.warning(self._tab, "Warning", "Channel Window must be a positive integer number")
            return False
        
        return True


class  TradingGUI(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Trading Strategies")
        self.setGeometry(250, 100, 1500, 900)

        self._src = None
        self._is_trading = False
        self._initial_capital = None
        self._margin = None
        self._tp = None
        self._sl = None
        self._commission_rate = None

        self.__tabs_init()
        self.__tabs_setup()
        self.ui()

    def __tabs_init(self):

        self._mavg_window = MovingAverageWindow(self)
        self._rsi_window = RSIWindow(self)
        self._macd_window = MACDWindow(self)
        self._bollinger_window = BollingerWindow(self)
        self._donchian_window = DonchianWindow(self)

        self.tab = QTabWidget(self)
        self.binance_tab = QWidget()
        self.rsi_tab = QWidget()
        self.macd_tab = QWidget()
        self.bollinger_tab = QWidget()
        self.donchian_tab = QWidget()
        self.hybrid_tab = QWidget()
        self.settings_tab = QWidget()

        self.tab.addTab(self.binance_tab, "Connect Binance")
        self.tab.addTab(self.settings_tab, "Settings")
        self.tab.addTab(self._mavg_window._tab, "Moving Average")
        self.tab.addTab(self._rsi_window._tab, "RSI")
        self.tab.addTab(self._macd_window._tab, "MACD")
        self.tab.addTab(self._bollinger_window._tab, "Bollinger Band")
        self.tab.addTab(self._donchian_window._tab, "Donchian Channel")
        self.tab.addTab(self.hybrid_tab, "Hybrid")

    def __tabs_setup(self):

        self.__binance_tab()
        self.__settings_tab()

    def ui(self):
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.tab)
        self.setLayout(main_layout)
        self.show()

    def __binance_tab(self):
        vbox = QVBoxLayout()
        hbox = QHBoxLayout()
        result_box = QHBoxLayout()

        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.WrapAllRows)

        currecny_label        = QLabel("Currency")
        start_t_label         = QLabel("Start Time")
        stop_t_label          = QLabel("Stop Time")
        time_frame_label      = QLabel("Time Frame")

        self._currecny_edit   = QLineEdit("BTCUSDT")
        self._start_t_edit    = QLineEdit("2022-01-01")
        self._stop_t_edit     = QLineEdit("2023-01-01")

        self._currecny_edit.setPlaceholderText("Enter Currency like BTCUSDT")
        self._start_t_edit.setPlaceholderText("Enter Start Time like 2022-01-01")
        self._stop_t_edit.setPlaceholderText("Enter Stop Time like 2022-01-01")

        self._time_frame = QComboBox()
        TIME_FRAMES = ["1s", 
                      "1min", "3min", "5min", "15min", "30min",
                      "1h", "2h", "4h", "6h", "8h",
                      "1d", "3d",
                      "1w",
                      "1m"]
        self._time_frame.addItems(TIME_FRAMES)
        self._time_frame.setCurrentText("1d")
        
        form.addRow(currecny_label, self._currecny_edit)
        form.addRow(start_t_label, self._start_t_edit)
        form.addRow(stop_t_label, self._stop_t_edit)
        form.addRow(time_frame_label, self._time_frame)

        hbox.addStretch()
        self._connect_buttom = QPushButton("Connect")
        hbox.addWidget(self._connect_buttom)
        self._connect_buttom.clicked.connect(self.__connect_binance)
        vbox.addLayout(hbox)

        self._connection_result_label = QLabel()
        result_box.addWidget(self._connection_result_label)
        vbox.addLayout(result_box)

        form.addRow(vbox)

        self.binance_tab.setLayout(form)

    def __connect_binance(self):

        text = ""
        self._connection_result_label.setText(text)
        text = self._connection_result_label.text() + "\n" + "⌛ Getting Data ..."
        self._connection_result_label.setText(text)

        if not self.__check_connect_field():
            self._connection_result_label.setText("❌ ERROR: Getting Data met with failure.")
            return 
        
        currency = self._currecny_edit.text().strip()
        t1 = self._start_t_edit.text().strip()
        t2 = self._stop_t_edit.text().strip()
        time_frame = self._time_frame.currentText()
        
        src_name = f"{currency}_{t1}_{t2}_{time_frame}"

        try:
            with open(f"{src_name}.pkl", "rb") as f:
                self._src = pickle.load(f)
                text = self._connection_result_label.text() + "\n" + "📂 Loaded data from file."
                self._connection_result_label.setText(text)
        
        except:
            try:
                text = self._connection_result_label.text() + "\n" + "🔄️ Downloading Data from Binance ..."
                self._connection_result_label.setText(text)
                self._src = ConnectBinance(currency=currency,
                                           start_time=t1,
                                           stop_time=t2,
                                           timeframe=time_frame)
            except:     
                text = self._connection_result_label.text() + "\n" + "❌ ERROR: Data was not downloaded. Check your internet connection"
                self._connection_result_label.setText(text)
                return
            
            if self._src._ready:
                text = self._connection_result_label.text() + "\n" + "✅ Data downloaded from Binance successfully."
                self._connection_result_label.setText(text)
                try:
                    with open(f"{src_name}.pkl", "wb") as f:
                        pickle.dump(self._src, f)
                        text = self._connection_result_label.text() + "\n" + "💾 Data saved to file."
                    self._connection_result_label.setText(text)
                    
                except:
                    text = self._connection_result_label.text() + "\n" + "❌ ERROR: could not open the file"
                    self._connection_result_label.setText(text)
                    self._src._ready = False

            else:
                text = self._connection_result_label.text() + "\n" + "❌ ERROR: Data was not downloaded."
                self._connection_result_label.setText(text)

    def __check_connect_field(self):

        currency = self._currecny_edit.text().strip()
        t1 = self._start_t_edit.text().strip()
        t2 = self._stop_t_edit.text().strip()

        # currency
        if not currency:
            QMessageBox.warning(self, "warning", "Currecncy can not be empty")
            return False

        if not re.search(r"^\D*$", currency):
            QMessageBox.warning(self, "warning", "Currecncy is not in a valid format")
            return False

        # start time
        if not t1:
            QMessageBox.warning(self, "warning", "Start Time can not be empty")
            return False

        time_format = r"^([\d]{4})-([\d]{2})-([\d]{2})$"
        t1_s = re.search(time_format, t1)
        
        if not t1_s:
            QMessageBox.warning(self, "warning", "Start Time is not in a valid format")
            return False

        # stop time
        if not t2:
            QMessageBox.warning(self, "warning", "Stop Time can not be empty")
            return False

        t2_s = re.search(time_format, t2)
        
        if not t2_s:
            QMessageBox.warning(self, "warning", "Stop Time is not in a valid format")
            return False

        return True

    def __settings_tab(self):

        hbox = QHBoxLayout()
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.WrapAllRows)

        initial_capital_label   = QLabel("Initial Capital")
        margin_label            = QLabel("Margin Portion")
        tp_label                = QLabel("Take Profit")
        sl_label                = QLabel("Stop Loss")
        commission_rate_label   = QLabel("Commission Rate")

        self._setting_init_capital = QLineEdit("1000")
        self._setting_marging = QLineEdit("0.2")
        self._settig_tp = QLineEdit("0.015")
        self._setting_sl = QLineEdit("0.005")
        self._setting_commission_rate = QLineEdit("0.001")

        self._setting_init_capital.setPlaceholderText("Enter Initial Capital in dollar")
        self._setting_marging.setPlaceholderText("Enter Margin Portion between 0-1")
        self._settig_tp.setPlaceholderText("Enter Take Profit between 0-1")
        self._setting_sl.setPlaceholderText("Enter Stop Loss between 0-1")
        self._setting_commission_rate.setPlaceholderText("Enter Commission Rate between 0-1")


        self._setting_save = QPushButton("Saving")
        self._setting_save.clicked.connect(self.__save_setting)
        hbox.addStretch()
        hbox.addWidget(self._setting_save)

        form.addRow(initial_capital_label, self._setting_init_capital)
        form.addRow(margin_label, self._setting_marging)
        form.addRow(tp_label, self._settig_tp)
        form.addRow(sl_label, self._setting_sl)
        form.addRow(commission_rate_label, self._setting_commission_rate)
        form.addRow(hbox)

        self.settings_tab.setLayout(form)

    def __save_setting(self):

        err = False
        initial_capital = self._setting_init_capital.text().strip()
        margin = self._setting_marging.text().strip()
        tp = self._settig_tp.text().strip()
        sl = self._setting_sl.text().strip()
        commission = self._setting_commission_rate.text().strip()

        if self._is_trading:
            QMessageBox.warning(self, "Warning", "Trading is in progress.")
            return

        # initial capacity
        if not initial_capital:
            QMessageBox.warning(self, "Warning", "Initial Capital Cannot be empty.")
            return

        try:
            initial_capital = float(initial_capital)
            if not initial_capital > 0:
                err = True
        except:
            err = True
        finally:
            if err:
                QMessageBox.warning(self, "Warning", "Initial Capital Must be a positive number.")
                return

        # marging
        if not margin:
            QMessageBox.warning(self, "Warning", "Margin Cannot be empty.")
            return

        try:
            margin = float(margin)
            if not 0 < margin <= 1:
                err = True 
        except:
            err = True
        finally:
            if err:
                QMessageBox.warning(self, "Warning", "Marging Must be between 0-1.")
                return

        # tp
        if not tp:
            QMessageBox.warning(self, "Warning", "Take Profit Cannot be empty.")
            return

        try:
            tp = float(tp)
            if not 0 < tp <= 1:
                err = True
        except:
            err = True
        finally:
            if err:
                QMessageBox.warning(self, "Warning", "Take Profit Must be between 0-1.")
                return        

        # sl
        if not sl:
            QMessageBox.warning(self, "Warning", "Stop Loss Cannot be empty.")
            return

        try:
            sl = float(sl)
            if not 0 < sl <= 1:
                err = True
        except:
            err = True
        finally:
            if err:
                QMessageBox.warning(self, "Warning", "Stop Loss Must be between 0-1.")
                return        

        # commission
        if not commission:
            QMessageBox.warning(self, "Warning", "Commission Rate Cannot be empty.")
            return

        try:
            commission = float(commission)
            if not 0 < commission <= 1:
                err = True
        except:
            err = True
        finally:
            if err:
                QMessageBox.warning(self, "Warning", "Commission Rate Must be between 0-1.")
                return        

        # save the changes
        self._initial_capital = initial_capital
        self._margin = margin
        self._tp = tp
        self._sl = sl
        self._commission_rate = commission

        QMessageBox.information(self, "Saved Settings", "Settings saved successfully.")


def main():
    app = QApplication(sys.argv)
    window = TradingGUI()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
