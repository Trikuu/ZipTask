from app import create_app

try:
    app = create_app()
    app.run(host="0.0.0.0", port=10000)
except Exception as e:
    import traceback
    traceback.print_exc()
    raise