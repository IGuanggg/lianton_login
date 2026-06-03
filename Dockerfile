FROM python:3.10-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt
ENV HOST=0.0.0.0
ENV PORT=5123
ENV FLASK_DEBUG=0
EXPOSE 5123
CMD ["python", "app.py"]
