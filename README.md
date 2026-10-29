# The Daily Brief

A Django news application for readers, journalists, and editors. It provides a browser interface and a token-authenticated REST API backed by MariaDB.

## Features

- Custom users with reader, journalist, and editor roles.
- Django groups and permissions aligned to each role.
- Article submission by journalists and editorial approval.
- Reader subscriptions to publishers and independent journalists.
- Subscriber email notifications and a secured approval callback endpoint.
- Newsletters containing approved articles only.
- Token authentication for the API.
- MariaDB support, with SQLite available for isolated automated tests.

## Local setup

1. Create and activate a virtual environment.
2. Install dependencies:

   ```powershell
   .\myenv\Scripts\python.exe -m pip install -r requirements.txt
   ```

3. Copy `.env.example` to `newsproject/.env` and fill in your local MariaDB values. Do not commit this file.
4. Apply migrations:

   ```powershell
   .\myenv\Scripts\python.exe manage.py migrate --database default
   ```

5. Start the site:

   ```powershell
   .\myenv\Scripts\python.exe manage.py runserver
   ```

Visit `http://127.0.0.1:8000/` for the website. The Django admin is at `/admin/`.

## API endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/api/token/` | Obtain an API token with username and password. |
| POST | `/api/users/register/` | Register a new reader account. |
| GET | `/api/users/me/` | View the authenticated user's profile. |
| GET | `/api/publishers/` | List publishers. |
| GET, POST | `/api/articles/` | List approved articles; journalists submit articles. |
| GET | `/api/articles/subscribed/` | View approved content from reader subscriptions. |
| GET, PUT, PATCH, DELETE | `/api/articles/<id>/` | View or manage an article according to role. |
| POST | `/api/articles/<id>/approve/` | Approve an article as an editor. |
| GET, POST | `/api/newsletters/` | List or create newsletters. |
| GET, PUT, PATCH, DELETE | `/api/newsletters/<id>/` | View or manage a newsletter. |

Use the header `Authorization: Token <token>` for token-authenticated API requests.

## Run automated tests

The test suite uses an isolated SQLite database:

```powershell
$env:DB_ENGINE='sqlite'; .\myenv\Scripts\python.exe manage.py test news
```

## Postman demonstration

Import `postman/The_Daily_Brief.postman_collection.json` and
`postman/The_Daily_Brief.postman_environment.example.json` into Postman.
Duplicate the environment in Postman, then add credentials for one reader, one
journalist, and one editor. Start the development server before sending requests:

```powershell
.\myenv\Scripts\python.exe manage.py runserver
```

Run the collection in order. It demonstrates public access, token login,
reader restrictions, journalist submission, editor approval, and newsletter
creation. Do not commit an environment export containing your real passwords
or generated tokens.

## Security notes

- `newsproject/.env` contains passwords and callback tokens and is ignored by Git.
- The approval callback requires `X-Callback-Token`.
- Set a unique `DJANGO_SECRET_KEY` before deployment and set `DEBUG=False` in production.
