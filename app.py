import os
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return jsonify({
        'status': 'ok',
        'message': 'Sophie Analytics System - Minimal Mode'
    })

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'Sophie Analytics System'
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)