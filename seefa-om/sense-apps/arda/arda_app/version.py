__VERSION__ = ""

with open("VERSION", "r") as f:
    __VERSION__ = f.read().strip("\n")
