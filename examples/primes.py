#!/usr/bin/python

import sys

def isPrime(n):
	if n < 2:
		return False

	for i in range(2, n):
		if float(n) % float(i) == 0:
			return False

	return True

def getPrimes(count):
	primes = list()
	i = 0;

	while len(primes) < count:
		if isPrime(i):
			primes.append(i)
		
		i = i + 1
		
	return primes

if len(sys.argv) < 2:
	print "Usage: ", sys.argv[0], " COUNT"
else:
	try:
		count = int(sys.argv[1])

		print getPrimes(count)
	except ValueError:
		print "Please provide the count of primes as an argument."

