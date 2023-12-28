if [ "${ENV}" = "DEV" ]; then
  python -m app.app
else
  gunicorn -w 4 -b 0.0.0.0:8080 app.app:app
fi