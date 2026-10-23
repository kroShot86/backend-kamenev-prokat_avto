# Прокат автомобилей

## Запуск
pip install flask flask-pydantic-spec
python app.py
Сервис слушает http://localhost:8000

## Эндпоинты
| Метод | Путь | Описание |
| --- | --- | --- |
| GET | /health | проверка живости |
| POST | /api/cars | создать автомобиль |
| GET | /api/cars | список (limit, offset, brand) |
| GET | /api/cars/{id} | один автомобиль |
| PATCH | /api/cars/{id} | обновить |
| DELETE | /api/cars/{id} | удалить |