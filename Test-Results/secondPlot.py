import matplotlib.pyplot as plt
import numpy as np

file1 = open("secondPlot.txt", "r")
fin = file1.read()
lines = fin.split("\n")

plt.title("Throughput v/s Packet Loss")
plt.xlabel("Network Delay (in ms)")
plt.ylabel("Bandwidth (B/s)")

i = 0
while i < len(lines):
    x, y = lines[i].split(" ")
    x = float(x)
    y = float(y)
    plt.scatter(x, y, color="b")
    i += 1

i = 0
while i < len(lines):
    if i + 1 > len(lines) - 1:
        break
    x1, y1 = lines[i].split(" ")
    x2, y2 = lines[i + 1].split(" ")
    x1 = float(x1)
    y1 = float(y1)
    x2 = float(x2)
    y2 = float(y2)
    plt.plot([x1, x2], [y1, y2], "g")
    i += 1

plt.show()
