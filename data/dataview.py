import pandas as pd

df = pd.read_parquet("CIC-DDoS2019/Syn-training.parquet")

print(df.head())
print(df.columns)
print(df.shape)