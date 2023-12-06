FROM python:3.8.18-slim-bullseye

WORKDIR /app

RUN pip install -U requests mthrottle

RUN echo 'from kitetrader import Kite\n\
with Kite() as kite:\n\t\
print(kite.quote("hdfcbank"))\n\
print("all working well")' > test.py

COPY kitetrader/ kitetrader/
COPY __init__.py .

CMD ["python3", "test.py"]
