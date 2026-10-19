import sys
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtWidgets import QGroupBox, QFormLayout, QTabWidget, QMessageBox
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout
from PyQt5.QtWidgets import QLabel, QPushButton, QComboBox, QLineEdit, QListWidget
from strategies import *
import pickle


class  TradingGUI(QWidget):

    __CANDLE_TYPE = ["Open", "Close", "High", "Low"]

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

        self.tab = QTabWidget(self)
        self.binance_tab = QWidget()
        self.mavg_tab = QWidget()
        self.rsi_tab = QWidget()
        self.macd_tab = QWidget()
        self.bollinger_tab = QWidget()
        self.donchian_tab = QWidget()
        self.hybrid_tab = QWidget()
        self.settings_tab = QWidget()

        self.tab.addTab(self.binance_tab, "Connect Binance")
        self.tab.addTab(self.settings_tab, "Settings")
        self.tab.addTab(self.mavg_tab, "Moving Average")
        self.tab.addTab(self.rsi_tab, "RSI")
        self.tab.addTab(self.macd_tab, "MACD")
        self.tab.addTab(self.bollinger_tab, "Bollinger Band")
        self.tab.addTab(self.donchian_tab, "Donchian Channel")
        self.tab.addTab(self.hybrid_tab, "Hybrid")

    def __tabs_setup(self):
        self.__binance_tab()
        self.__mavg_tab()
        self.__settings_tab()

    def ui(self):
        main_layout = QVBoxLayout()

        ############ tab2 #########
        hbox2 = QHBoxLayout()
        # self.btn = QPushButton("Click Me")
        # self.btn.clicked.connect(self.btn_clicked)
        # hbox2.addWidget(self.btn)
        # self.tab2.setLayout(hbox2)

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
        
        src_name = f"{self._currecny_edit.text()}_{self._start_t_edit.text()}_{self._stop_t_edit.text()}_{self._time_frame.currentText()}"

        try:
            with open(f"{src_name}.pkl", "rb") as f:
                self._src = pickle.load(f)
                text = self._connection_result_label.text() + "\n" + "📂 Loaded data from file."
                self._connection_result_label.setText(text)
        
        except:
            try:
                text = self._connection_result_label.text() + "\n" + "🔄️ Downloading Data from Binance ..."
                self._connection_result_label.setText(text)
                self._src = ConnectBinance(currency=self._currecny_edit.text(),
                                        start_time=self._start_t_edit.text(),
                                        stop_time=self._stop_t_edit.text(),
                                        timeframe=self._time_frame.currentText())
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

        if not self._currecny_edit.text().strip():
            QMessageBox.warning(self, "warning", "Currecncy can not be empty")
            return False
        
        if not self._start_t_edit.text().strip():
            QMessageBox.warning(self, "warning", "Start Time can not be empty")
            return False
        
        if not self._stop_t_edit.text().strip():
            QMessageBox.warning(self, "warning", "Stop Time can not be empty")
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

    def __mavg_tab(self):

        master_layout = QVBoxLayout()

        upper_hbox = QHBoxLayout()
        lower_hbox = QHBoxLayout()

        right_vbox = QVBoxLayout()
        left_vbox  = QVBoxLayout()

        ###################### Upper Hbox ######################

        # Left Vbox
        hbox  = QHBoxLayout()
        lgroup = QGroupBox("Add Moving Average")
        lform  = QFormLayout()
        lform.setRowWrapPolicy(QFormLayout.WrapAllRows)

        CANDLE_TYPES = ("Close", "Open", "High", "Low")
        window_label    = QLabel("Window")
        candle_label    = QLabel("Candle Type")

        self._mavg_window_edit   = QLineEdit()
        
        self._candle_type   = QComboBox()
        self._candle_type.addItems(CANDLE_TYPES)

        lform.addRow(window_label, self._mavg_window_edit)
        lform.addRow(candle_label, self._candle_type)

        self.sma_list = QListWidget()
        hbox.addWidget(self.sma_list)

        self._mavg_add_button = QPushButton("Add SMA")
        self._mavg_add_button.clicked.connect(self.__add_sma)
        hbox.addWidget(self._mavg_add_button)

        lform.addRow(hbox)
        lgroup.setLayout(lform)
        left_vbox.addWidget(lgroup)
        upper_hbox.addLayout(left_vbox)

        # Right Vbox
        hbox2 = QHBoxLayout()
        rgroup = QGroupBox("Strategy Setup")
        rform  = QFormLayout()
        rform.setRowWrapPolicy(QFormLayout.WrapAllRows)

        shorter_window_label    = QLabel("Shorter SMA Window")
        longer_window_label     = QLabel("Longer SMA Window")
        trade_candle_label      = QLabel("Candle Type")

        self._mavg_shorter_sma_edit = QLineEdit()
        self._mavg_longer_sma_edit = QLineEdit()

        self._mavg_shorter_sma_edit.setPlaceholderText("Enter Shorter SMA Window")
        self._mavg_longer_sma_edit.setPlaceholderText("Enter Longer SMA Window")

        self._mavg_trade_candle_type = QComboBox()
        self._mavg_trade_candle_type.addItems(TradingGUI.__CANDLE_TYPE)
        self._mavg_trade_candle_type.setCurrentText("Close")

        rform.addRow(shorter_window_label, self._mavg_shorter_sma_edit)
        rform.addRow(longer_window_label, self._mavg_longer_sma_edit)
        rform.addRow(trade_candle_label, self._mavg_trade_candle_type)

        hbox2.addStretch()
        self._mavg_start_trade = QPushButton("Start Trading")
        hbox2.addWidget(self._mavg_start_trade)
        self._mavg_start_trade.clicked.connect(self.__mavg)
        rform.addRow(hbox2)

        rgroup.setLayout(rform)
        right_vbox.addWidget(rgroup)
        upper_hbox.addLayout(right_vbox)

        master_layout.addLayout(upper_hbox)

        ###################### Lower Hbox ######################
        self._mavg_trade_result_label = QLabel("")
        lower_hbox.addWidget(self._mavg_trade_result_label)

        master_layout.addLayout(lower_hbox)
        self.mavg_tab.setLayout(master_layout)

    def __add_sma(self):

        window = self._mavg_window_edit.text().strip()

        if not window:
            QMessageBox.warning(self, "Warning", "SMA window cannot be empty.")
            return

        try:
            window = int(window)
            if window <= 0:
                raise ValueError
            
        except ValueError:
            QMessageBox.warning(
                self, "Warning", "SMA window must be a positive integer."
            )
            return

        candle_type = self._candle_type.currentText()
        self.sma_list.addItem(f"{candle_type}-{window}")

    def __mavg(self):

        self._mavg_trade_result_label.setText("Trading Started ...")

        if self._src is None:
            self._mavg_trade_result_label.setText("Trading met with failure! There is no data so check the Binance.")
            return

        if self._initial_capital is None:
            self._mavg_trade_result_label.setText("Trading met with failure! Check Settings.")
            return

        candle = self._mavg_trade_candle_type.currentText()
        short_window = self._mavg_shorter_sma_edit.text()
        long_window = self._mavg_longer_sma_edit.text()
        windows = (short_window, long_window)

        print("start trading")

        mavg_strategy = MovingAverage(self._src)
        mavg_strategy.add_sma(windows)

        s = mavg_strategy.trade(price=candle,
                                windows=windows,
                                margin_portion=self._margin,
                                initial_capital=self._initial_capital,
                                tp=self._tp,
                                sl=self._sl,
                                commission_rate=self._commission_rate)
        if s is None:
            self._mavg_trade_result_label.setText("Trading met with failure.")
            return

        self._mavg_trade_result_label.setText("Trading successfully finished.")
        s.report()

def main():
    app = QApplication(sys.argv)
    window = TradingGUI()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
