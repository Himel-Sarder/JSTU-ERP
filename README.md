# ERP-JSTU

Enterprise Resource Planning system for **Jamalpur Science and Technology University**,
built from the project proposal dated 16 July 2026.


## Quick start

```bash
python -m venv venv
Windows: venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser   
python manage.py runserver
```

Open <http://127.0.0.1:8000/> — you land straight on the passkey screen.
