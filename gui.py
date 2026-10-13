import sys
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtWidgets import QFormLayout, QTabWidget, QMessageBox
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout
from PyQt5.QtWidgets import QLabel, QPushButton, QComboBox, QLineEdit
from strategies import *
import pickle


class  Window(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Trading Strategies")
        self.setGeometry(250, 100, 1500, 900)

        self._src = None

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

        self.tab.addTab(self.binance_tab, "Connect Binance")
        self.tab.addTab(self.mavg_tab, "Moving Average")
        self.tab.addTab(self.rsi_tab, "RSI")
        self.tab.addTab(self.macd_tab, "MACD")
        self.tab.addTab(self.bollinger_tab, "Bollinger Band")
        self.tab.addTab(self.donchian_tab, "Donchian Channel")
        self.tab.addTab(self.hybrid_tab, "Hybrid")

    def __tabs_setup(self):
        self.__binance_tab()

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

        self._currecny_edit   = QLineEdit()
        self._start_t_edit    = QLineEdit()
        self._stop_t_edit     = QLineEdit()

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

        if not self.__check_connect_field():
            self._connection_result_label.setText("Getting Data met with failure.")
            return 
        
        src_name = f"{self._currecny_edit.text()}_{self._start_t_edit.text()}_{self._stop_t_edit.text()}_{self._time_frame.currentText()}"

        try:
            with open(f"{src_name}.pkl", "rb") as f:
                self._src = pickle.load(f)
                text = self._connection_result_label.text() + "\n" + "📂 Loaded data from file."
                self._connection_result_label.setText(text)
        
        except:
            text = self._connection_result_label.text() + "\n" + "🔄️ Downloading Data from Binance ..."
            self._connection_result_label.setText(text)
            self._src = ConnectBinance(currency=self._currecny_edit.text(),
                                      start_time=self._start_t_edit.text(),
                                      stop_time=self._stop_t_edit.text(),
                                      timeframe=self._time_frame.currentText())            

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

    def __mavg(self):
        pass



def main():
    app = QApplication(sys.argv)
    window = Window()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
