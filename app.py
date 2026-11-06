import os
import time
from flask import Flask, request, jsonify, g
from pydantic import BaseModel, Field, ValidationError
from dotenv import load_dotenv
from flask_migrate import Migrate
from sqlalchemy import func

from models import db, Car, Rental

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///cars.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)


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


class RentalIn(BaseModel):
    renter_name: str = Field(..., min_length=1)
    taken_at: str = Field(..., min_length=10, max_length=10)



@app.before_request
def start_timer():
    g.start_time = time.time()


@app.after_request
def log_request(response):
    duration = (time.time() - g.start_time) * 1000
    print(f"{request.method} {request.path} {response.status_code} {duration:.1f}ms")
    return response



@app.get('/health')
def health():
    return jsonify({"status": "ok"})



def validate(model_cls, data):
    try:
        return model_cls(**data), None
    except ValidationError as e:
        err = e.errors()[0]
        field = err['loc'][0]
        return None, (jsonify({"error": err['msg'], "field": field}), 400)



@app.post('/api/cars')
def create_car():
    body = request.get_json(silent=True)
    if body is None:
        return jsonify({"error": "Invalid JSON", "field": "body"}), 400

    car_in, err = validate(CarIn, body)
    if err:
        return err

    car = Car(**car_in.model_dump())
    db.session.add(car)
    db.session.commit()
    return jsonify(car.to_dict()), 201


@app.get('/api/cars')
def list_cars():
    limit = request.args.get('limit', type=int)
    offset = request.args.get('offset', default=0, type=int)
    brand = request.args.get('brand')
    q = request.args.get('q')  # поиск для ★

    query = Car.query

    if brand is not None:
        query = query.filter(Car.brand == brand)

    if q:
        query = query.filter(Car.brand.ilike(f'%{q}%'))

    if limit is not None:
        query = query.offset(offset).limit(limit)
    else:
        query = query.offset(offset)

    cars = query.all()
    return jsonify([c.to_dict() for c in cars])


@app.get('/api/cars/<int:car_id>')
def get_car(car_id):
    car = db.session.get(Car, car_id)
    if not car:
        return jsonify({"error": "not found"}), 404
    return jsonify(car.to_dict())


@app.patch('/api/cars/<int:car_id>')
def update_car(car_id):
    car = db.session.get(Car, car_id)
    if not car:
        return jsonify({"error": "not found"}), 404

    body = request.get_json(silent=True)
    if body is None:
        return jsonify({"error": "Invalid JSON", "field": "body"}), 400

    patch, err = validate(CarPatch, body)
    if err:
        return err

    for key, value in patch.model_dump(exclude_unset=True).items():
        setattr(car, key, value)
    db.session.commit()
    return jsonify(car.to_dict())


@app.delete('/api/cars/<int:car_id>')
def delete_car(car_id):
    car = db.session.get(Car, car_id)
    if not car:
        return jsonify({"error": "not found"}), 404
    db.session.delete(car)
    db.session.commit()
    return '', 204



@app.post('/api/cars/<int:car_id>/rentals')
def create_rental(car_id):
    car = db.session.get(Car, car_id)
    if not car:
        return jsonify({"error": "Car not found"}), 404

    body = request.get_json(silent=True)
    if body is None:
        return jsonify({"error": "Invalid JSON", "field": "body"}), 400

    rental_in, err = validate(RentalIn, body)
    if err:
        return err


    if not car.available:
        return jsonify({
            "error": "Car is not available",
            "reason": "Машина уже арендована или снята с проката"
        }), 409


    try:
        rental = Rental(
            car_id=car_id,
            renter_name=rental_in.renter_name,
            taken_at=rental_in.taken_at,
        )
        car.available = False
        db.session.add(rental)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Transaction failed"}), 500

    return jsonify(rental.to_dict()), 201


@app.get('/api/cars/<int:car_id>/rentals')
def list_rentals(car_id):
    car = db.session.get(Car, car_id)
    if not car:
        return jsonify({"error": "Car not found"}), 404
    return jsonify([r.to_dict() for r in car.rentals])



@app.get('/api/cars/stats')
def stats():
    rows = (
        db.session.query(
            Car.brand,
            func.count(Rental.id).label('rentals_count'),
            func.sum(Car.price_per_day).label('total_price'),
            func.avg(Car.price_per_day).label('avg_price'),
        )
        .outerjoin(Rental, Rental.car_id == Car.id)
        .group_by(Car.brand)
        .all()
    )
    return jsonify([
        {
            "brand": r.brand,
            "rentals_count": int(r.rentals_count or 0),
            "total_price": int(r.total_price or 0),
            "avg_price": float(r.avg_price or 0),
        }
        for r in rows
    ])



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
                presets: [SwaggerUIBundle.presets.apis]
            });
        </script>
    </body>
    </html>
    """
    return html


@app.route('/openapi.json')
def openapi_spec():
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Car Rental API", "version": "2.0"},
        "paths": {
            "/api/cars": {
                "get": {"summary": "List cars"},
                "post": {"summary": "Create car"}
            },
            "/api/cars/{id}": {
                "get": {"summary": "Get car"},
                "patch": {"summary": "Update car"},
                "delete": {"summary": "Delete car"}
            },
            "/api/cars/{id}/rentals": {
                "get": {"summary": "List rentals"},
                "post": {"summary": "Create rental"}
            },
            "/api/cars/stats": {"get": {"summary": "Statistics"}}
        }
    }
    return jsonify(spec)


if __name__ == '__main__':
    app.run(port=8000, debug=True)