from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_socketio import SocketIO
from flask_migrate import Migrate
from flask_socketio import SocketIO
from flask_mail import Mail
from flask_wtf import CSRFProtect
csrf = CSRFProtect()
socketio = SocketIO()
mail = Mail()
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()



db = SQLAlchemy()
login_manager = LoginManager()
socketio = SocketIO()
migrate = Migrate()
