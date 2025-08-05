import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "your-secret-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "postgresql+psycopg2://postgres:Happen123!@localhost:5432/livestockdb")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'app', 'static', 'uploads')
    INSPECTION_UPLOAD_FOLDER = 'app/static/uploads/inspection_files'

    # Payment keys
    FLUTTERWAVE_PUBLIC_KEY = os.getenv('FLUTTERWAVE_PUBLIC_KEY')
    FLUTTERWAVE_SECRET_KEY = os.getenv('FLUTTERWAVE_SECRET_KEY')
    FLUTTERWAVE_ENCRYPTION_KEY = os.getenv('FLUTTERWAVE_ENCRYPTION_KEY')

    PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY')
    PAYSTACK_PUBLIC_KEY = os.getenv('PAYSTACK_PUBLIC_KEY')
import os

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
