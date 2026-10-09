import os 
import csv

def read_csv(self):
    if not os.path.exists(self.csv_path):
        return []

    with open(
        self.csv_path,
        "r",
        newline="",
        encoding="utf-8"
    ) as file:

        reader = csv.DictReader(file)

        return list(reader)