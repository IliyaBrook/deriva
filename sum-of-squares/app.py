from flask import Flask, request, jsonify
import os
from graphs.main_graph import create_sum_of_squares_graph

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'service': 'sum-of-squares'})

@app.route('/sum_of_squares', methods=['POST'])
def sum_of_squares():
    try:
        data = request.get_json()
        
        if not data or 'length' not in data:
            return jsonify({'error': 'Missing required field: length'}), 400
        
        length = data['length']
        
        if not isinstance(length, int) or length <= 0:
            return jsonify({'error': 'Length must be a positive integer'}), 400
        
        if length > 10000:
            return jsonify({'error': 'Length must be <= 10000 for performance reasons'}), 400
        
        graph = create_sum_of_squares_graph()
        
        result = graph.invoke({"length": length})
        
        return jsonify({"sum_of_squares": result["sum_of_squares"]})
        
    except Exception as e:
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route('/', methods=['GET'])
def index():
    return jsonify({
        'service': 'Sum of Squares API',
        'endpoints': {
            'POST /sum_of_squares': 'Calculate sum of squares for random integers',
            'GET /health': 'Health check endpoint'
        },
        'example': {
            'request': {'length': 100},
            'response': {'sum_of_squares': 123456}
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug) 