supervisord -c /etc/supervisord.conf

if [ "${ENV}" = "DEV" ]; then
  python -m app.app
else
  # preload option enables some memory sharing across workers
  gunicorn -w 5 -b 0.0.0.0:8080 --timeout 180 --preload app.app:app
fi
