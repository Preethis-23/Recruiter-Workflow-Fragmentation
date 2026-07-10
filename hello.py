import sys

def greet(name):
    print(f"Hey {name}!")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        greet(sys.argv[1])
    else:
        greet("Guest")
