# DheeMail

Django MVT project with one app, `mailapp`, using SQLite and a custom user model.

## Run locally

From `C:\Users\shree\OneDrive\Desktop\Projects\dheemail`:

```powershell
..\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

If your virtual environment is inside the project folder instead, activate:

```powershell
.\.venv\Scripts\Activate.ps1
```

Then open `http://127.0.0.1:8000/`.
