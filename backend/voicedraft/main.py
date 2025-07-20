from cl_generator import get_best_cl
from utils import load_yaml


def main():
    user_yaml = load_yaml("inputs/user.yaml")
    job_yaml = load_yaml("inputs/job_desc.yaml")
    cover_letter = get_best_cl(user_yaml, job_yaml, par_count=4)
    print(cover_letter)

if __name__ == "__main__":
    main()