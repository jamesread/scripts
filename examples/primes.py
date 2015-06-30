#!/usr/bin/python

import sys

minPrime = 2

def isPrime(n):
	if n < minPrime:
		return False

	for i in range(minPrime, n):
		if n % i == 0:
			return False

	return True

def getPrimes(count):
	primes = list()
	i = minPrime;

	while len(primes) < count:
		if isPrime(i):
			primes.append(i)
		
		i = i + 1
		
	return primes

def main():
	if len(sys.argv) < 2:
		print "Usage: ", sys.argv[0], " COUNT"
		return
	
	try:
		count = int(sys.argv[1])
	except ValueError:
		print "Please provide the count of primes as an argument."
		return

	print getPrimes(count)

if __name__ == "__main__":
	main()
