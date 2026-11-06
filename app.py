import time
from flask import Flask, request, jsonify, g
from pydantic import BaseModel, Field, ValidationError

app = Flask(__name__)

# Модели
class CarIn(BaseModel):
    brand: str = Field(..., min_length=1)
    model: str = Field(..., min_length=1)
    price_per_day: int = Field(..., ge=0)
    available: bool = True

class CarPatch(BaseModel):
    brand: str | None = Field(default=None, min_length=1)
    model: str | None = Field(default=None, min_length=1)
    price_per_day: int | None = Field(default=None, ge=0)
    available: bool | None = None

# Хранилище
cars_db: dict[int, dict] = {}
next_id = 1

# Логирование
@app.before_request
def start_timer():
    g.start_time = time.time()

@app.after_request
def log_request(response):
    duration = (time.time() - g.start_time) * 1000
    print(f"{request.method} {request.path} {response.status_code} {duration:.1f}ms")
    return response

# Health
@app.get('/health')
def health():
    return jsonify({"status": "ok"})

# Хелпер валидации (для 400 и field)
def validate(model_cls, data):
    try:
        return model_cls(**data), None
    except ValidationError as e:
        err = e.errors()[0]
        field = err['loc'][0]
        return None, (jsonify({"error": err['msg'], "field": field}), 400)

# CRUD
@app.post('/api/cars')
def create_car():
    global next_id
    body = request.get_json(silent=True)
    if body is None:
        return jsonify({"error": "Invalid JSON", "field": "body"}), 400

    car, err = validate(CarIn, body)
    if err:
        return err

    record = {"id": next_id, **car.model_dump()}
    cars_db[next_id] = record
    next_id += 1
    return jsonify(record), 201

@app.get('/api/cars')
def list_cars():
    limit = request.args.get('limit', type=int)
    offset = request.args.get('offset', default=0, type=int)
    brand = request.args.get('brand')

    result = list(cars_db.values())
    if brand is not None:
        result = [c for c in result if c.get('brand') == brand]

    if limit is not None:
        result = result[offset:offset + limit]
    else:
        result = result[offset:]

    return jsonify(result)

@app.get('/api/cars/<int:car_id>')
def get_car(car_id):
    if car_id not in cars_db:
        return jsonify({"error": "not found"}), 404
    return jsonify(cars_db[car_id])

@app.patch('/api/cars/<int:car_id>')
def update_car(car_id):
    if car_id not in cars_db:
        return jsonify({"error": "not found"}), 404

    body = request.get_json(silent=True)
    if body is None:
        return jsonify({"error": "Invalid JSON", "field": "body"}), 400

    patch, err = validate(CarPatch, body)
    if err:
        return err

    updates = patch.model_dump(exclude_unset=True)
    cars_db[car_id].update(updates)
    return jsonify(cars_db[car_id])

@app.delete('/api/cars/<int:car_id>')
def delete_car(car_id):
    if car_id not in cars_db:
        return jsonify({"error": "not found"}), 404
    del cars_db[car_id]
    return '', 204

# Документация (★★)
@app.route('/docs')
def docs():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Car Rental API Docs</title>
        <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui.css" />
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui-bundle.js"></script>
        <script>
            SwaggerUIBundle({
                url: "/openapi.json",
                dom_id: '#swagger-ui',
                presets: [SwaggerUIBundle.presets.apis, SwaggerUIBundle.SwaggerUIStandalonePreset]
            });
        </script>
    </body>
    </html>
    """
    return html

# Ручная спецификация OpenAPI
@app.route('/openapi.json')
def openapi_spec():
    car_schema = {
        "type": "object",
        "required": ["brand", "model", "price_per_day"],
        "properties": {
            "brand":         {"type": "string", "minLength": 1},
            "model":         {"type": "string", "minLength": 1},
            "price_per_day": {"type": "integer", "minimum": 0},
            "available":     {"type": "boolean", "default": True},
        },
    }
    car_patch_schema = {
        "type": "object",
        "properties": {
            "brand":         {"type": "string", "minLength": 1},
            "model":         {"type": "string", "minLength": 1},
            "price_per_day": {"type": "integer", "minimum": 0},
            "available":     {"type": "boolean"},
        },
    }
    id_param = {
        "name": "id",
        "in": "path",
        "required": True,
        "schema": {"type": "integer"},
    }

    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Car Rental API", "version": "1.0"},
        "paths": {
            "/api/cars": {
                "get": {
                    "summary": "List cars",
                    "parameters": [
                        {"name": "limit",  "in": "query", "required": False, "schema": {"type": "integer"}},
                        {"name": "offset", "in": "query", "required": False, "schema": {"type": "integer", "default": 0}},
                        {"name": "brand",  "in": "query", "required": False, "schema": {"type": "string"}},
                    ],
                    "responses": {"200": {"description": "OK"}},
                },
                "post": {
                    "summary": "Create car",
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": car_schema}},
                    },
                    "responses": {
                        "201": {"description": "Created"},
                        "400": {"description": "Bad Request"},
                    },
                },
            },
            "/api/cars/{id}": {
                "get": {
                    "summary": "Get car",
                    "parameters": [id_param],
                    "responses": {"200": {"description": "OK"}, "404": {"description": "Not Found"}},
                },
                "patch": {
                    "summary": "Update car",
                    "parameters": [id_param],
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": car_patch_schema}},
                    },
                    "responses": {
                        "200": {"description": "OK"},
                        "400": {"description": "Bad Request"},
                        "404": {"description": "Not Found"},
                    },
                },
                "delete": {
                    "summary": "Delete car",
                    "parameters": [id_param],
                    "responses": {"204": {"description": "No Content"}, "404": {"description": "Not Found"}},
                },
            },
        },
    }
    return jsonify(spec)

@app.route('/')
def index():
    return jsonify({
        "service": "Car Rental API",
        "docs": "/docs",
        "openapi": "/openapi.json",
        "health": "/health",
        "cars": "/api/cars"
    })

if __name__ == '__main__':
    app.run(port=8000, debug=True)