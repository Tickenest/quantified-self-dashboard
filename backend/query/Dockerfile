FROM public.ecr.aws/lambda/python:3.12

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY lambda_query.py ${LAMBDA_TASK_ROOT}/lambda_query.py

CMD ["lambda_query.lambda_handler"]
