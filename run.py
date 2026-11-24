import os
from app import create_app

env = os.getenv("FLASK_ENV", "development")
app = create_app(env)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    # Bind to 0.0.0.0 to enable communication from Android emulator (10.0.2.2)
    app.run(host="0.0.0.0", port=port, debug=True)

