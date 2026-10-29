# The Daily Brief - container image for the Django news capstone.
# 3.14 matches the interpreter the project is developed and tested on locally.
FROM python:3.14-slim

# PYTHONDONTWRITEBYTECODE / PIP_NO_CACHE_DIR keep the image small;
# PYTHONUNBUFFERED makes Django's request log appear immediately rather than
# being held in a buffer that dies with the container.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# mysqlclient compiles a C extension against the database client library, so the
# compiler and header files must exist before pip runs. They stay in this layer,
# which is why the apt lists are deleted in the same step.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        default-libmysqlclient-dev \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Requirements are copied and installed on their own. Docker caches one layer per
# instruction, so editing a .py file reuses this expensive layer instead of
# reinstalling Django every build.
COPY requirements.txt .
RUN pip install -r requirements.txt

# Everything the app needs to run: code, templates, migrations.
# .dockerignore decides what "everything" excludes.
COPY . .

# The image runs on SQLite so it works with no external database. Set
# DB_ENGINE=mysql to point the same image at a MariaDB server.
ENV DB_ENGINE=sqlite

EXPOSE 8000

# A brand-new container has an empty database, so migrate before serving or every
# page raises "no such table". exec hands runserver the PID so Ctrl-C stops it.
CMD ["sh", "-c", "python manage.py migrate --noinput && exec python manage.py runserver 0.0.0.0:8000"]
