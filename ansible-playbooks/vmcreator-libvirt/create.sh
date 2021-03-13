#!/usr/bin/env bash

i=0
for f in /jwrFs/Software/PC/OS/* ; do
	FILES[i]=$(basename "$f")
	FILES[i+1]=$(basename "$f")
	((i+=2))
done

IMAGE=$(whiptail --title "Image" --menu "Chose an ooption" 25 300 10 ${FILES[@]} --notags 3>&1 1>&2 2>&3 )

./create.yml -e baseImageFilename=$IMAGE

