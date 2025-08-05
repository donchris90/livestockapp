from flask_script import Manager
from flask_migrate import MigrateCommand
from app import create_app
from app.extensions import db

app = create_app()
manager = Manager(app)

# Add migrate command
manager.add_command('db', MigrateCommand)

if __name__ == '__main__':
    manager.run()
