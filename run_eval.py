from src.evaluation.runner import run
if __name__ == "__main__":
    rep = run(k=5)
    print(rep["verdict"])
    print(rep["aggregate"])
    print(rep["checks"])
