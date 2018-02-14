#!/usr/bin/python3

import sys

import threading
import queue

from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument("-t", "--threads", type = int, default = 1)
parser.add_argument("count", type = int)
parser.add_argument("--step", default = 1000)
args = parser.parse_args();


threads = 1
minPrime = 2

def isPrime(n):
	if n < minPrime:
		return False

	for i in range(minPrime, n):
		if n % i == 0:
			return False

	return True

def checkForPrimes():
  while True:
    start = q.get()

    if start is None:
      break
    else:
      stop = start + args.step

      print("Checking for primes between", start, "and", stop)

      for i in range(start, stop):
        if isPrime(i):
          primes.append(i)

      q.task_done()

  print("Finished thread.")

#---
primes = list()
q = queue.Queue()

def main():

  threads = []

  for i in range(args.threads):
    t = threading.Thread(target=checkForPrimes)
    t.start()
    threads.append(t)

  index = 0

  while len(primes) < args.count:
    print("Found", len(primes), " primes so far.")

    for i in range(args.threads):
      q.put(index * args.step)
      index = index + 1

    q.join()

  for i in range(args.threads):
    q.put(None)

  for t in threads:
    t.join()

  print("Primes", primes)

if __name__ == "__main__":
	main()
