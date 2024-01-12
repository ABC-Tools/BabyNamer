supervisord -c /etc/supervisord.conf

if [ "${ENV}" = "DEV" ]; then
  python -m app.app
else
  gunicorn -w 2 -b 0.0.0.0:8080 --timeout 180 app.app:app
fi
