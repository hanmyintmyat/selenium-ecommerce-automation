# Browser runs in the Selenium service; the test runner stays small.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HEADLESS=true

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config ./config
COPY pages ./pages
COPY tests ./tests
COPY utils ./utils
COPY test_data ./test_data
COPY conftest.py pytest.ini pyproject.toml ./
RUN mkdir -p reports screenshots logs

CMD ["pytest", "--browser", "chrome", "--headless", "--html=reports/report.html", "--self-contained-html", "--alluredir=reports/allure-results", "--junitxml=reports/junit.xml"]
