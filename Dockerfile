FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt requirements-fund.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-fund.txt

COPY . .

ENV HOST=0.0.0.0
ENV PORT=8765

EXPOSE 8765

CMD ["python", "-m", "fund_agents.dashboard"]
