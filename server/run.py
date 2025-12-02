from app import create_app

app = create_app()

if __name__ == '__main__':
    host = os.environ.get("API_HOST", "0.0.0.0")
    port = int(os.environ.get("API_PORT", 8080))
    
    logger.info(f"Starting Flask server on {host}:{port}")
    app.run(host=host, port=port)