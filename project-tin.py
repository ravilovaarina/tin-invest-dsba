import sys
import sqlite3
import hashlib
from datetime import timedelta
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QLineEdit, QPushButton, QVBoxLayout,
    QWidget, QComboBox, QMessageBox, QStackedWidget, QRadioButton, QButtonGroup
)
from tinkoff.invest import Client, RequestError, CandleInterval, InstrumentStatus
from tinkoff.invest.utils import now
from tqdm import tqdm
import numpy as np

# Токен Tinkoff API
TOKEN = 't.VxcncZUimvL_m-QfJ7a4dDOaI4CmyQhW3rpA_auRQSnYX-0n9a6UfoyfOZlN9wPHvXmR0_fK5tKJOhVh3T_ldw'

# Инициализация базы данных для хранения информации о пользователях
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    # Создание таблицы пользователей, если она не существует
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        username TEXT PRIMARY KEY,
                        password TEXT
                    )''')
    conn.commit()
    conn.close()

# Функция для хеширования пароля (SHA-256)
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


class PortfolioApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Portfolio Recommendation & Bank Deposits")
        self.setGeometry(300, 300, 400, 600)

        # Инициализация базы данных пользователей
        init_db()

        # Стек для управления отображением различных экранов (вход, регистрация, основное окно)
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        # Создание виджетов для экрана входа, регистрации и основного приложения
        self.login_widget = self.create_login_widget()
        self.registration_widget = self.create_registration_widget()
        self.main_widget = self.create_main_widget()

        # Добавление виджетов в стек
        self.stacked_widget.addWidget(self.login_widget)
        self.stacked_widget.addWidget(self.registration_widget)
        self.stacked_widget.addWidget(self.main_widget)

    # Создание виджета для экрана входа
    def create_login_widget(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Поля ввода для логина и пароля
        self.login_username_input = QLineEdit()
        self.login_password_input = QLineEdit()
        self.login_password_input.setEchoMode(QLineEdit.Password)

        # Кнопка для входа
        login_button = QPushButton("Login")
        login_button.clicked.connect(self.login)

        # Кнопка для перехода к регистрации
        register_button = QPushButton("Register")
        register_button.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.registration_widget))

        layout.addWidget(QLabel("Username:"))
        layout.addWidget(self.login_username_input)
        layout.addWidget(QLabel("Password:"))
        layout.addWidget(self.login_password_input)
        layout.addWidget(login_button)
        layout.addWidget(register_button)

        # Добавление бренда компании Kderavioli
        branding_label = QLabel("Kderavioli Investment Analyzer")
        branding_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #0077cc;")
        layout.addWidget(branding_label)

        widget.setLayout(layout)
        return widget

    # Создание виджета для экрана регистрации
    def create_registration_widget(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Заголовок с брендом Kderavioli
        branding_label = QLabel("Kderavioli Investment Analyzer")
        branding_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #0077cc;")
        layout.addWidget(branding_label)

        # Поля ввода для регистрации
        self.register_username_input = QLineEdit()
        self.register_password_input = QLineEdit()
        self.register_password_input.setEchoMode(QLineEdit.Password)

        # Кнопка для регистрации
        register_button = QPushButton("Register")
        register_button.clicked.connect(self.register)

        # Кнопка для возврата на экран входа
        back_to_login_button = QPushButton("Back to Login")
        back_to_login_button.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.login_widget))

        layout.addWidget(QLabel("Username:"))
        layout.addWidget(self.register_username_input)
        layout.addWidget(QLabel("Password:"))
        layout.addWidget(self.register_password_input)
        layout.addWidget(register_button)
        layout.addWidget(back_to_login_button)

        widget.setLayout(layout)
        return widget

    # Создание виджета для основного экрана приложения
    def create_main_widget(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Вкладка для выбора типа инвестиции (акции или депозит)
        self.investment_option_label = QLabel("Choose Investment Type:")
        layout.addWidget(self.investment_option_label)

        self.stock_radio = QRadioButton("Stocks")
        self.deposit_radio = QRadioButton("Bank Deposit")
        self.investment_type_group = QButtonGroup()
        self.investment_type_group.addButton(self.stock_radio)
        self.investment_type_group.addButton(self.deposit_radio)
        self.stock_radio.setChecked(True)  # По умолчанию выбраны акции

        layout.addWidget(self.stock_radio)
        layout.addWidget(self.deposit_radio)

        # Выпадающий список для предложенных сумм инвестиций
        self.suggested_amount_label = QLabel("Suggested Investment Amount:")
        self.suggested_amount_dropdown = QComboBox()
        self.suggested_amount_dropdown.addItems(["5000", "10000", "20000", "50000"])
        layout.addWidget(self.suggested_amount_label)
        layout.addWidget(self.suggested_amount_dropdown)

        # Поле ввода для индивидуальной суммы
        self.custom_amount_label = QLabel("Or Enter Custom Amount (RUB):")
        self.custom_amount_input = QLineEdit()
        layout.addWidget(self.custom_amount_label)
        layout.addWidget(self.custom_amount_input)

        # Выпадающий список для выбора горизонта инвестиций (краткосрочный, долгосрочный)
        self.horizon_label = QLabel("Investment Horizon:")
        self.horizon_dropdown = QComboBox()
        self.horizon_dropdown.addItems(["Short-term", "Long-term"])
        layout.addWidget(self.horizon_label)
        layout.addWidget(self.horizon_dropdown)

        # Выпадающий список для выбора категории акций
        self.category_label = QLabel("Stock Category:")
        self.category_dropdown = QComboBox()
        self.category_dropdown.addItems(["Any", "Technology", "Finance", "Healthcare", "Energy"])
        layout.addWidget(self.category_label)
        layout.addWidget(self.category_dropdown)

        # Выпадающий список для выбора страны компании
        self.country_label = QLabel("Company Country:")
        self.country_dropdown = QComboBox()
        self.country_dropdown.addItems(["Any", "Russia", "USA", "China", "Germany", "Japan"])
        layout.addWidget(self.country_label)
        layout.addWidget(self.country_dropdown)

        # Кнопка для расчета прибыли от инвестиций
        calc_button = QPushButton("Calculate Investment")
        calc_button.clicked.connect(self.calculate_investment)
        layout.addWidget(calc_button)

        # Кнопка для выхода из аккаунта
        logout_button = QPushButton("Logout")
        logout_button.clicked.connect(self.logout)
        layout.addWidget(logout_button)

        widget.setLayout(layout)
        return widget

    # Функция для входа в систему
    def login(self):
        username = self.login_username_input.text()
        password = hash_password(self.login_password_input.text())

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            self.stacked_widget.setCurrentWidget(self.main_widget)
        else:
            QMessageBox.warning(self, "Login Failed", "Incorrect username or password.")

    # Функция для регистрации нового пользователя
    def register(self):
        username = self.register_username_input.text()
        password = hash_password(self.register_password_input.text())

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            QMessageBox.information(self, "Registration Successful", "You are now logged in.")
            self.login_username_input.setText(username)
            self.login_password_input.setText(self.register_password_input.text())
            self.stacked_widget.setCurrentWidget(self.main_widget)  # Автоматический вход после регистрации
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "Registration Failed", "Username already exists.")
        finally:
            conn.close()

    # Функция для выхода из аккаунта
    def logout(self):
        self.login_username_input.clear()
        self.login_password_input.clear()
        self.stacked_widget.setCurrentWidget(self.login_widget)
    
    def get_real_time_data(self, client, category, country):
        shares = client.instruments.shares().instruments
        if category != "Any":
            shares = [s for s in shares if category.lower() in s.name.lower()]
        if country != "Any":
            shares = [s for s in shares if s.country_of_risk and s.country_of_risk.lower() == country.lower()]

        shares = [i for i in shares if i.currency == "rub"]
        real_time_prices = {}
        closes = []
        for share in tqdm(shares):
            try:
                price = client.market_data.get_last_prices(figi=[share.figi]).last_prices[0]
                real_time_prices[share.figi] = price.price.units + price.price.nano / 1e9
                
                response = client.market_data.get_candles(
                    figi=share.figi,
                    from_=now() - timedelta(days=365),
                    to=now(),
                    interval=CandleInterval.CANDLE_INTERVAL_DAY,
                )
                candles = [
                    (candle.time, candle.close.units + candle.close.nano / 1e9)
                    for candle in response.candles
                ]
                closes.extend([c[1] for c in candles])
            except RequestError as e:
                print(f"Error fetching data for {share.name}: {e}")
                continue
            

        
        return shares, real_time_prices, closes
    
    def evaluate_stocks(self, shares, real_time_prices, volatility):
        ratings = {share: np.random.rand() * 10 for share in shares}
        sorted_shares = sorted(shares, key=lambda x: ratings[x], reverse=True)
        
        return sorted_shares
    
    def build_portfolio(self, shares, real_time_prices, budget):
        portfolio = []
        for share in shares:
            price = real_time_prices.get(share.figi, 0)
            if price <= budget:
                portfolio.append((share.name, price))
                budget -= price
            if budget <= 0:
                break
        return portfolio, budget
    
    def calculate_volatility(self, closes):
        if not closes:
            print("No candles data available.")
            return 0
        

        returns = np.diff(np.log(closes))
        volatility = np.std(returns)
        print(volatility)
        return volatility

    # Функция для расчета прибыли от инвестиций
    def calculate_investment(self):
        try:
            # Получаем сумму инвестиций
            amount = float(self.custom_amount_input.text()) if self.custom_amount_input.text() else float(
                self.suggested_amount_dropdown.currentText())
            category = self.category_dropdown.currentText()
            country = self.country_dropdown.currentText()

            if self.stock_radio.isChecked():
                # Рассчитываем прибыль от инвестиций в акции
                with Client(TOKEN) as client:
                    '''tocks = client.instruments.shares()  # Получаем список акций
                    estimated_growth = amount * 1.1  # Гипотетический рост на 10%
                    profit = estimated_growth - amount
                    QMessageBox.information(self, "Stock Portfolio",
                                            f"Expected growth: {estimated_growth:.2f} RUB\n"
                                            f"Profit: {profit:.2f} RUB")'''
                    try: 
                        shares, real_time_prices, closes = self.get_real_time_data(client, category, country)
                        volatility = self.calculate_volatility(closes)
                        evaluated_shares = self.evaluate_stocks(shares, real_time_prices, volatility)
                        portfolio, remaining_budget = self.build_portfolio(evaluated_shares, real_time_prices, amount)

                        portfolio_text = "\n".join([f"{stock[0]} - {stock[1]:.2f} RUB" for stock in portfolio])
                        QMessageBox.information(self, "Stock Portfolio",
                                            f"Portfolio:\n{portfolio_text}\n\n"
                                            f"Remaining Budget: {remaining_budget:.2f} RUB")
                    except RequestError as e:
                        QMessageBox.critical(self, "API Error", f"Failed to fetch data from Tinkoff: {e}")

            elif self.deposit_radio.isChecked():
                # Рассчитываем прибыль от депозита в банке
                horizon = self.horizon_dropdown.currentText()
                if horizon == "Short-term":
                    rate = 0.03  # 3% краткосрочный банковский процент (пример)
                else:
                    rate = 0.06  # 6% долгосрочный банковский процент (пример)

                estimated_growth = amount * (1 + rate)
                profit = estimated_growth - amount
                QMessageBox.information(self, "Bank Deposit",
                                        f"Expected growth: {estimated_growth:.2f} RUB\n"
                                        f"Profit: {profit:.2f} RUB")
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Please enter a valid number for the investment amount.")
        except RequestError as e:
            QMessageBox.critical(self, "API Error", f"Failed to fetch data from Tinkoff: {e}")

# Запуск приложения
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PortfolioApp()
    window.show()
    sys.exit(app.exec_())
