from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Car(db.Model):
    __tablename__ = 'cars'

    id = db.Column(db.Integer, primary_key=True)
    brand = db.Column(db.String(100), nullable=False, index=True)
    model = db.Column(db.String(100), nullable=False)
    price_per_day = db.Column(db.Integer, nullable=False)
    available = db.Column(db.Boolean, default=True, nullable=False)

    rentals = db.relationship('Rental', backref='car', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            "id": self.id,
            "brand": self.brand,
            "model": self.model,
            "price_per_day": self.price_per_day,
            "available": self.available,
        }


class Rental(db.Model):
    __tablename__ = 'rentals'

    id = db.Column(db.Integer, primary_key=True)
    car_id = db.Column(db.Integer, db.ForeignKey('cars.id'), nullable=False)
    renter_name = db.Column(db.String(200), nullable=False)
    taken_at = db.Column(db.String(10), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "car_id": self.car_id,
            "renter_name": self.renter_name,
            "taken_at": self.taken_at,
        }