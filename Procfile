web: cd backend && python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn motogram.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120
bot: cd bot && python main.py
