from app import create_app, socketio

app = create_app()

if __name__ == '__main__':
    import eventlet
    import eventlet.wsgi
    socketio.run(app, debug=True)
