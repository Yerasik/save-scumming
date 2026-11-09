import os
import glob
import pandas as pd

def inspect():
    print("--- EXPERIMENT A COLUMNS ---")
    files_a = glob.glob("sim/out/A/*.csv")
    if files_a:
        print(pd.read_csv(files_a[0]).columns.tolist())

    print("\n--- EXPERIMENT D COLUMNS ---")
    files_d = glob.glob("sim/out/D/*.csv")
    if files_d:
        print(pd.read_csv(files_d[0]).columns.tolist())

    print("\n--- EXPERIMENT H5 COLUMNS ---")
    files_h5 = glob.glob("sim/out/H5/*.csv")
    if files_h5:
        print(pd.read_csv(files_h5[0]).columns.tolist())

if __name__ == '__main__':
    inspect()