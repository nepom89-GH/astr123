from flask import Flask, render_template, request, jsonify
from pathlib import Path
import json
import traceback
import requests

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config['UPLOAD_FOLDER'] = 'static/charts'
app.config['REPORTS_FOLDER'] = 'reports'

# Создаём необходимые директории
Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)
Path(app.config['REPORTS_FOLDER']).mkdir(parents=True, exist_ok=True)

@app.route('/api/search_city', methods=['GET'])
def search_city():
    try:
        query = request.args.get('q', '')
        if not query or len(query) < 2:
            return jsonify({'results': []})
        url = 'https://nominatim.openstreetmap.org/search'
        params = {
            'q': query,
            'format': 'json',
            'limit': 10,
            'addressdetails': 1
        }
        headers = {'User-Agent': 'Kerykeion Astrology App'}
        response = requests.get(url, params=params, headers=headers, timeout=5)
        if response.status_code == 200:
            results = []
            for item in response.json():
                results.append({
                    'name': item.get('display_name', ''),
                    'lat': float(item.get('lat', 0)),
                    'lon': float(item.get('lon', 0)),
                    'country': item.get('address', {}).get('country', '')
                })
            return jsonify({'results': results})
        else:
            return jsonify({'results': []})
    except Exception as e:
        app.logger.error(f"Error searching city: {str(e)}")
        return jsonify({'results': [], 'error': str(e)})

@app.route('/')
def index():
    return render_template('form.html')

@app.route('/api/submit_form', methods=['POST'])
def submit_form():
    try:
        data = request.json
        app.logger.info(f"Form submission received: {json.dumps(data, ensure_ascii=False, indent=2)}")

        # Извлечение данных (с защитой от отсутствующих полей)
        customer = data.get('customer', {})
        phone = customer.get('phone')  # может отсутствовать
        birth_time = customer.get('birthTime')  # может быть null или ''
        
        # Обработка 10 вопросов
        questions = {}
        for i in range(1, 11):
            q = data.get('questions', {}).get(f'question{i}')
            if q is not None:
                questions[f'question{i}'] = q

        # Family members — birthTime тоже необязательный
        family_members = data.get('familyMembers', [])
        for member in family_members:
            if 'birthTime' not in member:
                member['birthTime'] = None

        # Подготовка данных для лога и webhook (оставляем структуру как есть)
        processed_data = {
            'customer': {
                'name': customer.get('name'),
                'email': customer.get('email'),
                'phone': phone,
                'birthDate': customer.get('birthDate'),
                'birthTime': birth_time,
                'birthPlace': customer.get('birthPlace')
            },
            'familyMembers': family_members,
            'questions': questions
            # Нет: focus, forecastYear — они удалены из формы
        }

        # Отправка на webhook
        webhook_url = "https://script.google.com/macros/s/AKfycbwsocKrTBv36qGvuBMEQU8G-sCTsh01jX6LbZ0WbroZRQleNtkUypViznM0J-FTBFGZ/exec"
        if webhook_url:
            try:
                response = requests.post(
                    webhook_url,
                    json=processed_data,
                    timeout=10,
                    headers={'Content-Type': 'application/json'}
                )
                app.logger.info(f"Webhook response: {response.status_code}")
                if response.status_code >= 400:
                    app.logger.warning(f"Webhook returned error: {response.text}")
            except Exception as webhook_error:
                app.logger.error(f"Error sending to webhook: {str(webhook_error)}")

        # Лог в консоль
        print("\n" + "="*50)
        print("FORM SUBMISSION DATA (PROCESSED):")
        print("="*50)
        print(json.dumps(processed_data, ensure_ascii=False, indent=2))
        print("="*50 + "\n")

        return jsonify({
            'success': True,
            'message': 'Данные успешно получены'
        })

    except Exception as e:
        app.logger.error(f"Error processing form submission: {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)