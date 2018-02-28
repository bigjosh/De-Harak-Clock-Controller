#!/bin/bash
echo "Content-type: text/html"
echo ''
echo 'Query=' $QUERY_STRING
./runleds.sh "$QUERY_STRING" 
echo 'CGI Color set<br>'
