cd /jwrFs/Tasks/

if ! git diff --quiet || ! git diff --cached --quiet; then
	git add .
	git commit -m "Autocommit $HOSTNAME $(date)"
	git push
fi
