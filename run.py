# run.py
from app import create_app

app = create_app()

if __name__ == '__main__':
    # Debug=True is helpful during development, but should be False in production
    # Host='0.0.0.0' makes it accessible on your network
    app.run(host='0.0.0.0', port=5000, debug=True)