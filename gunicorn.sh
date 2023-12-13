if [ "${ENV}" = "DEV" ]; then
  python app/app.py
else
  gunicorn --chdir ./app -w 4 -b 0.0.0.0:8080 app:app
fi