#!/bin/sh
# Post to a Loglet log from the shell. Example:
#   loglet -l20 2LNbYgNEAaezJduj hello world

baseurl="http://loglet.radbox.org"
usage () {
    echo usage: $0 [-l LEVEL] LOGID MESSAGE... >&2
    exit 1
}

while getopts l: opt
do    case "$opt" in
        l) level="$OPTARG";;
        [?]) usage;;
        esac
done
shift $((OPTIND-1))

logid=$1
shift
if [ "$logid" == "" ]; then
    echo "no log ID specified" >&2
    usage
fi

message=$@
if [ "$message" == "" ]; then
    echo "no message specified" >&2
    usage
fi

levelarg=""
if [ "$level" != "" ]; then
    levelarg="--data-urlencode level=$level"
fi
response=$(curl -sSo /dev/null -w %{http_code} --data-urlencode message="$message" $levelarg $baseurl/$logid)

if [ "$response" != "200" ]; then
    echo "server error: $response" >&2
    exit 1
fi
