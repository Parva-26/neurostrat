#!/bin/bash
cd ../ml
pip install -r requirements.txt
python -c "
from data_generator import generate_dataset
from train_evaluate import train_and_evaluate
import os
os.makedirs('models', exist_ok=True)
df = generate_dataset(3000)
train_and_evaluate(df) 