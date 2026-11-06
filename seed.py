from app import app
from models import db, Car, Rental


def seed():
    with app.app_context():
        # Очищаем
        db.session.query(Rental).delete()
        db.session.query(Car).delete()
        db.session.commit()

        cars = [
            Car(brand="Toyota", model="Camry", price_per_day=5000, available=True),
            Car(brand="BMW", model="X5", price_per_day=12000, available=True),
            Car(brand="Kia", model="Rio", price_per_day=3000, available=True),
        ]
        db.session.add_all(cars)
        db.session.commit()

        rentals = [
            Rental(car_id=cars[0].id, renter_name="Иванов", taken_at="2026-10-01"),
            Rental(car_id=cars[1].id, renter_name="Петров", taken_at="2026-10-02"),
        ]
        db.session.add_all(rentals)
        db.session.commit()
        print("Seed OK: 3 cars, 2 rentals")


if __name__ == '__main__':
    seed()